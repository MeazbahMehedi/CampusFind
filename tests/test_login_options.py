import json

from werkzeug.security import generate_password_hash

from campusfind import create_app
from campusfind.models import User, db
from conftest import token


def post_login(client, path, email, password="TestingPass123!"):
    return client.post(
        path, data={"email": email, "password": password, "csrf_token": token(client, path)}
    )


def test_login_choices_are_visible(client):
    for path in ["/auth/login", "/auth/admin-login"]:
        response = client.get(path)
        assert response.status_code == 200
        assert b"Login as Student" in response.data
        assert b"Login as Administrator" in response.data
    assert "/auth/admin-login" in client.get("/admin").location


def test_admin_sign_in_lands_in_console(client):
    response = post_login(client, "/auth/admin-login", "admin@example.com")
    assert response.status_code == 302
    assert response.location == "/admin"
    assert b"Campus control room" in client.get("/admin").data


def test_student_sign_in_lands_in_dashboard(client):
    response = post_login(client, "/auth/login", "owner@example.com")
    assert response.location == "/dashboard"


def test_student_cannot_use_admin_login(client):
    response = post_login(client, "/auth/admin-login", "owner@example.com")
    assert response.status_code == 200
    assert b"Use Login as Student" in response.data
    with client.session_transaction() as session:
        assert "_user_id" not in session


def test_admin_must_use_admin_choice(client):
    response = post_login(client, "/auth/login", "admin@example.com")
    assert b"Use Login as Administrator" in response.data
    with client.session_transaction() as session:
        assert "_user_id" not in session


def test_role_field_does_not_grant_admin(client):
    response = client.post(
        "/auth/admin-login",
        data={
            "email": "owner@example.com",
            "password": "TestingPass123!",
            "role": "admin",
            "csrf_token": token(client, "/auth/admin-login"),
        },
    )
    assert b"Use Login as Student" in response.data
    assert client.get("/admin").status_code == 302


def test_admin_csrf_and_safe_redirect(client):
    assert (
        client.post(
            "/auth/admin-login", data={"email": "admin@example.com", "password": "TestingPass123!"}
        ).status_code
        == 400
    )
    response = post_login(client, "/auth/admin-login?next=https://example.org", "admin@example.com")
    assert response.location == "/admin"


def test_about_has_only_current_people_and_service_copy(client):
    response = client.get("/about")
    assert b"Meazbah Mehedi" in response.data and b"Monika" in response.data
    assert response.data.count(b"Developer &amp; Designer") == 2
    assert b"Built with Python" not in response.data
    assert b"This version does not include" not in response.data
    assert b"FELIX" not in response.data and b"JAMES" not in response.data


def test_one_time_admin_provisioning_preserves_existing_data(tmp_path):
    pending = tmp_path / "admin-bootstrap.json"
    chosen = "ConfiguredOnly123!"
    pending.write_text(
        json.dumps(
            {
                "email": "admin@gmail.com",
                "name": "Campus Administrator",
                "password_hash": generate_password_hash(chosen),
            }
        )
    )
    app = create_app(
        {
            "TESTING": True,
            "SQLALCHEMY_DATABASE_URI": f"sqlite:///{tmp_path / 'bootstrap.db'}",
            "UPLOAD_FOLDER": str(tmp_path / "uploads"),
            "ADMIN_BOOTSTRAP_PATH": str(pending),
        }
    )
    runner = app.test_cli_runner()
    assert runner.invoke(args=["init-db"]).exit_code == 0
    assert runner.invoke(args=["configure-admin"]).exit_code == 0
    assert not pending.exists()
    result = runner.invoke(args=["seed-demo", "--password", "StudentDemo123!"])
    assert result.exit_code == 0, result.output
    with app.app_context():
        admin = db.session.scalar(db.select(User).where(User.email == "admin@gmail.com"))
        assert admin.is_admin and admin.check_password(chosen)
        assert not admin.check_password("StudentDemo123!")
        count = db.session.scalar(db.select(db.func.count()).select_from(User))
    # Reapply a newly supplied private setup to an existing account, without clearing records.
    pending.write_text(
        json.dumps(
            {"email": "admin@gmail.com", "password_hash": generate_password_hash("Replacement123!")}
        )
    )
    assert runner.invoke(args=["configure-admin"]).exit_code == 0
    with app.app_context():
        assert db.session.scalar(db.select(db.func.count()).select_from(User)) == count
        assert db.session.scalar(
            db.select(User).where(User.email == "admin@gmail.com")
        ).check_password("Replacement123!")
    assert runner.invoke(args=["configure-admin"]).exit_code != 0
