"""
Go Farm Work - v3 Backend API Test Suite
Tests all v1+v2+v3 endpoints including OTP auth, webhooks, live location, chatbot, etc.
"""
import os
import time
import uuid
import hashlib
import requests

BASE_URL = os.environ.get("REACT_APP_BACKEND_URL", "https://api.gofarmwork.com").rstrip("/")
API = f"{BASE_URL}/api"

RUN = uuid.uuid4().hex[:8]
OWNER_EMAIL = f"TEST_owner_{RUN}@test.com"
PARTNER_EMAIL = f"TEST_partner_{RUN}@test.com"
PWD = "Test@1234"
ADMIN_EMAIL = "admin@gofarmwork.in"
ADMIN_PWD = "Admin@123"

state = {}  # shared across tests


def _hdr(tok):
    return {"Authorization": f"Bearer {tok}", "Content-Type": "application/json"}


class TestResults:
    def __init__(self):
        self.passed = []
        self.failed = []
        self.total = 0

    def record(self, name, passed, error=None):
        self.total += 1
        if passed:
            self.passed.append(name)
            print(f"✅ {name}")
        else:
            self.failed.append({"test": name, "error": str(error)})
            print(f"❌ {name}: {error}")

    def summary(self):
        print(f"\n{'='*60}")
        print(f"BACKEND TEST SUMMARY")
        print(f"{'='*60}")
        print(f"Total: {self.total} | Passed: {len(self.passed)} | Failed: {len(self.failed)}")
        if self.failed:
            print(f"\n❌ FAILED TESTS:")
            for f in self.failed:
                print(f"  - {f['test']}: {f['error']}")
        return len(self.failed) == 0


results = TestResults()


# ========== HEALTH & REFERENCE DATA ==========
def test_health():
    try:
        r = requests.get(f"{API}/health", timeout=15)
        assert r.status_code == 200
        assert r.json().get("ok") is True
        results.record("Health check", True)
    except Exception as e:
        results.record("Health check", False, e)


def test_districts_31():
    try:
        r = requests.get(f"{API}/locations/districts", timeout=15)
        assert r.status_code == 200
        data = r.json()
        assert len(data) >= 31, f"Expected 31 districts, got {len(data)}"
        assert "_id" not in data[0]
        state["district_id"] = data[0]["district_id"]
        mysuru = next((d for d in data if d["name"] == "Mysuru"), data[0])
        state["mysuru_id"] = mysuru["district_id"]
        results.record("Districts (31 Karnataka)", True)
    except Exception as e:
        results.record("Districts (31 Karnataka)", False, e)


def test_categories():
    try:
        r = requests.get(f"{API}/categories", timeout=15)
        assert r.status_code == 200
        data = r.json()
        assert len(data) >= 29, f"Expected 29 categories, got {len(data)}"
        cid_key = "category_id" if "category_id" in data[0] else "id"
        state["category_id"] = data[0][cid_key]
        results.record("Categories", True)
    except Exception as e:
        results.record("Categories", False, e)


# ========== AUTH v1 (email/password) ==========
def test_admin_login():
    try:
        r = requests.post(f"{API}/auth/login", json={"email": ADMIN_EMAIL, "password": ADMIN_PWD}, timeout=15)
        assert r.status_code == 200, r.text
        data = r.json()
        assert data["user"]["role"] == "admin"
        assert "password_hash" not in data["user"]
        state["admin_token"] = data["token"]
        results.record("Admin login", True)
    except Exception as e:
        results.record("Admin login", False, e)


def test_signup_owner():
    try:
        r = requests.post(f"{API}/auth/signup", json={
            "email": OWNER_EMAIL, "password": PWD, "full_name": "Test Owner"
        }, timeout=15)
        assert r.status_code == 200, r.text
        data = r.json()
        assert data["token"]
        state["owner_token"] = data["token"]
        state["owner_id"] = data["user"]["user_id"]
        results.record("Signup owner", True)
    except Exception as e:
        results.record("Signup owner", False, e)


