from datetime import date, timedelta
from io import BytesIO

from PIL import Image
import pytest

from campusfind.models import Audit, Claim, Item, Notification, User, db
from conftest import login, logout, review, submit_claim, token


@pytest.mark.parametrize(
    "path", ["/", "/items", "/about", "/auth/login", "/auth/register", "/items/1"]
)
def test_public_pages(client, path):
    assert client.get(path).status_code == 200


@pytest.mark.parametrize(
    "path", ["/dashboard", "/notifications", "/admin", "/items/new", "/auth/profile"]
)
def test_login_required(client, path):
    assert client.get(path).status_code == 302


def test_csrf_and_registration_role(client, app):
    assert client.post("/auth/register", data={"name": "Evil"}).status_code == 400
    response = client.post(
        "/auth/register",
        data={
            "csrf_token": token(client, "/auth/register"),
            "name": "New Student",
            "email": "new@example.com",
            "password": "StudentPass123!",
            "confirm": "StudentPass123!",
            "role": "admin",
        },
        follow_redirects=True,
    )
    assert response.status_code == 200
    with app.app_context():
        assert (
            db.session.scalar(db.select(User).where(User.email == "new@example.com")).role
            == "student"
        )
    assert client.get("/admin").status_code == 403


def test_duplicate_email_and_password_validation(client):
    response = client.post(
        "/auth/register",
        data={
            "csrf_token": token(client, "/auth/register"),
            "name": "New Student",
            "email": "owner@example.com",
            "password": "StudentPass123!",
            "confirm": "StudentPass123!",
        },
        follow_redirects=True,
    )
    assert b"already registered" in response.data
    response = client.post(
        "/auth/register",
        data={
            "csrf_token": token(client, "/auth/register"),
            "name": "New Student",
            "email": "new@example.com",
            "password": "short",
            "confirm": "different",
        },
        follow_redirects=True,
    )
    assert b"Passwords must match" in response.data


def test_student_permissions(client):
    login(client)
    assert client.get("/admin").status_code == 403
    assert (
        client.post(
            "/admin/users/2/toggle", data={"csrf_token": token(client, "/dashboard")}
        ).status_code
        == 403
    )
    assert client.get("/items/1/edit").status_code == 403


def test_full_claim_review_and_return(client, app):
    login(client)
    assert b"Claim #0001" in submit_claim(client).data
    with app.app_context():
        assert db.session.get(Item, 1).status == "claim_pending"
    logout(client)
    login(client, "admin@example.com")
    assert b"Claim review recorded" in review(client, "needs_info").data
    logout(client)
    login(client)
    response = client.post(
        "/claims/1/message",
        data={
            "csrf_token": token(client, "/claims/1"),
            "body": "The notebook is red and the first page contains my initials.",
        },
        follow_redirects=True,
    )
    assert b"sent for review" in response.data
    logout(client)
    login(client, "admin@example.com")
    review(client, "approve")
    with app.app_context():
        assert db.session.get(Item, 1).status == "awaiting_handover"
        assert db.session.get(Claim, 1).status == "approved"
        assert db.session.get(Item, 1).reserved_claim_id == 1
    review(client, "return")
    with app.app_context():
        assert db.session.get(Item, 1).status == "returned"
        assert db.session.get(Claim, 1).status == "returned"
        assert db.session.scalar(db.select(db.func.count()).select_from(Audit)) == 3
        assert db.session.scalar(db.select(db.func.count()).select_from(Notification)) >= 4


def test_claim_evidence_is_private(client):
    login(client)
    submit_claim(client)
    assert b"Private proof" not in client.get("/items/1").data
    logout(client)
    login(client, "finder@example.com")
    assert client.get("/claims/1").status_code == 403
    logout(client)
    login(client, "other@example.com")
    assert client.get("/claims/1").status_code == 403


def test_duplicate_and_self_claim(client, app):
    login(client)
    submit_claim(client)
    submit_claim(client)
    with app.app_context():
        assert db.session.scalar(db.select(db.func.count()).select_from(Claim)) == 1
    logout(client)
    login(client, "finder@example.com")
    assert (
        client.post(
            "/claims/item/1",
            data={"csrf_token": token(client, "/items/1"), "evidence": "This is my own report."},
        ).status_code
        == 403
    )


def test_cannot_claim_lost_report(client, app):
    login(client, "other@example.com")
    submit_claim(client, 2)
    with app.app_context():
        assert db.session.scalar(db.select(db.func.count()).select_from(Claim)) == 0


def test_only_one_claim_approved(client, app):
    login(client)
    submit_claim(client)
    logout(client)
    login(client, "other@example.com")
    submit_claim(client)
    logout(client)
    login(client, "admin@example.com")
    review(client, "approve")
    with app.app_context():
        assert db.session.get(Claim, 1).status == "approved"
        assert db.session.get(Claim, 2).status == "rejected"
    review(client, "approve", 2)
    with app.app_context():
        assert db.session.get(Item, 1).reserved_claim_id == 1


def test_cannot_return_unapproved_claim(client, app):
    login(client)
    submit_claim(client)
    logout(client)
    login(client, "admin@example.com")
    assert b"Only the approved claim" in review(client, "return").data
    with app.app_context():
        assert db.session.get(Item, 1).status == "claim_pending"


def test_withdraw_refreshes_report(client, app):
    login(client)
    submit_claim(client)
    client.post("/claims/1/withdraw", data={"csrf_token": token(client, "/claims/1")})
    with app.app_context():
        assert db.session.get(Item, 1).status == "reported"
        assert db.session.get(Claim, 1).status == "withdrawn"


