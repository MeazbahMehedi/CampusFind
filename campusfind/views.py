from flask import Blueprint, flash, redirect, render_template, url_for
from flask_login import current_user, login_required

from .models import Claim, Item, Notification, db

bp = Blueprint("views", __name__)


def visible_items():
    return db.select(Item).where(Item.is_hidden.is_(False))


def totals():
    return {
        key: db.session.scalar(
            db.select(db.func.count()).select_from(Item).where(Item.is_hidden.is_(False), condition)
        )
        for key, condition in {
            "lost": (Item.kind == "lost") & Item.status.in_(("reported", "claim_pending")),
            "found": (Item.kind == "found") & Item.status.in_(("reported", "claim_pending")),
            "returned": Item.status == "returned",
            "total": Item.id > 0,
        }.items()
    }


@bp.get("/")
def home():
    items = db.session.scalars(
        visible_items()
        .where(Item.status.in_(("reported", "claim_pending")))
        .order_by(Item.created_at.desc())
        .limit(6)
    ).all()
    return render_template("home.html", items=items, stats=totals())


@bp.get("/about")
def about():
    return render_template("about.html")


@bp.get("/dashboard")
@login_required
def dashboard():
    items = db.session.scalars(
        db.select(Item).where(Item.owner_id == current_user.id).order_by(Item.created_at.desc())
    ).all()
    claims = db.session.scalars(
        db.select(Claim)
        .where(Claim.claimant_id == current_user.id)
        .order_by(Claim.created_at.desc())
    ).all()
    notifications = db.session.scalars(
        db.select(Notification)
        .where(Notification.user_id == current_user.id)
        .order_by(Notification.created_at.desc())
        .limit(4)
    ).all()
    return render_template(
        "dashboard.html", items=items, claims=claims, notifications=notifications
    )


@bp.get("/notifications")
@login_required
def notifications():
    notices = db.session.scalars(
        db.select(Notification)
        .where(Notification.user_id == current_user.id)
        .order_by(Notification.created_at.desc())
    ).all()
    return render_template("notifications.html", notices=notices)


@bp.post("/notifications/read")
@login_required
def read_notifications():
    db.session.execute(
        db.update(Notification).where(Notification.user_id == current_user.id).values(is_read=True)
    )
    db.session.commit()
    flash("All notifications marked as read.", "success")
    return redirect(url_for("views.notifications"))