def test_signup_partner():
    try:
        r = requests.post(f"{API}/auth/signup", json={
            "email": PARTNER_EMAIL, "password": PWD, "full_name": "Test Partner"
        }, timeout=15)
        assert r.status_code == 200, r.text
        state["partner_token"] = r.json()["token"]
        state["partner_id"] = r.json()["user"]["user_id"]
        results.record("Signup partner", True)
    except Exception as e:
        results.record("Signup partner", False, e)


def test_auth_me():
    try:
        r = requests.get(f"{API}/auth/me", headers=_hdr(state["owner_token"]), timeout=15)
        assert r.status_code == 200
        assert r.json()["email"] == OWNER_EMAIL.lower()
        results.record("GET /auth/me", True)
    except Exception as e:
        results.record("GET /auth/me", False, e)


def test_set_roles():
    try:
        r1 = requests.patch(f"{API}/auth/role", json={"role": "farm_owner"}, headers=_hdr(state["owner_token"]), timeout=15)
        assert r1.status_code == 200
        r2 = requests.patch(f"{API}/auth/role", json={"role": "farm_partner"}, headers=_hdr(state["partner_token"]), timeout=15)
        assert r2.status_code == 200
        results.record("Set roles", True)
    except Exception as e:
        results.record("Set roles", False, e)


# ========== AUTH v3 (OTP) ==========
def test_otp_request_mobile():
    try:
        r = requests.post(f"{API}/auth/otp/request", json={
            "channel": "mobile", "identifier": "+919876500001", "purpose": "login"
        }, timeout=15)
        assert r.status_code == 200, r.text
        data = r.json()
        assert data["ok"] is True
        assert "masked_identifier" in data
        assert "dev_otp" in data  # dev mode
        state["dev_otp_mobile"] = data.get("dev_otp")
        results.record("OTP request (mobile)", True)
    except Exception as e:
        results.record("OTP request (mobile)", False, e)


def test_otp_request_email():
    try:
        r = requests.post(f"{API}/auth/otp/request", json={
            "channel": "email", "identifier": "test@example.com", "purpose": "login"
        }, timeout=15)
        assert r.status_code == 200, r.text
        data = r.json()
        assert data["ok"] is True
        state["dev_otp_email"] = data.get("dev_otp")
        results.record("OTP request (email)", True)
    except Exception as e:
        results.record("OTP request (email)", False, e)


def test_otp_verify_wrong():
    try:
        r = requests.post(f"{API}/auth/otp/verify", json={
            "channel": "mobile", "identifier": "+919876500001", "otp": "000000", "purpose": "login"
        }, timeout=15)
        assert r.status_code == 400
        results.record("OTP verify (wrong OTP returns 400)", True)
    except Exception as e:
        results.record("OTP verify (wrong OTP returns 400)", False, e)


def test_otp_verify_correct():
    try:
        if not state.get("dev_otp_mobile"):
            print("⚠️  Skipping OTP verify (no dev_otp)")
            return
        r = requests.post(f"{API}/auth/otp/verify", json={
            "channel": "mobile", "identifier": "+919876500001", "otp": state["dev_otp_mobile"], "purpose": "login", "full_name": "OTP User"
        }, timeout=15)
        assert r.status_code == 200, r.text
        data = r.json()
        assert "token" in data
        assert "user" in data
        state["otp_token"] = data["token"]
        results.record("OTP verify (correct)", True)
    except Exception as e:
        results.record("OTP verify (correct)", False, e)


def test_otp_cooldown():
    try:
        # Rapid resend should be blocked
        r = requests.post(f"{API}/auth/otp/request", json={
            "channel": "mobile", "identifier": "+919876500001", "purpose": "login"
        }, timeout=15)
        assert r.status_code == 429, "Expected 429 for rapid resend"
        results.record("OTP cooldown enforced", True)
    except Exception as e:
        results.record("OTP cooldown enforced", False, e)


