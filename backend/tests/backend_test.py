"""
Go Farm Work - Comprehensive Backend API Test Suite
Covers: auth, reference data, jobs, proposals, contracts, milestones,
messages, reviews, notifications, saved jobs, maps, admin, RBAC, and _id leaks.
"""
import os
import time
import uuid
import pytest
import requests

BASE_URL = os.environ.get("REACT_APP_BACKEND_URL", "https://find-farm-work-now.preview.emergentagent.com").rstrip("/")
API = f"{BASE_URL}/api"

RUN = uuid.uuid4().hex[:8]
OWNER_EMAIL = f"TEST_owner_{RUN}@test.com"
PARTNER_EMAIL = f"TEST_partner_{RUN}@test.com"
PWD = "Test@1234"
ADMIN_EMAIL = "admin@gofarmwork.in"
ADMIN_PWD = "Admin@123"

state = {}  # shared across tests in order


def _hdr(tok):
    return {"Authorization": f"Bearer {tok}", "Content-Type": "application/json"}


# ---------- Health & Reference ----------
def test_health():
    r = requests.get(f"{API}/health", timeout=15)
    assert r.status_code == 200
    assert r.json().get("ok") is True


def test_districts_seeded():
    r = requests.get(f"{API}/locations/districts", timeout=15)
    assert r.status_code == 200
    data = r.json()
    assert isinstance(data, list) and len(data) >= 10
    assert "_id" not in data[0]
    assert "district_id" in data[0] and "name" in data[0]
    state["district_id"] = data[0]["district_id"]
    # Use Mysuru for location tests
    mysuru = next((d for d in data if d["name"] == "Mysuru"), data[0])
    state["mysuru_id"] = mysuru["district_id"]


def test_taluks_by_district():
    r = requests.get(f"{API}/locations/taluks", params={"district_id": state["mysuru_id"]}, timeout=15)
    assert r.status_code == 200
    data = r.json()
    assert isinstance(data, list)
    if data:
        assert "taluk_id" in data[0]
        state["taluk_id"] = data[0]["taluk_id"]


def test_villages_by_taluk():
    if "taluk_id" not in state:
        pytest.skip("No taluk seeded")
    r = requests.get(f"{API}/locations/villages", params={"taluk_id": state["taluk_id"]}, timeout=15)
    assert r.status_code == 200
    assert isinstance(r.json(), list)


def test_categories():
    r = requests.get(f"{API}/categories", timeout=15)
    assert r.status_code == 200
    data = r.json()
    assert len(data) >= 20
    # NOTE: schema inconsistency — categories use 'id' while districts use 'district_id'
    cid_key = "category_id" if "category_id" in data[0] else "id"
    state["category_id"] = data[0][cid_key]


def test_crops_and_skills():
    r1 = requests.get(f"{API}/crops", timeout=15)
    r2 = requests.get(f"{API}/skills", timeout=15)
    assert r1.status_code == 200 and r2.status_code == 200
    assert isinstance(r1.json(), list) and isinstance(r2.json(), list)


# ---------- Auth ----------
def test_admin_login():
    r = requests.post(f"{API}/auth/login", json={"email": ADMIN_EMAIL, "password": ADMIN_PWD}, timeout=15)
    assert r.status_code == 200, r.text
    data = r.json()
    assert data["user"]["role"] == "admin"
    assert "password_hash" not in data["user"]
    state["admin_token"] = data["token"]


def test_signup_owner():
    r = requests.post(f"{API}/auth/signup", json={
        "email": OWNER_EMAIL, "password": PWD, "full_name": "Test Owner"
    }, timeout=15)
    assert r.status_code == 200, r.text
    data = r.json()
    assert data["token"]
    assert data["user"]["email"] == OWNER_EMAIL.lower()
    assert "password_hash" not in data["user"]
    state["owner_token"] = data["token"]
    state["owner_id"] = data["user"]["user_id"]


def test_signup_partner():
    r = requests.post(f"{API}/auth/signup", json={
        "email": PARTNER_EMAIL, "password": PWD, "full_name": "Test Partner"
    }, timeout=15)
    assert r.status_code == 200, r.text
    state["partner_token"] = r.json()["token"]
    state["partner_id"] = r.json()["user"]["user_id"]


def test_signup_duplicate_rejected():
    r = requests.post(f"{API}/auth/signup", json={
        "email": OWNER_EMAIL, "password": PWD, "full_name": "Dup"
    }, timeout=15)
    assert r.status_code == 400


