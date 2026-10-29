from datetime import date
from io import BytesIO
import csv

import pytest
from pypdf import PdfReader
from sqlalchemy import text
from werkzeug.security import generate_password_hash

from campusfind import create_app
from campusfind.models import Audit, Claim, Item, ReportReview, User, db
from conftest import login, logout, review, submit_claim, token


def moderate(client, action, item=1):
    return client.post(
        f"/admin/reports/{item}/moderate",
        data={
            "csrf_token": token(client, f"/items/{item}"),
            "action": action,
            "reason": "Checked the report and recorded the management decision.",
        },
        follow_redirects=True,
    )


def report_data(client, title="Green campus folder"):
    return {
        "csrf_token": token(client, "/items/new"),
        "kind": "found",
        "title": title,
        "description": "A folder found beside the second floor library reading desk.",
        "category": "Bags",
        "location": "Central Library",
        "event_date": date.today().isoformat(),
    }


@pytest.mark.parametrize(
    "method,path",
    [
        ("get", "/items/new"),
        ("get", "/items/1/edit"),
        ("post", "/items/new"),
        ("post", "/items/1/edit"),
        ("post", "/items/1/close"),
        ("post", "/claims/item/1"),
        ("post", "/claims/1/message"),
        ("post", "/claims/1/withdraw"),
    ],
)
def test_admin_cannot_perform_student_actions(client, method, path):
    login(client, "admin@example.com")
    response = getattr(client, method)(
        path, **({"data": {"csrf_token": token(client, "/admin")}} if method == "post" else {})
    )
    assert response.status_code == 403


def test_admin_workspace_has_management_navigation(client):
    login(client, "admin@example.com")
    response = client.get("/admin")
    assert b"Management" in response.data or b"MANAGEMENT" in response.data
    for label in [
        "Item reports",
        "Ownership claims",
        "Handovers",
        "Students",
        "Analytics &amp; exports",
        "Activity log",
        "Campus settings",
    ]:
        assert label.encode() in response.data
    assert b">Report an item</a>" not in response.data
    assert b">My dashboard</a>" not in response.data
    assert client.get("/dashboard").location == "/admin"
    assert client.get("/").location == "/admin"
    assert b"Submit ownership claim" not in client.get("/items/1").data


def test_new_report_requires_publication_approval(client, app):
    login(client, "finder@example.com")
    response = client.post("/items/new", data=report_data(client), follow_redirects=True)
    assert b"not public yet" in response.data
    with app.app_context():
        item = db.session.scalar(db.select(Item).where(Item.title == "Green campus folder"))
        item_id = item.id
        assert item.review_status == "pending"
    logout(client)
    assert client.get(f"/items/{item_id}").status_code == 404
    assert b"Green campus folder" not in client.get("/items").data
    login(client, "owner@example.com")
    assert client.get(f"/items/{item_id}").status_code == 404
    assert (
        client.post(
            f"/claims/item/{item_id}",
            data={
                "csrf_token": token(client, "/dashboard"),
                "evidence": "My identifying details are in the folder.",
            },
        ).status_code
        == 404
    )
    logout(client)
    login(client, "admin@example.com")
    moderate(client, "approve", item_id)
    logout(client)
    assert client.get(f"/items/{item_id}").status_code == 200
    assert b"Green campus folder" in client.get("/items").data


def test_request_corrections_resubmit_and_approve(client, app):
    login(client, "admin@example.com")
    moderate(client, "needs_changes")
    with app.app_context():
        assert db.session.get(Item, 1).review_status == "needs_changes"
    logout(client)
    login(client, "finder@example.com")
    response = client.post(
        "/items/1/edit",
        data=report_data(client, "Blue backpack, corrected description"),
        follow_redirects=True,
    )
    assert b"resubmitted" in response.data
    with app.app_context():
        assert db.session.get(Item, 1).review_status == "pending"
    logout(client)
    login(client, "admin@example.com")
    moderate(client, "approve")
    with app.app_context():
        assert db.session.get(Item, 1).review_status == "approved"
        assert db.session.scalar(db.select(db.func.count()).select_from(ReportReview)) == 2


def test_editing_published_report_hides_it_until_rereview(client, app):
    login(client, "finder@example.com")
    data = report_data(client, "Updated private backpack title")
    client.post("/items/1/edit", data=data)
    logout(client)
    assert client.get("/items/1").status_code == 404
    assert b"Updated private backpack title" not in client.get("/").data