# ========== JOBS v1 ==========
def test_create_job():
    try:
        r = requests.post(f"{API}/jobs", json={
            "title": "TEST Paddy harvesting",
            "description": "Need 5 workers",
            "category_id": state["category_id"],
            "budget_type": "fixed", "budget_min": 5000, "budget_max": 8000,
            "district": "Mysuru", "workers_needed": 5,
        }, headers=_hdr(state["owner_token"]), timeout=15)
        assert r.status_code == 200, r.text
        state["job_id"] = r.json()["job_id"]
        results.record("Create job", True)
    except Exception as e:
        results.record("Create job", False, e)


def test_publish_job():
    try:
        r = requests.post(f"{API}/jobs/{state['job_id']}/publish", headers=_hdr(state["owner_token"]), timeout=15)
        assert r.status_code == 200
        results.record("Publish job", True)
    except Exception as e:
        results.record("Publish job", False, e)


def test_list_jobs():
    try:
        r = requests.get(f"{API}/jobs", params={"district": "Mysuru"}, timeout=15)
        assert r.status_code == 200
        assert any(j["job_id"] == state["job_id"] for j in r.json())
        results.record("List jobs", True)
    except Exception as e:
        results.record("List jobs", False, e)


# ========== PROPOSALS v1 ==========
def test_submit_proposal():
    try:
        r = requests.post(f"{API}/jobs/{state['job_id']}/proposals", json={
            "bid_amount": 6500, "message": "I can do this", "estimated_days": 3
        }, headers=_hdr(state["partner_token"]), timeout=15)
        assert r.status_code == 200, r.text
        state["proposal_id"] = r.json()["proposal_id"]
        results.record("Submit proposal", True)
    except Exception as e:
        results.record("Submit proposal", False, e)


def test_proposals_mine():
    try:
        r = requests.get(f"{API}/proposals/mine", headers=_hdr(state["partner_token"]), timeout=15)
        assert r.status_code == 200
        results.record("GET /proposals/mine", True)
    except Exception as e:
        results.record("GET /proposals/mine", False, e)


# ========== v2 FEE CALCULATOR ==========
def test_fee_calculator():
    try:
        r = requests.post(f"{API}/proposals/calculate-fee", json={"bid_amount": 10000}, headers=_hdr(state["partner_token"]), timeout=15)
        assert r.status_code == 200
        data = r.json()
        assert data["fee_percent"] == 5.0
        assert data["fee_amount"] == 500.0
        assert data["worker_net_amount"] == 9500.0
        results.record("Fee calculator (5%)", True)
    except Exception as e:
        results.record("Fee calculator (5%)", False, e)


# ========== CONTRACTS v1 ==========
def test_accept_proposal():
    try:
        r = requests.post(f"{API}/proposals/{state['proposal_id']}/accept", headers=_hdr(state["owner_token"]), timeout=15)
        assert r.status_code == 200, r.text
        state["contract_id"] = r.json()["contract_id"]
        results.record("Accept proposal (creates contract)", True)
    except Exception as e:
        results.record("Accept proposal (creates contract)", False, e)


def test_list_contracts():
    try:
        r = requests.get(f"{API}/contracts", headers=_hdr(state["owner_token"]), timeout=15)
        assert r.status_code == 200
        results.record("List contracts", True)
    except Exception as e:
        results.record("List contracts", False, e)


# ========== MESSAGES v1 ==========
def test_chats():
    try:
        r = requests.post(f"{API}/chats", json={"other_user_id": state["partner_id"], "job_id": state["job_id"]}, headers=_hdr(state["owner_token"]), timeout=15)
        assert r.status_code == 200
        state["thread_id"] = r.json()["thread_id"]
        results.record("Open chat", True)
    except Exception as e:
        results.record("Open chat", False, e)