def test_login_invalid():
    r = requests.post(f"{API}/auth/login", json={"email": OWNER_EMAIL, "password": "wrong"}, timeout=15)
    assert r.status_code == 401


def test_auth_me_owner():
    r = requests.get(f"{API}/auth/me", headers=_hdr(state["owner_token"]), timeout=15)
    assert r.status_code == 200
    assert r.json()["email"] == OWNER_EMAIL.lower()
    assert "password_hash" not in r.json()


def test_auth_me_no_token():
    r = requests.get(f"{API}/auth/me", timeout=15)
    assert r.status_code in (401, 403)


def test_set_role_owner():
    r = requests.patch(f"{API}/auth/role", json={"role": "farm_owner"},
                       headers=_hdr(state["owner_token"]), timeout=15)
    assert r.status_code == 200
    assert r.json()["role"] == "farm_owner"


def test_onboarding_owner():
    r = requests.post(f"{API}/auth/onboarding", json={
        "role": "farm_owner", "full_name": "Test Owner", "phone": "9999999999",
        "district": "Mysuru", "preferred_language": "en",
        "farm_name": "Test Farm", "main_crops": ["paddy"], "farm_type": "organic",
    }, headers=_hdr(state["owner_token"]), timeout=15)
    assert r.status_code == 200
    assert r.json()["onboarded"] is True
    assert r.json()["role"] == "farm_owner"


def test_onboarding_partner():
    r = requests.post(f"{API}/auth/onboarding", json={
        "role": "farm_partner", "full_name": "Test Partner", "phone": "8888888888",
        "district": "Mysuru", "preferred_language": "kn",
        "skills": ["harvesting"], "work_categories": ["cat_01"], "availability": "full_time",
    }, headers=_hdr(state["partner_token"]), timeout=15)
    assert r.status_code == 200
    assert r.json()["role"] == "farm_partner"


# ---------- Jobs ----------
def test_partner_cannot_post_job():
    r = requests.post(f"{API}/jobs", json={
        "title": "Should fail", "description": "x", "category_id": state["category_id"],
        "budget_type": "fixed",
    }, headers=_hdr(state["partner_token"]), timeout=15)
    assert r.status_code == 403


def test_create_job_as_owner():
    payload = {
        "title": "TEST Paddy harvesting",
        "description": "Need 5 workers for 3 days",
        "category_id": state["category_id"],
        "crop_type": "paddy", "work_type": "harvesting",
        "budget_type": "fixed", "budget_min": 5000, "budget_max": 8000,
        "urgency": "urgent", "district": "Mysuru", "workers_needed": 5,
    }
    r = requests.post(f"{API}/jobs", json=payload, headers=_hdr(state["owner_token"]), timeout=15)
    assert r.status_code == 200, r.text
    job = r.json()
    assert job["title"] == payload["title"]
    assert job["owner_user_id"] == state["owner_id"]
    assert "_id" not in job
    state["job_id"] = job["job_id"]


def test_publish_job():
    r = requests.post(f"{API}/jobs/{state['job_id']}/publish",
                      headers=_hdr(state["owner_token"]), timeout=15)
    assert r.status_code == 200
    # Verify persisted
    r2 = requests.get(f"{API}/jobs/{state['job_id']}", timeout=15)
    assert r2.status_code == 200
    assert r2.json()["job"]["status"] == "published"


def test_list_jobs_with_filter():
    r = requests.get(f"{API}/jobs", params={"district": "Mysuru", "urgency": "urgent"}, timeout=15)
    assert r.status_code == 200
    jobs = r.json()
    assert any(j["job_id"] == state["job_id"] for j in jobs)
    assert all("_id" not in j for j in jobs)


def test_jobs_mine_owner():
    r = requests.get(f"{API}/jobs/mine", headers=_hdr(state["owner_token"]), timeout=15)
    assert r.status_code == 200
    assert any(j["job_id"] == state["job_id"] for j in r.json())


def test_jobs_nearby():
    r = requests.get(f"{API}/jobs/nearby", params={"district": "Mysuru"}, timeout=15)
    assert r.status_code == 200


def test_jobs_recommended_partner():
    r = requests.get(f"{API}/jobs/recommended", headers=_hdr(state["partner_token"]), timeout=15)
    assert r.status_code == 200


def test_save_job_toggle():
    r1 = requests.post(f"{API}/jobs/{state['job_id']}/save",
                       headers=_hdr(state["partner_token"]), timeout=15)
    assert r1.status_code == 200 and r1.json()["saved"] is True
    r2 = requests.get(f"{API}/saved/jobs", headers=_hdr(state["partner_token"]), timeout=15)
    assert any(j["job_id"] == state["job_id"] for j in r2.json())
    r3 = requests.post(f"{API}/jobs/{state['job_id']}/save",
                       headers=_hdr(state["partner_token"]), timeout=15)
    assert r3.json()["saved"] is False


