from datetime import date
from pathlib import Path

from flask import (
    Blueprint,
    abort,
    current_app,
    flash,
    redirect,
    render_template,
    request,
    send_from_directory,
    url_for,
)
from flask_login import current_user, login_required
from sqlalchemy import or_

from .forms import ClaimForm, ItemForm, ModerateForm
from .models import Claim, Item, db
from .services import ACTIVE_CLAIMS, close_report, event, save_image

bp = Blueprint("reports", __name__, url_prefix="/items")


def get_visible(item_id):
    item = db.get_or_404(Item, item_id)
    if item.is_hidden and not (
        current_user.is_authenticated
        and (current_user.is_admin or item.owner_id == current_user.id)
    ):
        abort(404)
    return item


@bp.get("")
def browse():
    query = db.select(Item).where(Item.is_hidden.is_(False))
    q = request.args.get("q", "").strip()[:120]
    if q:
        escaped = q.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")
        term = f"%{escaped}%"
        query = query.where(
            or_(Item.title.ilike(term, escape="\\"), Item.description.ilike(term, escape="\\"))
        )
    for field in ("kind", "category", "location", "status"):
        value = request.args.get(field, "")
        if value:
            query = query.where(getattr(Item, field) == value)
    for field, lower in (("from_date", True), ("to_date", False)):
        value = request.args.get(field)
        if value:
            try:
                parsed = date.fromisoformat(value)
            except ValueError:
                flash("Please use a valid date in the filters.", "error")
            else:
                query = query.where(
                    Item.event_date >= parsed if lower else Item.event_date <= parsed
                )
    sort = request.args.get("sort", "newest")
    query = query.order_by(
        Item.created_at.asc() if sort == "oldest" else Item.created_at.desc(), Item.id.desc()
    )
    page = db.paginate(
        query, page=request.args.get("page", 1, type=int), per_page=9, error_out=False
    )
    filters = request.args.to_dict()
    filters.pop("page", None)
    return render_template("browse.html", page=page, filters=filters)


@bp.route("/new", methods=["GET", "POST"])
@login_required
def create():
    form = ItemForm()
    if request.method == "GET" and request.args.get("kind") in {"lost", "found"}:
        form.kind.data = request.args["kind"]
    if form.validate_on_submit():
        filename = None
        if form.image.data:
            try:
                filename = save_image(form.image.data)
            except ValueError as exc:
                form.image.errors.append(str(exc))
                return render_template("item_form.html", form=form, editing=False)
        item = Item(
            owner_id=current_user.id,
            kind=form.kind.data,
            title=form.title.data.strip(),
            description=form.description.data.strip(),
            category=form.category.data,
            location=form.location.data,
            event_date=form.event_date.data,
            image=filename,
        )
        db.session.add(item)
        db.session.flush()
        event(item, f"{item.kind.capitalize()} item reported.")
        db.session.commit()
        flash("Your report is live. Thank you for helping your campus.", "success")
        return redirect(url_for("reports.detail", item_id=item.id))
    return render_template("item_form.html", form=form, editing=False)


@bp.get("/<int:item_id>")
def detail(item_id):
    item = get_visible(item_id)
    own_claim = None
    if current_user.is_authenticated:
        own_claim = db.session.scalar(
            db.select(Claim).where(Claim.item_id == item.id, Claim.claimant_id == current_user.id)
        )
    return render_template(
        "item_detail.html",
        item=item,
        form=ClaimForm(),
        own_claim=own_claim,
        moderate_form=ModerateForm(),
    )


@bp.route("/<int:item_id>/edit", methods=["GET", "POST"])
@login_required
def edit(item_id):
    item = get_visible(item_id)
    if item.owner_id != current_user.id:
        abort(403)
    if (
        item.is_hidden
        or item.status != "reported"
        or any(claim.status in ACTIVE_CLAIMS for claim in item.claims)
    ):
        flash("This report cannot be edited while hidden, closed, or under claim review.", "error")
        return redirect(url_for("reports.detail", item_id=item.id))
    form = ItemForm(obj=item)
    if form.validate_on_submit():
        # Report type cannot change after publication.
        if form.kind.data != item.kind:
            form.kind.errors.append("The report type cannot be changed after publication.")
        else:
            filename = None
            if form.image.data:
                try:
                    filename = save_image(form.image.data)
                except ValueError as exc:
                    form.image.errors.append(str(exc))
                    return render_template("item_form.html", form=form, editing=True, item=item)
            for field in ["title", "description", "category", "location", "event_date"]:
                value = getattr(form, field).data
                setattr(item, field, value.strip() if isinstance(value, str) else value)
            old_image = item.image
            if filename:
                item.image = filename
            event(item, "Report details updated.")
            db.session.commit()
            if filename and old_image:
                (Path(current_app.config["UPLOAD_FOLDER"]) / old_image).unlink(missing_ok=True)
            flash("Report updated.", "success")
            return redirect(url_for("reports.detail", item_id=item.id))
    return render_template("item_form.html", form=form, editing=True, item=item)


@bp.post("/<int:item_id>/close")
@login_required
def close(item_id):
    item = get_visible(item_id)
    if item.owner_id != current_user.id:
        abort(403)
    if (
        item.status != "reported"
        or item.is_hidden
        or any(c.status in ACTIVE_CLAIMS for c in item.claims)
    ):
        flash(
            "Only an open report without active claims can be closed here. Contact an administrator for help.",
            "error",
        )
    else:
        close_report(item, "Closed by the report author.")
        db.session.commit()
        flash("Your report is closed.", "success")
    return redirect(url_for("reports.detail", item_id=item.id))


@bp.get("/images/<filename>")
def image(filename):
    item = db.session.scalar(db.select(Item).where(Item.image == filename))
    if not item:
        abort(404)
    get_visible(item.id)
    response = send_from_directory(
        current_app.config["UPLOAD_FOLDER"], filename, mimetype="image/jpeg"
    )
    response.headers["Cache-Control"] = "private, no-store"
    return response
