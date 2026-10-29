"""Publication review is separate from ownership verification and physical return."""

from flask_login import current_user

from .models import ReportReview, db, now
from .services import ACTIVE_CLAIMS, audit, close_report, event, notify


def moderate_report(item, action, reason):
    previous = f"{item.review_status}/{item.status}" + ("/hidden" if item.is_hidden else "")
    if action in {"approve", "needs_changes", "reject"}:
        if (
            item.is_hidden
            or item.status != "reported"
            or any(c.status in ACTIVE_CLAIMS for c in item.claims)
        ):
            raise ValueError(
                "Only visible, unreserved reports without active claims can enter publication review."
            )
        if action == "approve":
            if item.review_status not in {"pending", "needs_changes"}:
                raise ValueError("This report is already approved or requires reopening first.")
            item.review_status = "approved"
            event(item, "Report approved for publication.")
        elif action == "needs_changes":
            if item.review_status not in {"pending", "approved", "needs_changes"}:
                raise ValueError("Reopen this report before requesting corrections.")
            item.review_status = "needs_changes"
            event(item, "Corrections requested before publication.")
        else:
            if item.review_status not in {"pending", "needs_changes"}:
                raise ValueError(
                    "Only an unpublished report can be rejected. Close or hide a published report instead."
                )
            item.review_status = "rejected"
            close_report(item, reason)
        item.reviewed_by = current_user.id
        item.reviewed_at = now()
    elif action == "hide":
        if item.is_hidden:
            raise ValueError("This report is already hidden.")
        if item.status not in {"returned", "closed"}:
            close_report(item, reason)
        item.is_hidden = True
        event(item, "Report hidden by an administrator.")
    elif action == "restore":
        if not item.is_hidden:
            raise ValueError("This report is already visible.")
        item.is_hidden = False
        event(item, "Report visibility restored. Lifecycle unchanged.")
    elif action == "close":
        if item.status == "closed":
            raise ValueError("This report is already closed.")
        close_report(item, reason)
    elif action == "reopen":
        if (
            item.status != "closed"
            or item.is_hidden
            or any(c.status == "returned" for c in item.claims)
        ):
            raise ValueError(
                "Only visible, closed reports without a confirmed return can be reopened."
            )
        item.status = "reported"
        item.reserved_claim_id = None
        if item.review_status == "rejected":
            item.review_status = "pending"
        event(item, "Report reopened. Previous claim decisions remain unchanged.")
    else:
        raise ValueError("Unknown report action.")
    item.review_note = reason
    db.session.add(
        ReportReview(item_id=item.id, actor_id=current_user.id, action=action, note=reason)
    )
    next_state = f"{item.review_status}/{item.status}" + ("/hidden" if item.is_hidden else "")
    audit(f"Report #{item.id}: {action}", "report", item.id, previous, next_state, reason)
    notify(
        item.owner_id,
        "Your report was reviewed",
        f"{item.title}: {action.replace('_', ' ')}. {reason}",
        item_id=item.id,
    )
