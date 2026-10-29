from datetime import date
import re

import pytest
from campusfind import create_app
from campusfind.models import Item, User, db


@pytest.fixture()
def app(tmp_path):
    app = create_app(
        {
            "TESTING": True,
            "SECRET_KEY": "test-key-only",
            "SQLALCHEMY_DATABASE_URI": f"sqlite:///{tmp_path / 'test.db'}",
            "UPLOAD_FOLDER": str(tmp_path / "uploads"),
        }
    )
    with app.app_context():
        db.create_all()
        for name, email, role in [
            ("Admin", "admin@example.com", "admin"),
            ("Finder", "finder@example.com", "student"),
            ("Owner", "owner@example.com", "student"),
            ("Other", "other@example.com", "student"),
        ]:
            user = User(name=name, email=email, role=role)
            user.set_password("TestingPass123!")
            db.session.add(user)
        db.session.flush()
        db.session.add_all(
            [
                Item(
                    owner_id=2,
                    kind="found",
                    title="Blue backpack",
                    description="A backpack found on the library desk.",
                    category="Bags",
                    location="Central Library",
                    event_date=date.today(),
                ),
                Item(
                    owner_id=3,
                    kind="lost",
                    title="Reading notebook",
                    description="A small notebook lost after class.",
                    category="Books",
                    location="Teaching Building",
                    event_date=date.today(),
                ),
            ]
        )
        db.session.commit()
    yield app
    with app.app_context():
        db.session.remove()
        db.drop_all()


@pytest.fixture()
def client(app):
    return app.test_client()


def token(client, path="/auth/login"):
    response = client.get(path)
    match = re.search(rb'name="csrf_token"[^>]*value="([^"]+)"', response.data)
    assert match, (path, response.status_code)
    return match[1].decode()


def login(client, email="owner@example.com"):
    path = "/auth/admin-login" if email == "admin@example.com" else "/auth/login"
    return client.post(
        path,
        data={"email": email, "password": "TestingPass123!", "csrf_token": token(client, path)},
        follow_redirects=True,
    )


def logout(client):
    return client.post("/auth/logout", data={"csrf_token": token(client, "/dashboard")})


def submit_claim(client, item=1):
    return client.post(
        f"/claims/item/{item}",
        data={
            "csrf_token": token(client, f"/items/{item}"),
            "evidence": "Private proof: a red notebook with initials inside the front pocket.",
        },
        follow_redirects=True,
    )


def review(client, action, claim=1):
    return client.post(
        f"/admin/claims/{claim}/review",
        data={
            "csrf_token": token(client, f"/claims/{claim}"),
            "action": action,
            "note": "Ownership details checked carefully by the campus desk.",
        },
        follow_redirects=True,
    )
