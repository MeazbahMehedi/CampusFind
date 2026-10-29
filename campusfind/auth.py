from datetime import timedelta
import hashlib
from urllib.parse import urlsplit

from flask import Blueprint, flash, redirect, render_template, request, session, url_for
from flask_login import current_user, login_required, login_user, logout_user
from sqlalchemy.exc import IntegrityError

from .forms import LoginForm, PasswordForm, ProfileForm, RegisterForm
from .models import LoginAttempt, User, db, now

bp = Blueprint("auth", __name__, url_prefix="/auth")


@bp.route("/register", methods=["GET", "POST"])
def register():
    if current_user.is_authenticated:
        return redirect(url_for("admin.overview" if current_user.is_admin else "views.dashboard"))
    form = RegisterForm()
    if form.validate_on_submit():
        user = User(name=form.name.data.strip(), email=form.email.data.strip().lower())
        user.set_password(form.password.data)
        db.session.add(user)
        try:
            db.session.commit()
        except IntegrityError:
            db.session.rollback()
            form.email.errors.append("That email is already registered. Please sign in.")
        else:
            login_user(user)
            session.permanent = True
            flash("Your account is ready. Welcome to CampusFind!", "success")
            return redirect(url_for("views.dashboard"))
    return render_template("auth.html", form=form, register=True)


@bp.route("/login", methods=["GET", "POST"])
def login():
    return sign_in("student")


@bp.route("/admin-login", methods=["GET", "POST"])
def admin_login():
    return sign_in("admin")


def sign_in(required_role):
    """The selected route validates an existing role; it never assigns one."""
    if current_user.is_authenticated:
        return redirect(url_for("admin.overview" if current_user.is_admin else "views.dashboard"))
    form = LoginForm()
    if form.validate_on_submit():
        email = form.email.data.strip().lower()
        identity = hashlib.sha256(email.encode()).hexdigest()
        cutoff = now() - timedelta(minutes=15)
        db.session.execute(db.delete(LoginAttempt).where(LoginAttempt.created_at < cutoff))
        count = db.session.scalar(
            db.select(db.func.count())
            .select_from(LoginAttempt)
            .where(LoginAttempt.identity == identity)
        )
        if count >= 8:
            db.session.commit()
            flash("Too many attempts for this account. Try again in 15 minutes.", "error")
            return render_template(
                "auth.html", form=form, register=False, login_role=required_role
            ), 429
        user = db.session.scalar(db.select(User).where(User.email == email))
        if user and user.enabled and user.check_password(form.password.data):
            if user.role != required_role:
                db.session.commit()
                form.email.errors.append(
                    "Use Login as Administrator for this account."
                    if user.is_admin
                    else "Use Login as Student for this account."
                )
                return render_template(
                    "auth.html", form=form, register=False, login_role=required_role
                )
            db.session.execute(db.delete(LoginAttempt).where(LoginAttempt.identity == identity))
            db.session.commit()
            session.clear()
            login_user(user)
            session.permanent = True
            target = request.args.get("next", "")
            parts = urlsplit(target)
            if (
                not target.startswith("/")
                or target.startswith("//")
                or parts.scheme
                or parts.netloc
                or "\\" in target
            ):
                target = ""
            if target and required_role == "student" and target.startswith("/admin"):
                target = ""
            if not target:
                target = url_for("admin.overview" if user.is_admin else "views.dashboard")
            return redirect(target)
        db.session.add(LoginAttempt(identity=identity))
        db.session.commit()
        form.password.errors.append("Email or password is incorrect, or the account is disabled.")
    return render_template("auth.html", form=form, register=False, login_role=required_role)


@bp.post("/logout")
@login_required
def logout():
    logout_user()
    session.clear()
    return redirect(url_for("views.home"))


@bp.route("/profile", methods=["GET", "POST"])
@login_required
def profile():
    form = ProfileForm(obj=current_user)
    password_form = PasswordForm()
    if request.form.get("section") == "profile" and form.validate_on_submit():
        current_user.name = form.name.data.strip()
        db.session.commit()
        flash("Profile updated.", "success")
        return redirect(url_for("auth.profile"))
    if request.form.get("section") == "password" and password_form.validate_on_submit():
        if not current_user.check_password(password_form.current.data):
            password_form.current.errors.append("Your current password is incorrect.")
        else:
            current_user.set_password(password_form.password.data)
            db.session.commit()
            flash("Password changed.", "success")
            return redirect(url_for("auth.profile"))
    return render_template("profile.html", form=form, password_form=password_form)
