from datetime import date

from flask_wtf import FlaskForm
from flask_wtf.file import FileAllowed, FileField
from wtforms import DateField, PasswordField, SelectField, StringField, TextAreaField
from wtforms.validators import DataRequired, Email, EqualTo, Length, ValidationError

from . import CATEGORIES, LOCATIONS


class RegisterForm(FlaskForm):
    name = StringField("Full name", validators=[DataRequired(), Length(min=2, max=100)])
    email = StringField("Email address", validators=[DataRequired(), Email(), Length(max=254)])
    password = PasswordField("Password", validators=[DataRequired(), Length(min=10, max=128)])
    confirm = PasswordField(
        "Confirm password",
        validators=[DataRequired(), EqualTo("password", message="Passwords must match.")],
    )


class LoginForm(FlaskForm):
    email = StringField("Email address", validators=[DataRequired(), Email(), Length(max=254)])
    password = PasswordField("Password", validators=[DataRequired(), Length(max=128)])


class ItemForm(FlaskForm):
    kind = SelectField(
        "Report type", choices=[("lost", "I lost something"), ("found", "I found something")]
    )
    title = StringField("Item name", validators=[DataRequired(), Length(min=3, max=120)])
    description = TextAreaField(
        "Description", validators=[DataRequired(), Length(min=15, max=3000)]
    )
    category = SelectField("Category", choices=CATEGORIES)
    location = SelectField("Campus location", choices=LOCATIONS)
    event_date = DateField("Date lost or found", validators=[DataRequired()], default=date.today)
    image = FileField(
        "Item photograph",
        validators=[
            FileAllowed(["jpg", "jpeg", "png", "webp"], "Choose a JPG, PNG, or WebP image.")
        ],
    )

    def validate_event_date(self, field):
        if field.data > date.today():
            raise ValidationError("The date cannot be in the future.")


class ClaimForm(FlaskForm):
    evidence = TextAreaField(
        "How can you prove this item is yours?",
        validators=[DataRequired(), Length(min=20, max=4000)],
    )


class MessageForm(FlaskForm):
    body = TextAreaField(
        "Additional information", validators=[DataRequired(), Length(min=10, max=4000)]
    )


class ReviewForm(FlaskForm):
    action = SelectField(
        "Decision",
        choices=[
            ("needs_info", "Request more information"),
            ("approve", "Approve claim"),
            ("reject", "Reject claim"),
            ("return", "Confirm physical handover"),
        ],
    )
    note = TextAreaField("Review note", validators=[DataRequired(), Length(min=10, max=2000)])


class ProfileForm(FlaskForm):
    name = StringField("Full name", validators=[DataRequired(), Length(min=2, max=100)])


class PasswordForm(FlaskForm):
    current = PasswordField("Current password", validators=[DataRequired(), Length(max=128)])
    password = PasswordField("New password", validators=[DataRequired(), Length(min=10, max=128)])
    confirm = PasswordField(
        "Confirm new password", validators=[DataRequired(), EqualTo("password")]
    )


class ModerateForm(FlaskForm):
    action = SelectField(
        "Action",
        choices=[
            ("hide", "Hide & close report"),
            ("restore", "Restore visibility"),
            ("close", "Close report"),
            ("reopen", "Reopen report"),
        ],
    )
    reason = TextAreaField("Reason", validators=[DataRequired(), Length(min=10, max=1000)])