# ---------- Proposals ----------
def test_submit_proposal():
    r = requests.post(f"{API}/jobs/{state['job_id']}/proposals", json={
        "bid_amount": 6500, "message": "I can do this job",
        "estimated_days": 3, "availability_date": "2026-05-01",
    }, headers=_hdr(state["partner_token"]), timeout=15)
    assert r.status_code == 200, r.text
    p = r.json()
    assert p["status"] == "pending"
    assert "_id" not in p
    state["proposal_id"] = p["proposal_id"]


def test_proposal_duplicate():
    r = requests.post(f"{API}/jobs/{state['job_id']}/proposals", json={
        "bid_amount": 7000, "message": "again"
    }, headers=_hdr(state["partner_token"]), timeout=15)
    assert r.status_code == 400


def test_owner_cannot_propose():
    r = requests.post(f"{API}/jobs/{state['job_id']}/proposals", json={
        "bid_amount": 100, "message": "x"
    }, headers=_hdr(state["owner_token"]), timeout=15)
    assert r.status_code == 403


def test_list_proposals_for_owner():
    r = requests.get(f"{API}/jobs/{state['job_id']}/proposals",
                     headers=_hdr(state["owner_token"]), timeout=15)
    assert r.status_code == 200
    props = r.json()
    assert len(props) >= 1
    assert props[0].get("partner") is not None
    assert "email" not in props[0]["partner"]


def test_list_proposals_forbidden_for_partner():
    r = requests.get(f"{API}/jobs/{state['job_id']}/proposals",
                     headers=_hdr(state["partner_token"]), timeout=15)
    assert r.status_code == 403


def test_proposals_mine():
    r = requests.get(f"{API}/proposals/mine", headers=_hdr(state["partner_token"]), timeout=15)
    assert r.status_code == 200
    assert any(p["proposal_id"] == state["proposal_id"] for p in r.json())


def test_accept_proposal_creates_contract():
    r = requests.post(f"{API}/proposals/{state['proposal_id']}/accept",
                      headers=_hdr(state["owner_token"]), timeout=15)
    assert r.status_code == 200, r.text
    c = r.json()
    assert c["status"] == "active"
    assert c["partner_user_id"] == state["partner_id"]
    state["contract_id"] = c["contract_id"]
    # Verify job is in_progress
    time.sleep(0.5)
    j = requests.get(f"{API}/jobs/{state['job_id']}", timeout=15).json()["job"]
    assert j["status"] == "in_progress"


# ---------- Contracts & Milestones ----------
def test_list_contracts_both_sides():
    r1 = requests.get(f"{API}/contracts", headers=_hdr(state["owner_token"]), timeout=15)
    r2 = requests.get(f"{API}/contracts", headers=_hdr(state["partner_token"]), timeout=15)
    assert r1.status_code == 200 and r2.status_code == 200
    assert any(c["contract_id"] == state["contract_id"] for c in r1.json())
    assert any(c["contract_id"] == state["contract_id"] for c in r2.json())


def test_contract_detail():
    r = requests.get(f"{API}/contracts/{state['contract_id']}",
                     headers=_hdr(state["owner_token"]), timeout=15)
    assert r.status_code == 200
    assert "milestones" in r.json()


def test_add_milestone_owner_only():
    r_bad = requests.post(f"{API}/contracts/{state['contract_id']}/milestones", json={
        "title": "m1", "amount": 3000
    }, headers=_hdr(state["partner_token"]), timeout=15)
    assert r_bad.status_code == 403

    r = requests.post(f"{API}/contracts/{state['contract_id']}/milestones", json={
        "title": "Phase 1", "description": "First half", "amount": 3000
    }, headers=_hdr(state["owner_token"]), timeout=15)
    assert r.status_code == 200
    ms = r.json()
    assert ms["status"] == "pending"
    state["milestone_id"] = ms["milestone_id"]


