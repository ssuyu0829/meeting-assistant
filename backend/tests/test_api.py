"""最小回歸測試：註冊／登入、權限、以及會把 .env 送出去的路徑遍歷。

跑法（在 backend/ 底下）：
    SECRET_KEY=test-secret DATABASE_URL=sqlite:///./test.db pytest
"""
import os
import sys
import tempfile
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

BACKEND = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BACKEND))

os.environ.setdefault("SECRET_KEY", "test-secret")
TEST_DB = Path(tempfile.gettempdir()) / f"meeting_assistant_test_{os.getpid()}.db"
os.environ["DATABASE_URL"] = f"sqlite:///{TEST_DB}"

import main  # noqa: E402


@pytest.fixture(scope="session", autouse=True)
def cleanup_test_database():
    yield
    TEST_DB.unlink(missing_ok=True)


@pytest.fixture(scope="module")
def client():
    with TestClient(main.app) as c:
        yield c


def _register(client, email):
    r = client.post("/api/auth/register", json={"email": email, "name": email.split("@")[0], "password": "pw12345678"})
    assert r.status_code == 200, r.text
    return r.json()


def _auth(user):
    return {"Authorization": f"Bearer {user['token']}"}


def _create_group(client, user, name):
    r = client.post("/api/groups", json={"name": name}, headers=_auth(user))
    assert r.status_code == 200, r.text
    return r.json()


def test_register_then_login(client):
    email = "alice@example.com"
    created = _register(client, email)
    assert created["token"]

    r = client.post("/api/auth/login", json={"email": email, "password": "pw12345678"})
    assert r.status_code == 200
    assert r.json()["user_id"] == created["user_id"]

    r = client.post("/api/auth/login", json={"email": email, "password": "wrong-password"})
    assert r.status_code == 401


def test_non_member_cannot_read_group(client):
    owner = _register(client, "owner@example.com")
    outsider = _register(client, "outsider@example.com")

    r = client.post(
        "/api/groups",
        json={"name": "實驗室", "invitation_code": "lab-001"},
        headers={"Authorization": f"Bearer {owner['token']}"},
    )
    assert r.status_code == 200, r.text
    group_id = r.json()["id"]

    r = client.get(
        f"/api/meetings/folders/{group_id}",
        headers={"Authorization": f"Bearer {outsider['token']}"},
    )
    assert r.status_code == 403

    r = client.get(f"/api/meetings/folders/{group_id}")
    assert r.status_code == 403  # 沒帶 token


@pytest.mark.parametrize("path", [
    "/../backend/.env",
    "/%2e%2e/backend/.env",
    "/%2e%2e%2fbackend%2f.env",
    "/static/../../backend/.env",
])
def test_no_path_traversal(client, path):
    """靜態檔的 catch-all 只能回 frontend/ 底下的東西，其他一律回 index.html。"""
    r = client.get(path)
    assert r.status_code == 200
    assert "SECRET_KEY" not in r.text
    assert r.text.lstrip().startswith("<!DOCTYPE html>")


def test_healthz(client):
    assert client.get("/healthz").json() == {"ok": True}


def test_short_password_rejected(client):
    r = client.post("/api/auth/register", json={"email": "short@example.com", "name": "short", "password": "pw12"})
    assert r.status_code == 422


def test_invitation_code_is_server_generated(client):
    owner = _register(client, "codeowner@example.com")
    group = _create_group(client, owner, "碼組")
    # 使用者送什麼都不算，伺服器一律自己產生夠長的碼
    r = client.post("/api/groups", json={"name": "碼組二", "invitation_code": "lab-001"}, headers=_auth(owner))
    assert r.status_code == 200
    assert r.json()["invitation_code"] != "lab-001"
    assert len(r.json()["invitation_code"]) >= 12
    assert group["invitation_code"] != r.json()["invitation_code"]


def test_join_rate_limited_after_repeated_failures(client):
    user = _register(client, "guesser@example.com")
    codes = [f"no-such-code-{i}" for i in range(12)]
    statuses = [client.post("/api/groups/join", json={"invitation_code": c}, headers=_auth(user)).status_code
                for c in codes]
    assert statuses[0] == 404
    assert 429 in statuses


