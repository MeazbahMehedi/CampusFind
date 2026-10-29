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

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        from .settings import campus_settings

        values = campus_settings()
        for field, key in [(self.category, "categories"), (self.location, "locations")]:
            choices = list(values[key])
            obj = kwargs.get("obj")
            previous = getattr(obj, field.name, None) if obj else None
            if previous and previous not in choices:
                choices.append(previous)
            field.choices = choices

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
            ("approve", "Approve report for publication"),
            ("needs_changes", "Request corrections from student"),
            ("reject", "Reject report"),
            ("hide", "Hide & close report"),
            ("restore", "Restore visibility"),
            ("close", "Close report"),
            ("reopen", "Reopen report"),
        ],
    )
    reason = TextAreaField("Reason", validators=[DataRequired(), Length(min=10, max=1000)])


class AccessForm(FlaskForm):
    reason = TextAreaField(
        "Reason for access change", validators=[DataRequired(), Length(min=10, max=1000)]
    )


class HandoverForm(FlaskForm):
    collection_point = SelectField("Collection point", validators=[DataRequired()])
    note = TextAreaField(
        "Collection instructions", validators=[DataRequired(), Length(min=10, max=2000)]
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        from .settings import campus_settings

        self.collection_point.choices = list(campus_settings()["collection_points"])


class SettingsForm(FlaskForm):
    categories = TextAreaField("Item categories", validators=[DataRequired(), Length(max=2000)])
    locations = TextAreaField("Campus locations", validators=[DataRequired(), Length(max=4000)])
    collection_points = TextAreaField(
        "Collection points", validators=[DataRequired(), Length(max=3000)]
    )
    handover_instructions = TextAreaField(
        "Default collection instructions", validators=[DataRequired(), Length(min=20, max=2000)]
    )
    reason = TextAreaField(
        "Reason for settings change", validators=[DataRequired(), Length(min=10, max=1000)]
    )

    def validate_list(self, field, maximum_length):
        values = [line.strip() for line in field.data.splitlines() if line.strip()]
        if not 1 <= len(values) <= 30 or any(len(value) > maximum_length for value in values):
            raise ValidationError(
                f"Use 1–30 entries, one per line, each at most {maximum_length} characters."
            )
        if len({value.casefold() for value in values}) != len(values):
            raise ValidationError("Remove duplicate entries.")

    def validate_categories(self, field):
        self.validate_list(field, 40)

    def validate_locations(self, field):
        self.validate_list(field, 100)

    def validate_collection_points(self, field):
        self.validate_list(field, 100)
