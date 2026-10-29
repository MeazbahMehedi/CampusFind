"""Management-only workspace: publication, claims, returns, accounts and campus settings."""

from datetime import date, datetime, time, timedelta

from flask import Blueprint, abort, flash, redirect, render_template, request, url_for
from flask_login import current_user
from sqlalchemy import or_

from .forms import AccessForm, HandoverForm, ModerateForm, ReviewForm, SettingsForm
from .models import Audit, Claim, Item, User, db
from .moderation import moderate_report
from .services import admin_required, audit, decide_claim, notify
from .settings import campus_settings, save_settings

bp = Blueprint("admin", __name__, url_prefix="/admin")


def count(model, *conditions):
    return db.session.scalar(db.select(db.func.count()).select_from(model).where(*conditions))


def report_query():
    query = db.select(Item)
    for field in ["kind", "category", "location", "status", "review_status"]:
        value = request.args.get(field, "")
        if value:
            if field == "status" and value == "active":
                query = query.where(
                    Item.status.in_(("reported", "claim_pending", "awaiting_handover"))
                )
            else:
                query = query.where(getattr(Item, field) == value)
    if request.args.get("hidden") in {"0", "1"}:
        query = query.where(Item.is_hidden.is_(request.args["hidden"] == "1"))
    q = request.args.get("q", "").strip()[:120]
    if q:
        term = "%" + q.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_") + "%"
        query = query.where(
            or_(Item.title.ilike(term, escape="\\"), Item.description.ilike(term, escape="\\"))
        )
    for key, lower in [("from_date", True), ("to_date", False)]:
        value = request.args.get(key)
        if value:
            try:
                day = date.fromisoformat(value)
            except ValueError:
                abort(400)
            query = query.where(
                Item.created_at >= datetime.combine(day, time.min)
                if lower
                else Item.created_at < datetime.combine(day + timedelta(days=1), time.min)
            )
    return query


def analytics_data():
    items = db.session.scalars(report_query().order_by(Item.created_at.desc())).all()
    counts = {}
    locations = {}
    for item in items:
        counts[item.category] = counts.get(item.category, 0) + 1
        locations[item.location] = locations.get(item.location, 0) + 1
    return dict(
        items=items,
        total=len(items),
        returned=sum(i.status == "returned" for i in items),
        closed=sum(i.status == "closed" for i in items),
        pending=sum(i.review_status == "pending" for i in items),
        category_counts=sorted(counts.items(), key=lambda x: -x[1]),
        location_counts=sorted(locations.items(), key=lambda x: -x[1]),
    )


@bp.get("")
@admin_required
def overview():
    stats = {
        "pending_reports": count(
            Item,
            Item.review_status == "pending",
            Item.status == "reported",
            Item.is_hidden.is_(False),
        ),
        "pending_claims": count(Claim, Claim.status.in_(("pending", "needs_info"))),
        "handovers": count(Claim, Claim.status == "approved"),
        "returned": count(Item, Item.status == "returned"),
        "active": count(
            Item,
            Item.review_status == "approved",
            Item.is_hidden.is_(False),
            Item.status.in_(("reported", "claim_pending", "awaiting_handover")),
        ),
        "students": count(User, User.role == "student"),
    }
    reports = db.session.scalars(
        db.select(Item)
        .where(
            Item.review_status == "pending", Item.status == "reported", Item.is_hidden.is_(False)
        )
        .order_by(Item.updated_at)
        .limit(5)
    ).all()
    claims = db.session.scalars(
        db.select(Claim)
        .where(Claim.status.in_(("pending", "needs_info")))
        .order_by(Claim.created_at)
        .limit(5)
    ).all()
    activity = db.session.scalars(db.select(Audit).order_by(Audit.created_at.desc()).limit(5)).all()
    trend = []
    for offset in range(6, -1, -1):
        day = date.today() - timedelta(days=offset)
        trend.append(
            (day.strftime("%a"), count(Item, db.func.date(Item.created_at) == day.isoformat()))
        )
    return render_template(
        "admin.html",
        section="overview",
        stats=stats,
        reports=reports,
        claims=claims,
        activity=activity,
        trend=trend,
    )


@bp.get("/reports")
@admin_required
def reports():
    page = db.paginate(
        report_query().order_by(Item.updated_at.desc()), per_page=15, error_out=False
    )
    return render_template("admin.html", section="reports", page=page)


@bp.post("/reports/<int:item_id>/moderate")
@admin_required
def moderate(item_id):
    item = db.get_or_404(Item, item_id)
    form = ModerateForm()
    if form.validate_on_submit():
        try:
            moderate_report(item, form.action.data, form.reason.data.strip())
            db.session.commit()
            flash("Report decision recorded. The student has been notified.", "success")
        except ValueError as exc:
            db.session.rollback()
            flash(str(exc), "error")
    else:
        flash("Choose a valid action and provide a reason of at least 10 characters.", "error")
    return redirect(url_for("reports.detail", item_id=item.id))


@bp.get("/claims")
@admin_required
def claims():
    query = db.select(Claim)
    status = request.args.get("status", "")
    if status == "review":
        query = query.where(Claim.status.in_(("pending", "needs_info")))
    elif status:
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
                    "A different administrator must review legacy records involving your account."
                )
            decide_claim(claim, form.action.data, form.note.data.strip())
            db.session.commit()
            flash("Claim review recorded.", "success")
        except ValueError as exc:
            db.session.rollback()
            flash(str(exc), "error")
    else:
        flash("Choose a valid decision and write a review note of at least 10 characters.", "error")
    return redirect(url_for("claims.detail", claim_id=claim.id))