def test_fund_approve_release_milestone():
    r1 = requests.post(f"{API}/milestones/{state['milestone_id']}/fund",
                       headers=_hdr(state["owner_token"]), timeout=15)
    assert r1.status_code == 200
    assert r1.json()["order_id"].startswith("order_")

    r2 = requests.post(f"{API}/milestones/{state['milestone_id']}/approve",
                       headers=_hdr(state["owner_token"]), timeout=15)
    assert r2.status_code == 200

    r3 = requests.post(f"{API}/milestones/{state['milestone_id']}/release",
                       headers=_hdr(state["owner_token"]), timeout=15)
    assert r3.status_code == 200

    # verify milestone state
    c = requests.get(f"{API}/contracts/{state['contract_id']}",
                     headers=_hdr(state["owner_token"]), timeout=15).json()
    ms = next(m for m in c["milestones"] if m["milestone_id"] == state["milestone_id"])
    assert ms["status"] == "released"


def test_payment_history():
    r = requests.get(f"{API}/payments/history", headers=_hdr(state["owner_token"]), timeout=15)
    assert r.status_code == 200
    assert len(r.json()) >= 1
    assert all("_id" not in p for p in r.json())


# ---------- Messages ----------
def test_open_chat_and_messages():
    r = requests.post(f"{API}/chats", json={
        "other_user_id": state["partner_id"], "job_id": state["job_id"]
    }, headers=_hdr(state["owner_token"]), timeout=15)
    assert r.status_code == 200
    thread_id = r.json()["thread_id"]
    state["thread_id"] = thread_id

    # Idempotent retrieve
    r2 = requests.post(f"{API}/chats", json={
        "other_user_id": state["partner_id"], "job_id": state["job_id"]
    }, headers=_hdr(state["owner_token"]), timeout=15)
    assert r2.json()["thread_id"] == thread_id

    # Send message
    rm = requests.post(f"{API}/chats/{thread_id}/messages", json={"text": "Hello partner"},
                       headers=_hdr(state["owner_token"]), timeout=15)
    assert rm.status_code == 200

    # Fetch
    rg = requests.get(f"{API}/chats/{thread_id}/messages",
                      headers=_hdr(state["partner_token"]), timeout=15)
    assert rg.status_code == 200
    assert any(m["text"] == "Hello partner" for m in rg.json())


# ---------- Reviews ----------
def test_create_and_list_reviews():
    r = requests.post(f"{API}/reviews", json={
        "reviewee_user_id": state["partner_id"],
        "contract_id": state["contract_id"], "rating": 5, "comment": "Great work"
    }, headers=_hdr(state["owner_token"]), timeout=15)
    assert r.status_code == 200

    r2 = requests.get(f"{API}/reviews/{state['partner_id']}", timeout=15)
    assert r2.status_code == 200
    assert len(r2.json()) >= 1


# ---------- Notifications ----------
def test_notifications_flow():
    r = requests.get(f"{API}/notifications", headers=_hdr(state["partner_token"]), timeout=15)
    assert r.status_code == 200
    notifs = r.json()
    # Partner should have at least 'proposal_accepted' notif
    assert any(n["type"] == "proposal_accepted" for n in notifs)
    if notifs:
        nid = notifs[0]["notif_id"]
        rr = requests.patch(f"{API}/notifications/{nid}/read",
                            headers=_hdr(state["partner_token"]), timeout=15)
        assert rr.status_code == 200


# ---------- Maps (mock) ----------
def test_maps_autocomplete():
    r = requests.get(f"{API}/maps/autocomplete", params={"q": "Mys"}, timeout=15)
    assert r.status_code == 200
    assert isinstance(r.json(), list)


def test_maps_nearby_jobs():
    r = requests.get(f"{API}/maps/nearby-jobs", timeout=15)
    assert r.status_code == 200
    jobs = r.json()
    if jobs:
        assert "lat" in jobs[0] and "lng" in jobs[0]


# ---------- Admin ----------
def test_admin_overview():
    r = requests.get(f"{API}/admin/overview", headers=_hdr(state["admin_token"]), timeout=15)
    assert r.status_code == 200
    data = r.json()
    for k in ["total_users", "farm_owners", "farm_partners", "total_jobs", "active_contracts", "gmv"]:
        assert k in data


def test_admin_lists():
    for ep in ["users", "jobs", "payments"]:
        r = requests.get(f"{API}/admin/{ep}", headers=_hdr(state["admin_token"]), timeout=15)
        assert r.status_code == 200
        assert isinstance(r.json(), list)


def test_admin_analytics():
    r = requests.get(f"{API}/admin/analytics", headers=_hdr(state["admin_token"]), timeout=15)
    assert r.status_code == 200
    assert "categories" in r.json()


def test_admin_forbidden_for_non_admin():
    r = requests.get(f"{API}/admin/overview", headers=_hdr(state["owner_token"]), timeout=15)
    assert r.status_code == 403