# ========== v2 WORKER TALENT ==========
def test_worker_profile():
    try:
        r = requests.post(f"{API}/workers/profile", json={
            "public_title": "Expert Harvester", "short_pitch": "10 years exp", "skill_tags": ["harvesting", "plowing"],
            "service_categories": [state["category_id"]], "expected_fare_min": 500, "expected_fare_max": 1000,
            "fare_unit": "day", "profile_visibility": "public", "open_to_work_status": "immediate"
        }, headers=_hdr(state["partner_token"]), timeout=15)
        assert r.status_code == 200, r.text
        results.record("Create worker profile", True)
    except Exception as e:
        results.record("Create worker profile", False, e)


def test_list_workers():
    try:
        r = requests.get(f"{API}/workers", timeout=15)
        assert r.status_code == 200
        results.record("List workers (Talent)", True)
    except Exception as e:
        results.record("List workers (Talent)", False, e)


# ========== v2 WALLET ==========
def test_wallet():
    try:
        r = requests.get(f"{API}/wallet", headers=_hdr(state["partner_token"]), timeout=15)
        assert r.status_code == 200
        data = r.json()
        assert "held_balance" in data
        assert "available_balance" in data
        results.record("GET /wallet", True)
    except Exception as e:
        results.record("GET /wallet", False, e)


# ========== v2 CHATBOT FAQ ==========
def test_chatbot_faq():
    try:
        r = requests.get(f"{API}/chatbot/faq", timeout=15)
        assert r.status_code == 200
        assert isinstance(r.json(), list)
        results.record("GET /chatbot/faq", True)
    except Exception as e:
        results.record("GET /chatbot/faq", False, e)


# ========== v3 CHATBOT LLM ==========
def test_chatbot_v2_english():
    try:
        r = requests.post(f"{API}/chatbot/v2/message", json={"message": "How does the 5% fee work?", "language": "en"}, timeout=20)
        assert r.status_code == 200, r.text
        data = r.json()
        assert "reply" in data
        assert data["kind"] in ("llm", "fallback_no_key", "fallback_error")
        results.record("Chatbot v2 (English)", True)
    except Exception as e:
        results.record("Chatbot v2 (English)", False, e)


def test_chatbot_v2_kannada():
    try:
        r = requests.post(f"{API}/chatbot/v2/message", json={"message": "ಕನ್ನಡದಲ್ಲಿ ಹೇಳಿ", "language": "kn"}, timeout=20)
        assert r.status_code == 200
        results.record("Chatbot v2 (Kannada)", True)
    except Exception as e:
        results.record("Chatbot v2 (Kannada)", False, e)


def test_chatbot_v2_hindi():
    try:
        r = requests.post(f"{API}/chatbot/v2/message", json={"message": "हिंदी में बताएं", "language": "hi"}, timeout=20)
        assert r.status_code == 200
        results.record("Chatbot v2 (Hindi)", True)
    except Exception as e:
        results.record("Chatbot v2 (Hindi)", False, e)


# ========== v3 LIVE LOCATION ==========
def test_live_location_start():
    try:
        r = requests.post(f"{API}/live-location/start", json={
            "partner_user_id": state["partner_id"], "contract_id": state["contract_id"], "duration_minutes": 60
        }, headers=_hdr(state["owner_token"]), timeout=15)
        assert r.status_code == 200, r.text
        data = r.json()
        assert data["status"] == "pending_consent"
        state["loc_session_id"] = data["session_id"]
        results.record("Live location start", True)
    except Exception as e:
        results.record("Live location start", False, e)


def test_live_location_consent():
    try:
        r = requests.post(f"{API}/live-location/{state['loc_session_id']}/consent", json={"consent": True}, headers=_hdr(state["partner_token"]), timeout=15)
        assert r.status_code == 200
        assert r.json()["status"] == "active"
        results.record("Live location consent", True)
    except Exception as e:
        results.record("Live location consent", False, e)