def test_admin_cannot_submit_claim(client, app):
    login(client, "admin@example.com")
    response = client.post(
        "/claims/item/1",
        data={
            "csrf_token": token(client, "/items/1"),
            "evidence": "A claim is a student-only action.",
        },
    )
    assert response.status_code == 403
    with app.app_context():
        assert db.session.scalar(db.select(db.func.count()).select_from(Claim)) == 0


def test_hide_cancels_claims_and_enforces_visibility(client, app):
    login(client)
    submit_claim(client)
    logout(client)
    login(client, "admin@example.com")
    client.post(
        "/admin/reports/1/moderate",
        data={
            "csrf_token": token(client, "/items/1"),
            "action": "hide",
            "reason": "Duplicate report confirmed by the administrator.",
        },
    )
    with app.app_context():
        assert db.session.get(Item, 1).is_hidden
        assert db.session.get(Claim, 1).status == "rejected"
    logout(client)
    assert client.get("/items/1").status_code == 404
    assert b"Blue backpack" not in client.get("/items").data


def test_disable_account_revokes_existing_session(client, app):
    login(client)
    with app.app_context():
        db.session.get(User, 3).enabled = False
        db.session.commit()
    assert client.get("/dashboard").status_code == 302


def test_login_throttle_and_safe_next(client):
    for i in range(8):
        response = client.post(
            "/auth/login",
            data={
                "csrf_token": token(client),
                "email": "owner@example.com",
                "password": "incorrect",
            },
        )
        assert response.status_code == 200
    assert (
        client.post(
            "/auth/login",
            data={
                "csrf_token": token(client),
                "email": "owner@example.com",
                "password": "TestingPass123!",
            },
        ).status_code
        == 429
    )


def test_external_login_redirect_is_ignored(client):
    response = client.post(
        "/auth/login?next=https://evil.example",
        data={
            "csrf_token": token(client),
            "email": "owner@example.com",
            "password": "TestingPass123!",
        },
    )
    assert response.location == "/dashboard"


def test_photo_validation_and_future_date(client, app):
    login(client, "finder@example.com")
    base = {
        "kind": "found",
        "title": "Pocket notebook",
        "description": "A notebook found after a lecture.",
        "category": "Books",
        "location": "Central Library",
        "event_date": date.today().isoformat(),
    }
    response = client.post(
        "/items/new",
        data={
            **base,
            "csrf_token": token(client, "/items/new"),
            "image": (BytesIO(b"not-an-image"), "picture.png"),
        },
        content_type="multipart/form-data",
    )
    assert b"not a supported" in response.data
    response = client.post(
        "/items/new",
        data={
            **base,
            "event_date": (date.today() + timedelta(days=1)).isoformat(),
            "csrf_token": token(client, "/items/new"),
        },
    )
    assert b"cannot be in the future" in response.data
    image = BytesIO()
    Image.new("RGB", (100, 100), "green").save(image, "PNG")
    image.seek(0)
    response = client.post(
        "/items/new",
        data={**base, "csrf_token": token(client, "/items/new"), "image": (image, "picture.png")},
        content_type="multipart/form-data",
    )
    assert response.status_code == 302
    with app.app_context():
        item = db.session.scalar(db.select(Item).where(Item.title == "Pocket notebook"))
        assert item.image.endswith(".jpg")
        photo = item.image
    assert client.get("/items/images/" + photo).status_code == 200
    logout(client)
    login(client, "admin@example.com")
    client.post(
        f"/admin/reports/{item.id}/moderate",
        data={
            "csrf_token": token(client, f"/items/{item.id}"),
            "action": "hide",
            "reason": "Testing image visibility protection.",
        },
    )
    logout(client)
    assert client.get("/items/images/" + photo).status_code == 404


def test_filters_and_sql_wildcards(client):
    assert b"Blue backpack" in client.get("/items?q=backpack&category=Bags&kind=found").data
    assert b"Blue backpack" not in client.get("/items?category=Books").data
    assert b"No matching reports" in client.get("/items?q=%25").data
    assert b"valid date" in client.get("/items?from_date=invalid").data


def test_notifications_are_user_scoped(client, app):
    login(client)
    submit_claim(client)
    client.post("/notifications/read", data={"csrf_token": token(client, "/notifications")})
    with app.app_context():
        notices = db.session.scalars(db.select(Notification).where(Notification.user_id == 3)).all()
        assert all(n.is_read for n in notices)
        assert (
            db.session.scalar(db.select(Notification).where(Notification.user_id == 2)).is_read
            is False
        )


@pytest.mark.parametrize(
    "path", ["/admin", "/admin/reports", "/admin/claims", "/admin/users", "/admin/activity"]
)
def test_admin_screens(client, path):
    login(client, "admin@example.com")
    assert client.get(path).status_code == 200


def test_migrations_and_demo_commands(tmp_path):
    from campusfind import create_app

    app = create_app(
        {
            "TESTING": True,
            "SQLALCHEMY_DATABASE_URI": f"sqlite:///{tmp_path / 'migrated.db'}",
            "UPLOAD_FOLDER": str(tmp_path / "files"),
        }
    )
    runner = app.test_cli_runner()
    assert runner.invoke(args=["init-db"]).exit_code == 0
    assert runner.invoke(args=["init-db"]).exit_code == 0
    result = runner.invoke(args=["seed-demo", "--password", "TestingPass123!"])
    assert result.exit_code == 0, result.output
    assert runner.invoke(args=["seed-demo"]).exit_code != 0
    with app.app_context():
        assert db.session.scalar(db.select(db.func.count()).select_from(Item)) == 18
    assert runner.invoke(args=["reset-data"], input="n\n").exit_code != 0
    assert runner.invoke(args=["reset-data", "--yes"]).exit_code == 0
    with app.app_context():
        assert db.session.scalar(db.select(db.func.count()).select_from(User)) == 0
