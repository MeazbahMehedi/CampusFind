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


def student_required(function):
    @wraps(function)
    @login_required
    def wrapped(*args, **kwargs):
        if current_user.role != "student":
            abort(403)
        return function(*args, **kwargs)

    return wrapped


def notify(user_id, title, body, claim_id=None, item_id=None):
    db.session.add(
        Notification(user_id=user_id, title=title, body=body, claim_id=claim_id, item_id=item_id)
    )


def notify_admins(title, body, claim_id=None, item_id=None):
    from .models import User

    for admin in db.session.scalars(
        db.select(User).where(User.role == "admin", User.enabled.is_(True))
    ).all():
        notify(admin.id, title, body, claim_id, item_id)


def audit(action, object_type="general", object_id=None, previous="", next_status="", reason=""):
    db.session.add(
        Audit(
            actor_id=current_user.id,
            action=action,
            object_type=object_type,
            object_id=object_id,
            previous_status=previous,
            next_status=next_status,
            reason=reason,
        )
    )


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
    previous = claim.status
    if item.is_hidden or item.review_status != "approved" or item.status in {"returned", "closed"}:
        raise ValueError("This report is closed or hidden. Its claims cannot be reviewed.")
    if action == "return":
        if (
            claim.status != "approved"
            or item.reserved_claim_id != claim.id
            or item.status != "awaiting_handover"
        ):
            raise ValueError("Only the approved claim can be marked as physically returned.")
        claim.status = "returned"
        claim.returned_at = now()
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
                    Item.review_status == "approved",
                )
                .values(reserved_claim_id=claim.id, status="awaiting_handover", updated_at=now())
                .execution_options(synchronize_session=False)
            )
            if result.rowcount != 1:
                raise ValueError("This item has already been reserved or closed. Reload the page.")
            db.session.expire(item)
            claim.status = "approved"
            from .settings import campus_settings

            settings = campus_settings()
            claim.collection_point = settings["collection_points"][0]
            claim.handover_note = settings["handover_instructions"]
            for other in item.claims:
                if other.id != claim.id and other.status in {"pending", "needs_info"}:
                    other.status = "rejected"
                    other.review_note = "Another ownership claim was approved for this item."
                    other.reviewed_by = current_user.id
                    notify(other.claimant_id, "Claim reviewed", other.review_note, other.id)
                    audit(
                        f"Competing claim #{other.id} rejected",
                        "claim",
                        other.id,
                        "pending review",
                        "rejected",
                        other.review_note,
                    )
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
    audit(f"Claim #{claim.id}: {action}", "claim", claim.id, previous, claim.status, note)


def close_report(item, reason):
    if item.status == "returned":
        raise ValueError("A confirmed return cannot be changed to closed.")
    for claim in item.claims:
        if claim.status in ACTIVE_CLAIMS:
            claim.status = "rejected"
            claim.review_note = f"Report closed: {reason}"
            previous = claim.status
            if current_user.is_admin:
                claim.reviewed_by = current_user.id
                audit(
                    f"Claim #{claim.id} cancelled by report closure",
                    "claim",
                    claim.id,
                    previous,
                    "rejected",
                    reason,
                )
                db.session.add(
                    ClaimMessage(
                        claim_id=claim.id, author_id=current_user.id, body=claim.review_note
                    )
                )
            notify(claim.claimant_id, "Report closed", claim.review_note, claim.id)
    item.status = "closed"
    item.reserved_claim_id = None
    event(item, "Report closed.")