def test_live_location_ping():
    try:
        r = requests.post(f"{API}/live-location/{state['loc_session_id']}/ping", json={"lat": 12.9716, "lng": 77.5946, "accuracy_m": 10}, headers=_hdr(state["partner_token"]), timeout=15)
        assert r.status_code == 200
        results.record("Live location ping", True)
    except Exception as e:
        results.record("Live location ping", False, e)


def test_live_location_stop():
    try:
        r = requests.post(f"{API}/live-location/{state['loc_session_id']}/stop", headers=_hdr(state["owner_token"]), timeout=15)
        assert r.status_code == 200
        results.record("Live location stop", True)
    except Exception as e:
        results.record("Live location stop", False, e)


def test_live_location_unauth():
    try:
        r = requests.post(f"{API}/live-location/start", json={"partner_user_id": state["partner_id"], "duration_minutes": 60}, timeout=15)
        assert r.status_code == 401
        results.record("Live location (unauth returns 401)", True)
    except Exception as e:
        results.record("Live location (unauth returns 401)", False, e)


# ========== v3 STEP-UP AUTH ==========
def test_withdraw_secure_no_token():
    try:
        r = requests.post(f"{API}/wallet/withdraw-secure", json={"amount": 100, "method": "upi", "step_up_token": "fake"}, headers=_hdr(state["partner_token"]), timeout=15)
        assert r.status_code == 401
        results.record("Withdraw secure (no step_up_token returns 401)", True)
    except Exception as e:
        results.record("Withdraw secure (no step_up_token returns 401)", False, e)


# ========== v3 AUDIT LOG ==========
def test_audit_me():
    try:
        r = requests.get(f"{API}/audit/me", headers=_hdr(state["owner_token"]), timeout=15)
        assert r.status_code == 200
        assert isinstance(r.json(), list)
        results.record("GET /audit/me", True)
    except Exception as e:
        results.record("GET /audit/me", False, e)


# ========== v3 SHORTLIST ==========
def test_shortlist():
    try:
        r = requests.post(f"{API}/shortlist", json={"worker_ids": [state["partner_id"]], "job_id": state["job_id"], "label": "test"}, headers=_hdr(state["owner_token"]), timeout=15)
        assert r.status_code == 200
        results.record("POST /shortlist", True)
    except Exception as e:
        results.record("POST /shortlist", False, e)


def test_shortlist_compare():
    try:
        r = requests.post(f"{API}/shortlist/compare", json={"worker_ids": [state["partner_id"]]}, headers=_hdr(state["owner_token"]), timeout=15)
        assert r.status_code == 200
        results.record("POST /shortlist/compare", True)
    except Exception as e:
        results.record("POST /shortlist/compare", False, e)


# ========== v3 PRICING BENCHMARK ==========
def test_pricing_benchmark():
    try:
        r = requests.get(f"{API}/pricing/benchmark", params={"category_id": state["category_id"]}, timeout=15)
        assert r.status_code == 200
        data = r.json()
        assert "p25" in data and "p50" in data and "p75" in data
        results.record("GET /pricing/benchmark", True)
    except Exception as e:
        results.record("GET /pricing/benchmark", False, e)


# ========== v3 PUSH REGISTRATION ==========
def test_push_register():
    try:
        r = requests.post(f"{API}/push/register", json={"device_token": "test_token_123", "platform": "web"}, headers=_hdr(state["owner_token"]), timeout=15)
        assert r.status_code == 200
        results.record("POST /push/register", True)
    except Exception as e:
        results.record("POST /push/register", False, e)


# ========== v3 WEBHOOKS ==========
def test_whatsapp_webhook_verify():
    try:
        r = requests.get(f"{API}/webhooks/whatsapp", params={"hub.mode": "subscribe", "hub.verify_token": "gofarmwork-wa-verify", "hub.challenge": "test123"}, timeout=15)
        assert r.status_code == 200
        assert r.text == "test123"
        results.record("WhatsApp webhook verify (correct token)", True)
    except Exception as e:
        results.record("WhatsApp webhook verify (correct token)", False, e)