def test_non_member_cannot_touch_availability(client):
    """曾經的漏洞：availability 的兩個端點完全沒檢查成員身分。"""
    owner = _register(client, "lead@example.com")
    outsider = _register(client, "stranger@example.com")
    group = _create_group(client, owner, "時段組")

    r = client.post(
        "/api/meetings",
        json={"name": "週會", "group_id": group["id"], "dates": ["2026/10/01"]},
        headers=_auth(owner),
    )
    assert r.status_code == 200, r.text
    meeting_id = r.json()["id"]

    # 讀別人的時段表
    r = client.get(f"/api/availability/{meeting_id}", headers=_auth(outsider))
    assert r.status_code == 403, r.text

    # 往別人的會議塞時段
    r = client.post(
        f"/api/availability/{meeting_id}",
        json={"slots": {"2026/10/01": [1, 2]}},
        headers=_auth(outsider),
    )
    assert r.status_code == 403, r.text

    # 成員本人可以
    r = client.post(
        f"/api/availability/{meeting_id}",
        json={"slots": {"2026/10/01": [1, 2]}},
        headers=_auth(owner),
    )
    assert r.status_code == 200, r.text
    r = client.get(f"/api/availability/{meeting_id}", headers=_auth(owner))
    assert r.status_code == 200
    assert r.json()["submitted_members"] == ["lead"]


def _create_meeting(client, user, group_id, name="週會"):
    r = client.post(
        "/api/meetings",
        json={"name": name, "group_id": group_id, "dates": ["2026/10/01"]},
        headers=_auth(user),
    )
    assert r.status_code == 200, r.text
    return r.json()


def test_non_member_cannot_read_attendance_or_summary(client):
    """曾經的漏洞：attendance 與 summary 的 GET 只檢查會議存在，沒檢查成員身分。"""
    owner = _register(client, "att-owner@example.com")
    outsider = _register(client, "att-outsider@example.com")
    group = _create_group(client, owner, "出席組")
    meeting = _create_meeting(client, owner, group["id"])

    for path in (f"/api/records/{meeting['id']}/attendance", f"/api/records/{meeting['id']}/summary"):
        assert client.get(path, headers=_auth(outsider)).status_code == 403, path
        assert client.get(path, headers=_auth(owner)).status_code == 200, path


def test_attendance_rejects_invalid_status(client):
    """不合法的狀態字串要回 422，而不是進到 enum 轉換才炸 500。"""
    owner = _register(client, "att-enum@example.com")
    group = _create_group(client, owner, "狀態組")
    meeting = _create_meeting(client, owner, group["id"])

    r = client.post(
        f"/api/records/{meeting['id']}/attendance",
        json={"items": [{"user_id": owner["user_id"], "absence_status": "bogus"}]},
        headers=_auth(owner),
    )
    assert r.status_code == 422, r.text


def test_attendance_only_for_group_members(client):
    owner = _register(client, "att-lead@example.com")
    stranger = _register(client, "att-stranger@example.com")
    group = _create_group(client, owner, "名單組")
    meeting = _create_meeting(client, owner, group["id"])

    r = client.post(
        f"/api/records/{meeting['id']}/attendance",
        json={"items": [{"user_id": stranger["user_id"], "absence_status": "ontime"}]},
        headers=_auth(owner),
    )
    assert r.status_code == 403, r.text


def test_attendance_roundtrip_to_summary(client):
    owner = _register(client, "att-round@example.com")
    group = _create_group(client, owner, "總結組")
    meeting = _create_meeting(client, owner, group["id"])

    r = client.post(
        f"/api/records/{meeting['id']}/attendance",
        json={"items": [{"user_id": owner["user_id"], "absence_status": "late", "mission_status": "done"}]},
        headers=_auth(owner),
    )
    assert r.status_code == 200, r.text

    r = client.get(f"/api/records/{meeting['id']}/attendance", headers=_auth(owner))
    assert r.json() == [{
        "user_id": owner["user_id"], "name": "att-round",
        "absence_status": "late", "mission_status": "done",
    }]

    summary = client.get(f"/api/records/{meeting['id']}/summary", headers=_auth(owner)).json()
    assert summary["meeting_name"] == "週會"
    assert summary["late"] == ["att-round"]
    assert summary["done"] == ["att-round"]
    assert summary["ontime"] == [] and summary["absent"] == []
