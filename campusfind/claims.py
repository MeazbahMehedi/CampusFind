from flask import Blueprint, abort, flash, redirect, render_template, url_for
from flask_login import current_user, login_required
from sqlalchemy.exc import IntegrityError

from .forms import ClaimForm, MessageForm, ReviewForm
from .models import Claim, ClaimMessage, Item, db, now
from .reports import get_visible
from .services import event, notify, notify_admins, refresh_item, student_required

bp = Blueprint("claims", __name__, url_prefix="/claims")


@bp.post("/item/<int:item_id>")
@student_required
def create(item_id):
    item = get_visible(item_id)
    if item.owner_id == current_user.id:
        abort(403)
    if (
        item.kind != "found"
        or item.is_hidden
        or item.review_status != "approved"
        or item.status not in {"reported", "claim_pending"}
    ):
        flash("This item is not accepting ownership claims.", "error")
        return redirect(url_for("reports.detail", item_id=item.id))
    form = ClaimForm()
    if form.validate_on_submit():
        claim = Claim(
            item_id=item.id, claimant_id=current_user.id, evidence=form.evidence.data.strip()
        )
        db.session.add(claim)
        try:
            db.session.flush()
        except IntegrityError:
            db.session.rollback()
            flash("You already have a claim for this item. Check it in your dashboard.", "error")
        else:
            result = db.session.execute(
                db.update(Item)
                .where(
                    Item.id == item.id,
                    Item.reserved_claim_id.is_(None),
                    Item.is_hidden.is_(False),
                    Item.review_status == "approved",
                    Item.status.in_(("reported", "claim_pending")),
                )
                .values(status="claim_pending", updated_at=now())
                .execution_options(synchronize_session=False)
            )
            if result.rowcount != 1:
                db.session.rollback()
                flash(
                    "This item stopped accepting claims. Reload the report for its latest status.",
                    "error",
                )
                return redirect(url_for("reports.detail", item_id=item.id))
            db.session.expire(item)
            event(item, "An ownership claim was submitted for review.")
            notify(
                current_user.id,
                "Claim submitted",
                f"Your claim for {item.title} is awaiting administrator review.",
                claim.id,
            )
            notify(
                item.owner_id,
                "Your found-item report received a claim",
                f"An administrator will verify ownership for {item.title}.",
            )
            notify_admins("New ownership claim", item.title, claim_id=claim.id)
            db.session.commit()
            flash("Claim submitted. Your evidence is private.", "success")
            return redirect(url_for("claims.detail", claim_id=claim.id))
    else:
        for error in form.evidence.errors:
            flash(error, "error")
    return redirect(url_for("reports.detail", item_id=item.id))


@bp.get("/<int:claim_id>")
@login_required
def detail(claim_id):
    claim = db.get_or_404(Claim, claim_id)
    if claim.claimant_id != current_user.id and not current_user.is_admin:
        abort(403)
    review_form = ReviewForm()
    review_form.action.choices = (
        [("return", "Confirm physical handover")]
        if claim.status == "approved"
        else [
            ("needs_info", "Request more information"),
            ("approve", "Approve ownership claim"),
            ("reject", "Reject ownership claim"),
        ]
    )
    return render_template(
        "claim_detail.html", claim=claim, form=MessageForm(), review_form=review_form
    )


@bp.post("/<int:claim_id>/message")
@student_required
def message(claim_id):
    claim = db.get_or_404(Claim, claim_id)
    if claim.claimant_id != current_user.id:
        abort(403)
    form = MessageForm()
    if claim.status != "needs_info":
        flash("Additional evidence can be sent when an administrator requests it.", "error")
    elif form.validate_on_submit():
        db.session.add(
            ClaimMessage(claim_id=claim.id, author_id=current_user.id, body=form.body.data.strip())
        )
        claim.status = "pending"
        notify_admins("Claim clarification received", claim.item.title, claim_id=claim.id)
        db.session.commit()
        flash("Your information has been sent for review.", "success")
    else:
        for error in form.body.errors:
            flash(error, "error")
    return redirect(url_for("claims.detail", claim_id=claim.id))


@bp.post("/<int:claim_id>/withdraw")
@student_required
def withdraw(claim_id):
    claim = db.get_or_404(Claim, claim_id)
    if claim.claimant_id != current_user.id:
        abort(403)
    if claim.status not in {"pending", "needs_info"}:
        flash("This claim can no longer be withdrawn.", "error")
    else:
        claim.status = "withdrawn"
        db.session.flush()
        refresh_item(claim.item)
        event(claim.item, "An ownership claim was withdrawn.")
        db.session.commit()
        flash("Claim withdrawn.", "success")
    return redirect(url_for("claims.detail", claim_id=claim.id))
