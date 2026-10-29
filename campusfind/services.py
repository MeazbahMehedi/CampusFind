"""Shared transitions. Callers commit once after all related records are added."""

from functools import wraps
from io import BytesIO
from pathlib import Path
import secrets

from flask import abort, current_app
from flask_login import current_user, login_required
from PIL import Image, ImageOps, UnidentifiedImageError
from sqlalchemy import update

from .models import Audit, Claim, ClaimMessage, Item, ItemEvent, Notification, db, now

ACTIVE_CLAIMS = ("pending", "needs_info", "approved")


def admin_required(function):
    @wraps(function)
    @login_required
    def wrapped(*args, **kwargs):
        if not current_user.is_admin:
            abort(403)
        return function(*args, **kwargs)

    return wrapped


def notify(user_id, title, body, claim_id=None):
    db.session.add(Notification(user_id=user_id, title=title, body=body, claim_id=claim_id))


def audit(action):
    db.session.add(Audit(actor_id=current_user.id, action=action))


def event(item, label):
    db.session.add(ItemEvent(item_id=item.id, label=label))
    item.updated_at = now()


def save_image(file):
    data = file.stream.read(5 * 1024 * 1024 + 1)
    if len(data) > 5 * 1024 * 1024:
        raise ValueError("The image must be smaller than 5 MB.")
    try:
        with Image.open(BytesIO(data)) as source:
            if source.format not in {"JPEG", "PNG", "WEBP"}:
                raise ValueError("Choose a JPG, PNG, or WebP photograph.")
            if source.width * source.height > 20_000_000:
                raise ValueError("The image resolution is too large (maximum 20 megapixels).")
            image = ImageOps.exif_transpose(source).convert("RGB")
            image.thumbnail((1600, 1600))
            filename = secrets.token_hex(16) + ".jpg"
            image.save(Path(current_app.config["UPLOAD_FOLDER"]) / filename, "JPEG", quality=85)
            return filename
    except (
        UnidentifiedImageError,
        OSError,
        Image.DecompressionBombError,
        Image.DecompressionBombWarning,
    ) as exc:
        raise ValueError("This file is not a supported, readable image.") from exc


def refresh_item(item):
    if item.status in {"returned", "closed", "awaiting_handover"}:
        return
    active = db.session.scalar(
        db.select(db.func.count())
        .select_from(Claim)
        .where(Claim.item_id == item.id, Claim.status.in_(("pending", "needs_info")))
    )
    item.status = "claim_pending" if active else "reported"


def decide_claim(claim, action, note):
    item = claim.item
    if item.is_hidden or item.status in {"returned", "closed"}:
        raise ValueError("This report is closed or hidden. Its claims cannot be reviewed.")
    if action == "return":
        if (
            claim.status != "approved"
            or item.reserved_claim_id != claim.id
            or item.status != "awaiting_handover"
        ):
            raise ValueError("Only the approved claim can be marked as physically returned.")
        claim.status = "returned"
        item.status = "returned"
        event(item, "Physical handover confirmed. Item returned.")
        notify(item.owner_id, "Item successfully returned", item.title)
    else:
        if claim.status not in {"pending", "needs_info"}:
            raise ValueError("This claim has already been decided.")
        if action == "approve":
            # Reserve with a conditional database update so only one reviewer can win.
            result = db.session.execute(
                update(Item)
                .where(
                    Item.id == item.id,
                    Item.reserved_claim_id.is_(None),
                    Item.status.in_(("reported", "claim_pending")),
                    Item.is_hidden.is_(False),
                )
                .values(reserved_claim_id=claim.id, status="awaiting_handover", updated_at=now())
                .execution_options(synchronize_session=False)
            )
            if result.rowcount != 1:
                raise ValueError("This item has already been reserved or closed. Reload the page.")
            db.session.expire(item)
            claim.status = "approved"
            for other in item.claims:
                if other.id != claim.id and other.status in {"pending", "needs_info"}:
                    other.status = "rejected"
                    other.review_note = "Another ownership claim was approved for this item."
                    other.reviewed_by = current_user.id
                    notify(other.claimant_id, "Claim reviewed", other.review_note, other.id)
            event(item, "Ownership verified. Awaiting physical handover.")
            notify(
                item.owner_id,
                "Handover can be arranged",
                f"An ownership claim for {item.title} was approved. Please coordinate with the campus administrator.",
            )
        elif action == "reject":
            claim.status = "rejected"
        elif action == "needs_info":
            claim.status = "needs_info"
        else:
            raise ValueError("Unknown review action.")
        db.session.flush()
        refresh_item(item)
    claim.review_note = note
    claim.reviewed_by = current_user.id
    notify(
        claim.claimant_id,
        "Your claim was updated",
        f"{item.title}: {claim.status.replace('_', ' ')}. {note}",
        claim.id,
    )
    db.session.add(ClaimMessage(claim_id=claim.id, author_id=current_user.id, body=note))
    audit(f"Claim #{claim.id}: {action}")


def close_report(item, reason):
    if item.status == "returned":
        raise ValueError("A confirmed return cannot be changed to closed.")
    for claim in item.claims:
        if claim.status in ACTIVE_CLAIMS:
            claim.status = "rejected"
            claim.review_note = f"Report closed: {reason}"
            notify(claim.claimant_id, "Report closed", claim.review_note, claim.id)
    item.status = "closed"
    item.reserved_claim_id = None
    event(item, "Report closed.")