def test_rejection_and_reopening_preserve_decisions(client, app):
    with app.app_context():
        db.session.get(Item, 1).review_status = "pending"
        db.session.commit()
    login(client, "admin@example.com")
    moderate(client, "reject")
    with app.app_context():
        item = db.session.get(Item, 1)
        assert item.review_status == "rejected" and item.status == "closed"
    moderate(client, "reopen")
    with app.app_context():
        item = db.session.get(Item, 1)
        assert item.review_status == "pending" and item.status == "reported"
    moderate(client, "approve")
    with app.app_context():
        assert db.session.get(Item, 1).review_status == "approved"


def test_close_reopen_does_not_restore_claims_or_count_return(client, app):
    login(client)
    submit_claim(client)
    logout(client)
    login(client, "admin@example.com")
    review(client, "approve")
    moderate(client, "close")
    moderate(client, "reopen")
    with app.app_context():
        assert db.session.get(Item, 1).status == "reported"
        assert db.session.get(Claim, 1).status == "rejected"
        assert db.session.get(Item, 1).reserved_claim_id is None
        assert (
            db.session.scalar(
                db.select(db.func.count()).select_from(Item).where(Item.status == "returned")
            )
            == 0
        )
        entry = db.session.scalar(
            db.select(Audit).where(Audit.object_type == "report").order_by(Audit.id.desc())
        )
        assert entry.previous_status == "approved/closed"
        assert entry.next_status == "approved/reported"
        assert entry.reason


def test_confirmed_return_cannot_be_reopened(client, app):
    login(client)
    submit_claim(client)
    logout(client)
    login(client, "admin@example.com")
    review(client, "approve")
    review(client, "return")
    moderate(client, "reopen")
    with app.app_context():
        assert db.session.get(Item, 1).status == "returned"
        assert db.session.get(Claim, 1).returned_at is not None


def test_handover_collection_details_notify_student(client, app):
    login(client)
    submit_claim(client)
    logout(client)
    login(client, "admin@example.com")
    review(client, "approve")
    response = client.post(
        "/admin/handovers/1",
        data={
            "csrf_token": token(client, "/admin/handovers/1"),
            "collection_point": "Central Library Reception",
            "note": "Collect on Friday afternoon and bring your student identification.",
        },
        follow_redirects=True,
    )
    assert b"Central Library Reception" in response.data
    with app.app_context():
        assert db.session.get(Claim, 1).collection_point == "Central Library Reception"
        assert db.session.get(Item, 1).status == "awaiting_handover"
    logout(client)
    login(client)
    assert b"Friday afternoon" in client.get("/claims/1").data


def test_student_access_reason_and_history(client, app):
    login(client, "admin@example.com")
    client.post(
        "/admin/users/2/toggle",
        data={"csrf_token": token(client, "/admin/users/2"), "reason": "short"},
    )
    with app.app_context():
        assert db.session.get(User, 2).enabled
    response = client.post(
        "/admin/users/2/toggle",
        data={
            "csrf_token": token(client, "/admin/users/2"),
            "reason": "Suspended pending campus account verification.",
        },
        follow_redirects=True,
    )
    assert b"Suspended" in response.data
    assert b"Blue backpack" in response.data
    with app.app_context():
        assert db.session.get(Item, 1) is not None
        entry = db.session.scalar(db.select(Audit).where(Audit.object_type == "student"))
        assert entry.previous_status == "enabled" and entry.next_status == "disabled"


def test_settings_update_choices_and_preserve_historical_labels(client, app):
    login(client, "admin@example.com")
    values = {
        "csrf_token": token(client, "/admin/settings"),
        "categories": "Electronics\nStationery",
        "locations": "North Library\nMain Gate",
        "collection_points": "Student Services Desk",
        "handover_instructions": "Bring your student ID and arrange a collection time in advance.",
        "reason": "Update campus labels for the new teaching term.",
    }
    response = client.post("/admin/settings", data=values, follow_redirects=True)
    assert b"Campus settings saved" in response.data
    logout(client)
    login(client, "finder@example.com")
    form = client.get("/items/new").data
    assert b"Stationery" in form and b"North Library" in form
    assert b"Bags" in client.get("/items/1/edit").data
    with app.app_context():
        assert db.session.get(Item, 1).category == "Bags"