@bp.get("/handovers")
@admin_required
def handovers():
    status = request.args.get("status", "approved")
    if status not in {"approved", "returned"}:
        abort(400)
    page = db.paginate(
        db.select(Claim).where(Claim.status == status).order_by(Claim.updated_at),
        per_page=15,
        error_out=False,
    )
    return render_template("admin.html", section="handovers", page=page)


@bp.route("/handovers/<int:claim_id>", methods=["GET", "POST"])
@admin_required
def handover(claim_id):
    claim = db.get_or_404(Claim, claim_id)
    if (
        claim.status != "approved"
        or claim.item.status != "awaiting_handover"
        or claim.item.is_hidden
        or claim.item.review_status != "approved"
    ):
        flash("Only an active approved claim can have its collection details changed.", "error")
        return redirect(url_for("claims.detail", claim_id=claim.id))
    form = HandoverForm(collection_point=claim.collection_point, note=claim.handover_note)
    if claim.collection_point and claim.collection_point not in form.collection_point.choices:
        form.collection_point.choices.append(claim.collection_point)
    if form.validate_on_submit():
        previous = claim.collection_point
        claim.collection_point = form.collection_point.data
        claim.handover_note = form.note.data.strip()
        audit(
            f"Collection details updated for claim #{claim.id}",
            "handover",
            claim.id,
            previous,
            claim.collection_point,
            claim.handover_note,
        )
        notify(
            claim.claimant_id,
            "Collection details updated",
            f"{claim.collection_point}: {claim.handover_note}",
            claim_id=claim.id,
        )
        db.session.commit()
        flash("Collection details saved and sent to the student.", "success")
        return redirect(url_for("claims.detail", claim_id=claim.id))
    return render_template("admin.html", section="handover", claim=claim, form=form)


@bp.get("/users")
@admin_required
def users():
    query = db.select(User).where(User.role == "student")
    q = request.args.get("q", "").strip()[:120]
    if q:
        term = "%" + q.replace("%", "\\%").replace("_", "\\_") + "%"
        query = query.where(
            or_(User.name.ilike(term, escape="\\"), User.email.ilike(term, escape="\\"))
        )
    if request.args.get("access") in {"enabled", "disabled"}:
        query = query.where(User.enabled.is_(request.args["access"] == "enabled"))
    page = db.paginate(query.order_by(User.created_at.desc()), per_page=20, error_out=False)
    return render_template("admin.html", section="users", page=page)


@bp.get("/users/<int:user_id>")
@admin_required
def student(user_id):
    user = db.get_or_404(User, user_id)
    if user.role != "student":
        abort(404)
    reports = db.session.scalars(
        db.select(Item).where(Item.owner_id == user.id).order_by(Item.created_at.desc())
    ).all()
    claims = db.session.scalars(
        db.select(Claim).where(Claim.claimant_id == user.id).order_by(Claim.created_at.desc())
    ).all()
    return render_template(
        "admin.html",
        section="student",
        student=user,
        reports=reports,
        claims=claims,
        form=AccessForm(),
    )


@bp.post("/users/<int:user_id>/toggle")
@admin_required
def toggle_user(user_id):
    user = db.get_or_404(User, user_id)
    if user.is_admin:
        abort(403)
    form = AccessForm()
    if form.validate_on_submit():
        previous = "enabled" if user.enabled else "disabled"
        user.enabled = not user.enabled
        next_state = "enabled" if user.enabled else "disabled"
        audit(
            f"Student #{user.id}: {next_state}",
            "student",
            user.id,
            previous,
            next_state,
            form.reason.data.strip(),
        )
        notify(user.id, "Account access updated", form.reason.data.strip())
        db.session.commit()
        flash("Student access updated. Their reports and history are preserved.", "success")
    else:
        flash("Please give a reason of at least 10 characters.", "error")
    return redirect(url_for("admin.student", user_id=user.id))


@bp.get("/analytics")
@admin_required
def analytics():
    data = analytics_data()
    return render_template("admin.html", section="analytics", **data)


@bp.get("/analytics/export/<format>")
@admin_required
def export(format):
    if format not in {"csv", "pdf"}:
        abort(404)
    from .exports import report_export

    data = analytics_data()
    response = report_export(data, format)
    audit(
        f"Analytics exported as {format.upper()}",
        "analytics",
        reason=f"{data['total']} matching report records; filters: {request.query_string.decode('utf-8', errors='replace')[:1000]}",
    )
    db.session.commit()
    return response


@bp.get("/activity")
@admin_required
def activity():
    query = db.select(Audit)
    if request.args.get("object_type"):
        query = query.where(Audit.object_type == request.args["object_type"])
    page = db.paginate(query.order_by(Audit.created_at.desc()), per_page=25, error_out=False)
    return render_template("admin.html", section="activity", page=page)


@bp.route("/settings", methods=["GET", "POST"])
@admin_required
def settings():
    values = campus_settings()
    form = SettingsForm()
    if request.method == "GET":
        for key, value in values.items():
            getattr(form, key).data = "\n".join(value) if isinstance(value, list) else value
    if form.validate_on_submit():
        updated = {
            key: [line.strip() for line in getattr(form, key).data.splitlines() if line.strip()]
            for key in ["categories", "locations", "collection_points"]
        }
        updated["handover_instructions"] = form.handover_instructions.data.strip()
        save_settings(updated)
        audit(
            "Campus settings updated",
            "settings",
            previous="previous configuration",
            next_status="updated configuration",
            reason=form.reason.data.strip() + " | " + str(updated),
        )
        db.session.commit()
        flash("Campus settings saved. Existing reports retain their original labels.", "success")
        return redirect(url_for("admin.settings"))
    return render_template("admin.html", section="settings", form=form)
