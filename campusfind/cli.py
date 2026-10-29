"""Explicit setup, sample data, and maintenance commands."""

from datetime import timedelta
from pathlib import Path
import json
import secrets

import click
from email_validator import EmailNotValidError, validate_email
from flask_migrate import upgrade

from .models import Claim, ClaimMessage, Item, ItemEvent, Notification, User, db, now


def register(app):
    @app.cli.command("init-db")
    def init_db():
        """Apply versioned database migrations (safe to repeat)."""
        upgrade(directory=str(Path(app.root_path).parent / "migrations"))
        click.echo("Database is ready.")

    @app.cli.command("configure-admin")
    def configure_admin():
        """Apply the private, one-time local administrator setup supplied with a ZIP."""
        path = Path(app.config["ADMIN_BOOTSTRAP_PATH"])
        if not path.is_file():
            raise click.ClickException(
                "No pending administrator setup. Use create-admin or reset-password."
            )
        try:
            settings = json.loads(path.read_text(encoding="utf-8"))
            email = validate_email(settings["email"], check_deliverability=False).normalized.lower()
            password_hash = settings["password_hash"]
            name = settings.get("name", "Campus Administrator").strip()
            if (
                not isinstance(password_hash, str)
                or not password_hash.startswith(("scrypt:", "pbkdf2:"))
                or not 2 <= len(name) <= 100
            ):
                raise ValueError("Invalid administrator setup")
        except (ValueError, KeyError, TypeError) as exc:
            raise click.ClickException("The local administrator setup file is invalid.") from exc
        user = db.session.scalar(db.select(User).where(User.email == email))
        if user is None:
            user = User(email=email, name=name)
            db.session.add(user)
        user.role = "admin"
        user.enabled = True
        user.password_hash = password_hash
        db.session.commit()
        # Consume the private setup so future runs do not reset a changed password.
        path.unlink()
        click.echo(
            f"Administrator configured: {email}. Use Login as Administrator with your chosen password."
        )

    @app.cli.command("create-admin")
    @click.option("--email", prompt=True)
    @click.option("--name", prompt=True)
    @click.password_option()
    def create_admin(email, name, password):
        """Create an administrator. Public registration always creates students."""
        try:
            email = validate_email(email, check_deliverability=False).normalized.lower()
        except EmailNotValidError as exc:
            raise click.ClickException(str(exc)) from exc
        if len(password) < 10 or len(password) > 128 or not 2 <= len(name.strip()) <= 100:
            raise click.ClickException(
                "Use a 2–100 character name and a 10–128 character password."
            )
        if db.session.scalar(db.select(User).where(User.email == email)):
            raise click.ClickException("This email already exists. Use another email.")
        user = User(name=name.strip(), email=email, role="admin")
        user.set_password(password)
        db.session.add(user)
        db.session.commit()
        click.echo("Administrator created.")

    @app.cli.command("reset-password")
    @click.option("--email", prompt=True)
    @click.password_option()
    def reset_password(email, password):
        """Local operator recovery; no email service is required."""
        user = db.session.scalar(db.select(User).where(User.email == email.strip().lower()))
        if not user or not 10 <= len(password) <= 128:
            raise click.ClickException("Check the email and use a 10–128 character password.")
        user.set_password(password)
        db.session.commit()
        click.echo("Password reset.")

    @app.cli.command("seed-demo")
    @click.option(
        "--password",
        default=None,
        help="Optional local-demo password (10+ characters). Otherwise one is generated.",
    )
    def seed_demo(password):
        """Load fictional examples into an empty database or an administrator-only database."""
        existing = db.session.scalars(db.select(User)).all()
        existing_admin = existing[0] if len(existing) == 1 and existing[0].is_admin else None
        if existing and not (
            existing_admin and not db.session.scalar(db.select(db.func.count()).select_from(Item))
        ):
            raise click.ClickException(
                "Demo seed requires an empty database; existing records were left untouched."
            )
        password = password or secrets.token_urlsafe(16)
        if not 10 <= len(password) <= 128:
            raise click.ClickException("Use a 10–128 character password.")
        users = []
        for name, email, role in [
            ("Campus Administrator", "admin@gmail.com", "admin"),
            ("Alex Morgan", "student@example.com", "student"),
            ("Sam Rivera", "finder@example.com", "student"),
            ("Jamie Chen", "jamie@example.com", "student"),
        ]:
            if role == "admin" and existing_admin:
                users.append(existing_admin)
                continue
            user = User(name=name, email=email, role=role)
            user.set_password(password)
            db.session.add(user)
            users.append(user)
        db.session.flush()
        samples = [
            (
                "found",
                "Midnight blue backpack",
                "Bags",
                "Central Library",
                "bag",
                "A navy backpack was handed in near the second-floor reading area. Describe the contents when claiming.",
            ),
            (
                "lost",
                "Wireless headphones",
                "Electronics",
                "Sports Center",
                "headphones",
                "Lost my over-ear headphones after an afternoon study session. Please report a found item if you have them.",
            ),
            (
                "found",
                "Keys with a green keyring",
                "Keys",
                "Campus Garden",
                "keys",
                "A small set of keys with a green loop, found on the bench beside the main garden path.",
            ),
            (
                "found",
                "Insulated water bottle",
                "Accessories",
                "Teaching Building",
                "bottle",
                "A light green insulated bottle was left near a lecture room. Identify a distinctive detail to claim it.",
            ),
            (
                "lost",
                "Introduction to Algorithms",
                "Books",
                "Central Library",
                "book",
                "A hardcover algorithms textbook with handwritten study notes tucked inside. Last seen at a library desk.",
            ),
            (
                "found",
                "Brown leather wallet",
                "Accessories",
                "Cafeteria",
                "wallet",
                "A brown wallet was found near the cafeteria entrance and handed to the campus desk. Contents are kept private.",
            ),
            (
                "found",
                "Student access card",
                "Cards & IDs",
                "Student Dormitory",
                "card",
                "An access card was handed in outside the dormitory. Personal details are withheld for ownership verification.",
            ),
            (
                "lost",
                "Scientific calculator",
                "Electronics",
                "Teaching Building",
                "calculator",
                "My scientific calculator went missing after class. It has a handwritten label on the back.",
            ),
            (
                "found",
                "Cream canvas tote",
                "Bags",
                "Cafeteria",
                "bag",
                "A cream tote with a simple print, found hanging on a chair. Tell us what was inside.",
            ),
            (
                "lost",
                "Green campus notebook",
                "Books",
                "Campus Garden",
                "book",
                "A small green notebook with lecture notes, possibly left near the fountain.",
            ),
            (
                "found",
                "Black over-ear headphones",
                "Electronics",
                "Central Library",
                "headphones",
                "Headphones found beside a computer station. Ownership will be verified before handover.",
            ),
            (
                "found",
                "Spare dormitory keys",
                "Keys",
                "Student Dormitory",
                "keys",
                "Two small keys found by the dormitory entrance. Describe the attached tag to verify ownership.",
            ),
            (
                "lost",
                "Blue gym bottle",
                "Accessories",
                "Sports Center",
                "bottle",
                "A blue reusable bottle lost near the changing rooms. Any help finding it would be appreciated.",
            ),
            (
                "found",
                "Engineering workbook",
                "Books",
                "Teaching Building",
                "book",
                "A workbook was found after a morning class. The name and notes can be used to verify ownership.",
            ),
            (
                "found",
                "Pocket card holder",
                "Cards & IDs",
                "Cafeteria",
                "wallet",
                "A compact card holder was handed to staff. Its contents will not be posted publicly.",
            ),
            (
                "lost",
                "Everyday reading glasses",
                "Accessories",
                "Central Library",
                "other",
                "Reading glasses in a soft fabric case, last seen near the ground-floor entrance.",
            ),
            (
                "found",
                "Silver calculator",
                "Electronics",
                "Teaching Building",
                "calculator",
                "A calculator found after an exam. A unique marking on the cover can help confirm its owner.",
            ),
            (
                "found",
                "Garden gate keyring",
                "Keys",
                "Campus Garden",
                "keys",
                "A keyring was returned to its verified owner through the campus help desk.",
            ),
        ]
        items = []
        for index, (kind, title, category, location, illustration, description) in enumerate(
            samples
        ):
            created = now() - timedelta(days=index % 7, hours=index)
            item = Item(
                owner_id=users[1 if index % 4 == 1 else 2].id,
                kind=kind,
                title=title,
                category=category,
                location=location,
                illustration=illustration,
                description=description,
                event_date=(created - timedelta(hours=3)).date(),
                created_at=created,
                updated_at=created,
            )
            db.session.add(item)
            db.session.flush()
            db.session.add(
                ItemEvent(
                    item_id=item.id, label=f"{kind.capitalize()} item reported.", created_at=created
                )
            )
            items.append(item)
        for index, status, evidence in [
            (
                0,
                "pending",
                "The front pocket contains a small red notebook with my initials on the first page.",
            ),
            (
                3,
                "needs_info",
                "The bottle has a distinctive sticker near its base. I can provide more details.",
            ),
            (
                10,
                "approved",
                "The left ear cushion has a tiny stitched repair and the case has a blue label.",
            ),
            (
                11,
                "returned",
                "The smaller key is engraved with a private number I have provided to the administrator.",
            ),
            (17, "returned", "I described the exact shape of the key tag to the help desk."),
        ]:
            item = items[index]
            claimant = users[1] if item.owner_id != users[1].id else users[3]
            claim = Claim(
                item_id=item.id, claimant_id=claimant.id, status=status, evidence=evidence
            )
            db.session.add(claim)
            db.session.flush()
            item.status = (
                "awaiting_handover"
                if status == "approved"
                else "returned"
                if status == "returned"
                else "claim_pending"
            )
            if status in {"approved", "returned"}:
                item.reserved_claim_id = claim.id
                claim.review_note = "Ownership evidence checked by the campus desk."
                claim.reviewed_by = users[0].id
                db.session.add(
                    ItemEvent(
                        item_id=item.id, label="Ownership verified. Awaiting physical handover."
                    )
                )
            if status == "returned":
                db.session.add(
                    ItemEvent(item_id=item.id, label="Physical handover confirmed. Item returned.")
                )
            if status == "needs_info":
                claim.review_note = (
                    "Please describe the sticker in more detail so we can verify ownership."
                )
                db.session.add(
                    ClaimMessage(claim_id=claim.id, author_id=users[0].id, body=claim.review_note)
                )
            db.session.add(
                Notification(
                    user_id=claimant.id,
                    title="Your claim was updated",
                    body=f"{item.title}: {status.replace('_', ' ')}.",
                    claim_id=claim.id,
                )
            )
        db.session.commit()
        click.echo("Fictional demo data loaded. These are not real campus reports.")
        click.echo("Student: student@example.com | Finder: finder@example.com")
        click.echo(f"Student demo password: {password}")
        if existing_admin:
            click.echo(
                f"Administrator: {existing_admin.email} — your existing password is unchanged."
            )
        else:
            click.echo(f"Administrator: admin@gmail.com | Demo password: {password}")

    @app.cli.command("reset-data")
    @click.confirmation_option(
        prompt="Delete ALL accounts, reports, claims, and uploads in this configured database?"
    )
    def reset_data():
        """Destructive local maintenance; retains schema and developer config."""
        for table in reversed(db.metadata.sorted_tables):
            db.session.execute(table.delete())
        db.session.commit()
        for file in Path(app.config["UPLOAD_FOLDER"]).glob("*.jpg"):
            file.unlink()
        click.echo("Application data cleared. Run create-admin or seed-demo next.")