def test_settings_reject_duplicate_or_oversized_options(client):
    login(client, "admin@example.com")
    response = client.post(
        "/admin/settings",
        data={
            "csrf_token": token(client, "/admin/settings"),
            "categories": "Books\nbooks",
            "locations": "Library",
            "collection_points": "Help Desk",
            "handover_instructions": "Collect your verified item from the campus help desk.",
            "reason": "Testing duplicate category validation.",
        },
    )
    assert b"Remove duplicate entries" in response.data


@pytest.mark.parametrize(
    "path", ["/admin/handovers", "/admin/users/2", "/admin/analytics", "/admin/settings"]
)
def test_new_management_screens(client, path):
    login(client, "admin@example.com")
    assert client.get(path).status_code == 200


@pytest.mark.parametrize(
    "path",
    [
        "/admin/analytics/export/csv",
        "/admin/analytics/export/pdf",
        "/admin/settings",
        "/admin/handovers",
    ],
)
def test_management_requires_admin(client, path):
    login(client)
    assert client.get(path).status_code == 403


def test_exports_apply_filters_and_keep_claim_evidence_private(client, app):
    with app.app_context():
        db.session.get(Item, 1).title = "=Unsafe spreadsheet expression"
        db.session.commit()
    login(client, "admin@example.com")
    response = client.get("/admin/analytics/export/csv?kind=found")
    assert response.status_code == 200
    rows = list(csv.reader(response.data.decode("utf-8-sig").splitlines()))
    assert len(rows) == 2
    assert rows[1][1].startswith("'=")
    assert "Reading notebook" not in response.data.decode("utf-8-sig")
    assert "evidence" not in response.data.decode("utf-8-sig").lower()
    pdf = client.get("/admin/analytics/export/pdf?kind=found")
    assert pdf.status_code == 200 and pdf.data.startswith(b"%PDF")
    reader = PdfReader(BytesIO(pdf.data))
    content = "\n".join(page.extract_text() for page in reader.pages)
    assert "Unsafe spreadsheet" in content and "Reading notebook" not in content
    assert b"no-store" in pdf.headers["Cache-Control"].encode()


def test_upgrade_from_v11_preserves_reports_claims_and_audit(tmp_path):
    app = create_app(
        {
            "TESTING": True,
            "SQLALCHEMY_DATABASE_URI": f"sqlite:///{tmp_path / 'legacy.db'}",
            "UPLOAD_FOLDER": str(tmp_path / "uploads"),
        }
    )
    runner = app.test_cli_runner()
    assert runner.invoke(args=["db", "upgrade", "8ee7acbbad66"]).exit_code == 0
    with app.app_context():
        db.session.execute(
            text(
                "INSERT INTO user (id,name,email,password_hash,role,enabled,created_at) VALUES (1,'Legacy Student','legacy@example.com',:hash,'student',1,'2026-10-20 12:00:00')"
            ),
            {"hash": generate_password_hash("LegacyPass123!")},
        )
        db.session.execute(
            text(
                "INSERT INTO item (id,owner_id,kind,title,description,category,location,event_date,status,is_hidden,created_at,updated_at) VALUES (1,1,'found','Legacy bag','Preserve this historical report.','Bags','Central Library','2026-10-20','reported',0,'2026-10-20 12:00:00','2026-10-20 12:00:00')"
            )
        )
        db.session.execute(
            text(
                "INSERT INTO audit (actor_id,action,created_at) VALUES (1,'Legacy moderation entry','2026-10-20 12:00:00')"
            )
        )
        db.session.execute(
            text(
                "INSERT INTO claim (item_id,claimant_id,evidence,status,created_at,updated_at) VALUES (1,1,'Historical private evidence','rejected','2026-10-20 12:00:00','2026-10-20 12:00:00')"
            )
        )
        db.session.commit()
    result = runner.invoke(args=["init-db"])
    assert result.exit_code == 0, result.output
    with app.app_context():
        assert db.session.get(Item, 1).title == "Legacy bag"
        assert db.session.get(Item, 1).review_status == "approved"
        assert db.session.get(Claim, 1).evidence == "Historical private evidence"
        assert db.session.get(Audit, 1).action == "Legacy moderation entry"
        fresh = Item(
            owner_id=1,
            kind="lost",
            title="New report",
            description="New report description.",
            category="Bags",
            location="Central Library",
            event_date=date.today(),
        )
        db.session.add(fresh)
        db.session.commit()
        assert fresh.review_status == "pending"
