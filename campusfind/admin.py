from datetime import date, timedelta

from flask import Blueprint, flash, redirect, render_template, request, url_for
from flask_login import current_user

from .forms import ModerateForm, ReviewForm
from .models import Audit, Claim, Item, User, db
from .services import admin_required, audit, close_report, decide_claim, event, notify
from .views import totals

bp = Blueprint("admin", __name__, url_prefix="/admin")


@bp.get("")
@admin_required
def overview():
    pending = db.session.scalar(
        db.select(db.func.count())
        .select_from(Claim)
        .where(Claim.status.in_(("pending", "needs_info")))
    )
    recent = db.session.scalars(
        db.select(Claim)
        .where(Claim.status.in_(("pending", "needs_info", "approved")))
        .order_by(Claim.created_at)
        .limit(6)
    ).all()
    category_counts = db.session.execute(
        db.select(Item.category, db.func.count(Item.id))
        .group_by(Item.category)
        .order_by(db.func.count(Item.id).desc())
    ).all()
    trend = []
    for offset in range(6, -1, -1):
        day = date.today() - timedelta(days=offset)
        count = db.session.scalar(
            db.select(db.func.count())
            .select_from(Item)
            .where(db.func.date(Item.created_at) == day.isoformat())
        )
        trend.append((day.strftime("%a"), count))
    return render_template(
        "admin.html",
        section="overview",
        stats=totals(),
        pending=pending,
        recent=recent,
        category_counts=category_counts,
        trend=trend,
    )


@bp.get("/claims")
@admin_required
def claims():
    query = db.select(Claim)
    status = request.args.get("status", "")
    if status:
        query = query.where(Claim.status == status)
    page = db.paginate(query.order_by(Claim.created_at.desc()), per_page=15, error_out=False)
    return render_template("admin.html", section="claims", page=page)


@bp.post("/claims/<int:claim_id>/review")
@admin_required
def review(claim_id):
    claim = db.get_or_404(Claim, claim_id)
    form = ReviewForm()
    if form.validate_on_submit():
        try:
            if claim.claimant_id == current_user.id or claim.item.owner_id == current_user.id:
                raise ValueError(
                    "A different administrator must review claims involving your own account."
                )
            decide_claim(claim, form.action.data, form.note.data.strip())
            db.session.commit()
        except ValueError as exc:
            db.session.rollback()
            flash(str(exc), "error")
        else:
            flash("Claim review recorded.", "success")
    else:
        for field_errors in form.errors.values():
            for error in field_errors:
                flash(error, "error")
    return redirect(url_for("claims.detail", claim_id=claim.id))


@bp.get("/reports")
@admin_required
def reports():
    query = db.select(Item)
    if request.args.get("hidden") == "1":
        query = query.where(Item.is_hidden.is_(True))
    page = db.paginate(query.order_by(Item.created_at.desc()), per_page=15, error_out=False)
    return render_template("admin.html", section="reports", page=page)


@bp.post("/reports/<int:item_id>/moderate")
@admin_required
def moderate(item_id):
    item = db.get_or_404(Item, item_id)
    form = ModerateForm()
    if form.validate_on_submit():
        action = form.action.data
        reason = form.reason.data.strip()
        try:
            if action == "hide":
                if item.status != "returned":
                    close_report(item, reason)
                item.is_hidden = True
                event(item, "Report hidden by an administrator.")
            elif action == "restore":
                item.is_hidden = False
                event(item, "Report visibility restored.")
            elif action == "close":
                close_report(item, reason)
            elif action == "reopen":
                if item.status != "closed" or item.is_hidden:
                    raise ValueError("Only visible, closed reports can be reopened.")
                item.status = "reported"
                event(item, "Report reopened.")
            audit(f"Report #{item.id}: {action}. {reason}")
            notify(item.owner_id, "Your report was moderated", f"{item.title}: {action}. {reason}")
            db.session.commit()
            flash("Report updated.", "success")
        except ValueError as exc:
            db.session.rollback()
            flash(str(exc), "error")
    else:
        flash("Choose a valid action and provide a reason of at least 10 characters.", "error")
    return redirect(url_for("reports.detail", item_id=item.id))


@bp.get("/users")
@admin_required
def users():
    page = db.paginate(
        db.select(User).order_by(User.created_at.desc()), per_page=20, error_out=False
    )
    return render_template("admin.html", section="users", page=page)


@bp.post("/users/<int:user_id>/toggle")
@admin_required
def toggle_user(user_id):
    user = db.get_or_404(User, user_id)
    if user.is_admin:
        flash("Administrator accounts cannot be disabled from this screen.", "error")
    else:
        user.enabled = not user.enabled
        audit(f"User #{user.id}: {'enabled' if user.enabled else 'disabled'}")
        db.session.commit()
        flash("Account access updated.", "success")
    return redirect(url_for("admin.users"))


@bp.get("/activity")
@admin_required
def activity():
    page = db.paginate(
        db.select(Audit).order_by(Audit.created_at.desc()), per_page=25, error_out=False
    )
    return render_template("admin.html", section="activity", page=page)
