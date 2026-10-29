"""Database records; claim evidence is never part of public item content."""

from datetime import datetime, timezone

from flask_login import UserMixin
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import UniqueConstraint
from werkzeug.security import check_password_hash, generate_password_hash

db = SQLAlchemy()


def now():
    return datetime.now(timezone.utc).replace(tzinfo=None)


class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(254), unique=True, nullable=False, index=True)
    password_hash = db.Column(db.String(256), nullable=False)
    role = db.Column(db.String(20), nullable=False, default="student")
    enabled = db.Column(db.Boolean, nullable=False, default=True)
    created_at = db.Column(db.DateTime, nullable=False, default=now)

    @property
    def is_active(self):
        return self.enabled

    @property
    def is_admin(self):
        return self.role == "admin"

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)


class Item(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    owner_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False, index=True)
    owner = db.relationship("User", foreign_keys=[owner_id])
    kind = db.Column(db.String(10), nullable=False)
    title = db.Column(db.String(120), nullable=False)
    description = db.Column(db.Text, nullable=False)
    category = db.Column(db.String(40), nullable=False, index=True)
    location = db.Column(db.String(100), nullable=False, index=True)
    event_date = db.Column(db.Date, nullable=False, index=True)
    image = db.Column(db.String(120))
    illustration = db.Column(db.String(30), default="other")
    status = db.Column(db.String(30), nullable=False, default="reported", index=True)
    review_status = db.Column(db.String(30), nullable=False, default="pending", index=True)
    review_note = db.Column(db.Text, nullable=False, default="")
    reviewed_by = db.Column(db.Integer, db.ForeignKey("user.id"))
    reviewed_at = db.Column(db.DateTime)
    is_hidden = db.Column(db.Boolean, nullable=False, default=False)
    # The approved claim reserves an item; it does not confirm physical handover.
    reserved_claim_id = db.Column(db.Integer, nullable=True)
    created_at = db.Column(db.DateTime, nullable=False, default=now)
    updated_at = db.Column(db.DateTime, nullable=False, default=now, onupdate=now)
    events = db.relationship("ItemEvent", backref="item", order_by="ItemEvent.created_at")
    claims = db.relationship("Claim", backref="item")


class Claim(db.Model):
    __table_args__ = (UniqueConstraint("item_id", "claimant_id", name="uq_claim_item_user"),)
    id = db.Column(db.Integer, primary_key=True)
    item_id = db.Column(db.Integer, db.ForeignKey("item.id"), nullable=False, index=True)
    claimant_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False, index=True)
    claimant = db.relationship("User", foreign_keys=[claimant_id])
    evidence = db.Column(db.Text, nullable=False)
    status = db.Column(db.String(30), nullable=False, default="pending", index=True)
    review_note = db.Column(db.Text, default="")
    reviewed_by = db.Column(db.Integer, db.ForeignKey("user.id"))
    created_at = db.Column(db.DateTime, nullable=False, default=now)
    updated_at = db.Column(db.DateTime, nullable=False, default=now, onupdate=now)
    messages = db.relationship("ClaimMessage", backref="claim", order_by="ClaimMessage.created_at")
    collection_point = db.Column(db.String(100), nullable=False, default="")
    handover_note = db.Column(db.Text, nullable=False, default="")
    returned_at = db.Column(db.DateTime)


class ClaimMessage(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    claim_id = db.Column(db.Integer, db.ForeignKey("claim.id"), nullable=False)
    author_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False)
    author = db.relationship("User")
    body = db.Column(db.Text, nullable=False)
    created_at = db.Column(db.DateTime, nullable=False, default=now)


class ItemEvent(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    item_id = db.Column(db.Integer, db.ForeignKey("item.id"), nullable=False)
    label = db.Column(db.String(200), nullable=False)
    created_at = db.Column(db.DateTime, nullable=False, default=now)


class Notification(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False, index=True)
    title = db.Column(db.String(180), nullable=False)
    body = db.Column(db.Text, nullable=False)
    claim_id = db.Column(db.Integer, db.ForeignKey("claim.id"))
    item_id = db.Column(db.Integer, db.ForeignKey("item.id"))
    is_read = db.Column(db.Boolean, nullable=False, default=False)
    created_at = db.Column(db.DateTime, nullable=False, default=now)


class Audit(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    actor_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False)
    actor = db.relationship("User")
    action = db.Column(db.Text, nullable=False)
    object_type = db.Column(db.String(30), nullable=False, default="general")
    object_id = db.Column(db.Integer)
    previous_status = db.Column(db.String(80), nullable=False, default="")
    next_status = db.Column(db.String(80), nullable=False, default="")
    reason = db.Column(db.Text, nullable=False, default="")
    created_at = db.Column(db.DateTime, nullable=False, default=now)


class LoginAttempt(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    identity = db.Column(db.String(64), nullable=False, index=True)
    created_at = db.Column(db.DateTime, nullable=False, default=now, index=True)


class CampusSetting(db.Model):
    key = db.Column(db.String(50), primary_key=True)
    value = db.Column(db.Text, nullable=False)


class ReportReview(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    item_id = db.Column(db.Integer, db.ForeignKey("item.id"), nullable=False, index=True)
    actor_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False)
    actor = db.relationship("User")
    action = db.Column(db.String(30), nullable=False)
    note = db.Column(db.Text, nullable=False)
    created_at = db.Column(db.DateTime, nullable=False, default=now)