def test_whatsapp_webhook_verify_wrong():
    try:
        r = requests.get(f"{API}/webhooks/whatsapp", params={"hub.mode": "subscribe", "hub.verify_token": "wrong", "hub.challenge": "test"}, timeout=15)
        assert r.status_code == 403
        results.record("WhatsApp webhook verify (wrong token returns 403)", True)
    except Exception as e:
        results.record("WhatsApp webhook verify (wrong token returns 403)", False, e)


def test_razorpay_webhook():
    try:
        r = requests.post(f"{API}/webhooks/razorpay", json={"event": "payment.captured", "payload": {}}, timeout=15)
        assert r.status_code == 200
        results.record("Razorpay webhook (no signature check in dev)", True)
    except Exception as e:
        results.record("Razorpay webhook (no signature check in dev)", False, e)


# ========== v3 APP READINESS ==========
def test_app_readiness():
    try:
        r = requests.get(f"{API}/app/readiness", timeout=15)
        assert r.status_code == 200
        data = r.json()
        assert "store_ready_checklist" in data
        assert "integrations" in data
        results.record("GET /app/readiness", True)
    except Exception as e:
        results.record("GET /app/readiness", False, e)


# ========== ADMIN v3 ==========
def test_admin_geography_quality():
    try:
        r = requests.get(f"{API}/admin/geography-quality", headers=_hdr(state["admin_token"]), timeout=15)
        assert r.status_code == 200
        data = r.json()
        assert "districts" in data
        assert data["is_complete_karnataka"] is True
        results.record("GET /admin/geography-quality", True)
    except Exception as e:
        results.record("GET /admin/geography-quality", False, e)


# ========== RUN ALL ==========
def run_all():
    print(f"\n{'='*60}")
    print(f"GO FARM WORK - BACKEND TEST SUITE (v1+v2+v3)")
    print(f"{'='*60}")
    print(f"API: {API}\n")

    # Health & Reference
    test_health()
    test_districts_31()
    test_categories()

    # Auth v1
    test_admin_login()
    test_signup_owner()
    test_signup_partner()
    test_auth_me()
    test_set_roles()

    # Auth v3 (OTP)
    test_otp_request_mobile()
    test_otp_request_email()
    test_otp_verify_wrong()
    test_otp_verify_correct()
    test_otp_cooldown()

    # Jobs v1
    test_create_job()
    test_publish_job()
    test_list_jobs()

    # Proposals v1
    test_submit_proposal()
    test_proposals_mine()

    # v2 Fee
    test_fee_calculator()

    # Contracts v1
    test_accept_proposal()
    test_list_contracts()

    # Messages v1
    test_chats()

    # v2 Talent
    test_worker_profile()
    test_list_workers()

    # v2 Wallet
    test_wallet()

    # v2 Chatbot
    test_chatbot_faq()

    # v3 Chatbot LLM
    test_chatbot_v2_english()
    test_chatbot_v2_kannada()
    test_chatbot_v2_hindi()

    # v3 Live Location
    test_live_location_start()
    test_live_location_consent()
    test_live_location_ping()
    test_live_location_stop()
    test_live_location_unauth()

    # v3 Step-up
    test_withdraw_secure_no_token()

    # v3 Audit
    test_audit_me()

    # v3 Shortlist
    test_shortlist()
    test_shortlist_compare()

    # v3 Pricing
    test_pricing_benchmark()

    # v3 Push
    test_push_register()

    # v3 Webhooks
    test_whatsapp_webhook_verify()
    test_whatsapp_webhook_verify_wrong()
    test_razorpay_webhook()

    # v3 App Readiness
    test_app_readiness()

    # Admin v3
    test_admin_geography_quality()

    # Summary
    success = results.summary()
    return 0 if success else 1


if __name__ == "__main__":
    import sys
    sys.exit(run_all())
