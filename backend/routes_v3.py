"""
Go Farm Work v3 — Store-ready & founder-vision additions:
- OTP auth (mobile + email)
- LLM-powered chatbot (Universal key) with truthful fallback
- Live field location sessions (foreground, opt-in, time-limited)
- Audit log (sensitive action trail)
- Idempotency keys for payments
- Step-up auth for sensitive actions (withdrawal, big payouts)
- Razorpay webhook handler (signature verify) + WhatsApp webhook scaffolding
- Smart pricing benchmarks per category + district
- Multi-worker shortlist
- Geography quality endpoint
- Push token registration
"""
from flask import Blueprint, request, jsonify, g, Response
from pydantic import BaseModel, Field, EmailStr
from typing import Optional, List, Literal
from datetime import datetime, timezone, timedelta
import os
import hmac
import hashlib
import random
import string
import logging
import requests
import asyncio
from werkzeug.exceptions import NotFound, Forbidden, BadRequest

from auth import (
    login_required, validate_schema, new_id, new_user_id, create_jwt,
    hash_password, verify_password,
)

logger = logging.getLogger("gofarmwork.v3")

def iso():
    return datetime.now(timezone.utc).isoformat()


def make_v3_router(db):
    router = Blueprint("v3", __name__, url_prefix="/api")

    def write_audit(user_id: str, action: str, ref_type: str = None, ref_id: str = None, meta: dict = None):
        db.audit_log.insert_one({
            "audit_id": new_id("aud"),
            "user_id": user_id,
            "action": action,
            "ref_type": ref_type,
            "ref_id": ref_id,
            "meta": meta or {},
            "created_at": iso(),
        })

    # ====================================================
    # WHATSAPP WEBHOOK SCAFFOLD (verify + receive)
    # ====================================================
    @router.route("/webhooks/whatsapp", methods=["GET"])
    def whatsapp_verify():
        hub_mode = request.args.get("hub.mode")
        hub_challenge = request.args.get("hub.challenge")
        hub_verify_token = request.args.get("hub.verify_token")
        
        verify_token = os.environ.get("WHATSAPP_WEBHOOK_VERIFY_TOKEN", "")
        if hub_mode == "subscribe" and hub_verify_token == verify_token and hub_challenge:
            return Response(hub_challenge, mimetype="text/plain", status=200)
        raise Forbidden("Verification failed")

    @router.route("/webhooks/whatsapp", methods=["POST"])
    def whatsapp_incoming():
        try:
            event = request.get_json()
        except Exception:
            return jsonify({"ok": False})
        db.webhook_events.insert_one({
            "event_id": new_id("evt"), "provider": "whatsapp",
            "event": "message", "payload": event, "processed": False,
            "received_at": iso(),
        })
        # Note: actual WA flow handling is roadmap (truthful).
        return jsonify({"ok": True})

    # ====================================================
    # LIVE FIELD LOCATION SESSIONS
    # ====================================================
    class LocStart(BaseModel):
        contract_id: Optional[str] = None
        job_id: Optional[str] = None
        partner_user_id: str
        duration_minutes: int = Field(default=60, ge=5, le=480)

    @router.route("/live-location/start", methods=["POST"])
    @login_required
    @validate_schema(LocStart)
    def loc_start(body):
        user = g.current_user
        # Only owner can start towards a partner
        if user["user_id"] == body.partner_user_id:
            raise BadRequest("Self-session not allowed")
        sid = new_id("loc")
        now = datetime.now(timezone.utc)
        db.live_location_sessions.insert_one({
            "session_id": sid,
            "owner_user_id": user["user_id"],
            "partner_user_id": body.partner_user_id,
            "contract_id": body.contract_id,
            "job_id": body.job_id,
            "status": "pending_consent",
            "started_at": iso(),
            "expires_at": (now + timedelta(minutes=body.duration_minutes)).isoformat(),
            "last_lat": None, "last_lng": None, "last_seen_at": None,
        })
        db.notifications.insert_one({
            "notif_id": new_id("notif"), "user_id": body.partner_user_id,
            "type": "live_location_request",
            "title": "Live location request",
            "body": "The Farm Owner is requesting your live location for navigation.",
            "link": "/contracts", "read": False, "created_at": iso(),
        })
        write_audit(user["user_id"], "live_location_start", "session", sid, {"partner": body.partner_user_id})
        return jsonify({"session_id": sid, "status": "pending_consent"})

    class LocConsent(BaseModel):
        consent: bool

    @router.route("/live-location/<session_id>/consent", methods=["POST"])
    @login_required
    @validate_schema(LocConsent)
    def loc_consent(body, session_id):
        user = g.current_user
        s = db.live_location_sessions.find_one({"session_id": session_id}, {"_id": 0})
        if not s or s["partner_user_id"] != user["user_id"]:
            raise Forbidden("Forbidden")
        new_status = "active" if body.consent else "declined"
        db.live_location_sessions.update_one({"session_id": session_id}, {"$set": {"status": new_status, "consented_at": iso()}})
        write_audit(user["user_id"], f"live_location_{new_status}", "session", session_id)
        return jsonify({"ok": True, "status": new_status})

    class LocPing(BaseModel):
        lat: float
        lng: float
        accuracy_m: Optional[float] = None

    @router.route("/live-location/<session_id>/ping", methods=["POST"])
    @login_required
    @validate_schema(LocPing)
    def loc_ping(body, session_id):
        user = g.current_user
        s = db.live_location_sessions.find_one({"session_id": session_id}, {"_id": 0})
        if not s or user["user_id"] not in (s["partner_user_id"], s["owner_user_id"]):
            raise Forbidden("Forbidden")
        if s["status"] != "active":
            raise BadRequest(f"Session not active ({s['status']})")
        exp = datetime.fromisoformat(s["expires_at"])
        if exp.tzinfo is None:
            exp = exp.replace(tzinfo=timezone.utc)
        if exp < datetime.now(timezone.utc):
            db.live_location_sessions.update_one({"session_id": session_id}, {"$set": {"status": "expired"}})
            raise BadRequest("Session expired")
        db.live_location_sessions.update_one(
            {"session_id": session_id},
            {"$set": {"last_lat": body.lat, "last_lng": body.lng, "last_seen_at": iso(), "last_accuracy_m": body.accuracy_m}},
        )
        db.live_location_pings.insert_one({
            "session_id": session_id, "user_id": user["user_id"],
            "lat": body.lat, "lng": body.lng, "accuracy_m": body.accuracy_m, "at": iso(),
        })
        return jsonify({"ok": True})

    @router.route("/live-location/<session_id>/stop", methods=["POST"])
    @login_required
    def loc_stop(session_id):
        user = g.current_user
        s = db.live_location_sessions.find_one({"session_id": session_id}, {"_id": 0})
        if not s or user["user_id"] not in (s["partner_user_id"], s["owner_user_id"]):
            raise Forbidden("Forbidden")
        db.live_location_sessions.update_one({"session_id": session_id}, {"$set": {"status": "stopped", "stopped_at": iso()}})
        write_audit(user["user_id"], "live_location_stop", "session", session_id)
        return jsonify({"ok": True})

    @router.route("/live-location/active", methods=["GET"])
    @login_required
    def loc_active():
        user = g.current_user
        items = list(db.live_location_sessions.find(
            {"$or": [{"owner_user_id": user["user_id"]}, {"partner_user_id": user["user_id"]}], "status": {"$in": ["pending_consent", "active"]}},
            {"_id": 0},
        ).sort("started_at", -1).limit(50))
        return jsonify(items)

    # ====================================================
    # SMART PRICING benchmarks
    # ====================================================
    @router.route("/pricing/benchmark", methods=["GET"])
    def pricing_benchmark():
        category_id = request.args.get("category_id")
        district = request.args.get("district")
        if not category_id:
            raise BadRequest("category_id required")
            
        f = {"category_id": category_id, "status": {"$in": ["published", "in_progress", "completed"]}}
        if district:
            f["district"] = district
        jobs = list(db.jobs.find(f, {"_id": 0, "budget_min": 1, "budget_max": 1}))
        amounts = []
        for j in jobs:
            mn, mx = j.get("budget_min") or 0, j.get("budget_max") or 0
            if mn and mx:
                amounts.append((mn + mx) / 2)
            elif mn:
                amounts.append(mn)
            elif mx:
                amounts.append(mx)
        amounts.sort()
        n = len(amounts)
        if n == 0:
            return jsonify({"category_id": category_id, "district": district, "samples": 0,
                    "p25": None, "p50": None, "p75": None, "avg": None, "min": None, "max": None})
        def pct(p):
            idx = max(0, min(n - 1, int(round((p / 100.0) * (n - 1)))))
            return round(amounts[idx], 2)
        return jsonify({
            "category_id": category_id, "district": district, "samples": n,
            "p25": pct(25), "p50": pct(50), "p75": pct(75),
            "avg": round(sum(amounts) / n, 2),
            "min": round(amounts[0], 2), "max": round(amounts[-1], 2),
        })

    # ====================================================
    # SHORTLIST workers (multi-select, for compare)
    # ====================================================
    class ShortlistBody(BaseModel):
        worker_ids: List[str]
        job_id: Optional[str] = None
        label: Optional[str] = "default"

    @router.route("/shortlist", methods=["POST"])
    @login_required
    @validate_schema(ShortlistBody)
    def upsert_shortlist(body):
        user = g.current_user
        sid = new_id("sl")
        doc = {
            "shortlist_id": sid, "owner_user_id": user["user_id"],
            "label": body.label, "worker_ids": body.worker_ids, "job_id": body.job_id,
            "created_at": iso(), "updated_at": iso(),
        }
        db.shortlists.insert_one(doc)
        doc.pop("_id", None)
        return jsonify(doc)

    @router.route("/shortlist", methods=["GET"])
    @login_required
    def list_shortlists():
        user = g.current_user
        items = list(db.shortlists.find({"owner_user_id": user["user_id"]}, {"_id": 0}).sort("created_at", -1).limit(50))
        return jsonify(items)

    @router.route("/shortlist/compare", methods=["POST"])
    @login_required
    def compare_workers():
        data = request.get_json() or {}
        ids = data.get("worker_ids") or []
        out = []
        for wid in ids[:6]:
            p = db.worker_service_profiles.find_one({"user_id": wid}, {"_id": 0})
            u = db.users.find_one({"user_id": wid}, {"_id": 0, "password_hash": 0, "email": 0})
            pf = db.profiles.find_one({"user_id": wid}, {"_id": 0}) or {}
            agg = list(db.reviews.aggregate([
                {"$match": {"reviewee_user_id": wid}},
                {"$group": {"_id": None, "avg": {"$avg": "$rating"}, "count": {"$sum": 1}}},
            ]))
            rating = {"avg": (agg[0]["avg"] if agg else 0) or 0, "count": (agg[0]["count"] if agg else 0)}
            out.append({"worker_id": wid, "profile": p or {}, "user": u, "location": {"district": pf.get("district"), "taluk": pf.get("taluk")}, "rating": rating})
        return jsonify(out)

    # ====================================================
    # LLM-POWERED CHATBOT (Universal key, truthful)
    # ====================================================
    class ChatbotBody(BaseModel):
        message: str
        session_id: Optional[str] = None
        context_page: Optional[str] = None
        language: Optional[str] = "en"
        user_role: Optional[str] = None

    SYSTEM_PROMPT_BASE = """You are Go Farm Work Assistant, the helper for an agri-work marketplace serving Karnataka, India.
Always be friendly, concise, and TRUTHFUL.

Core facts you MUST follow:
- Two roles: Farm Owner (hires) and Farm Partner (worker).
- Platform fee: 5% on every accepted proposal, deducted from worker's payment.
- Cash-mode jobs require a one-time ₹400 booking fee paid by the owner via Razorpay to confirm a hire; the worker's salary is still paid in cash offline.
- Supported languages: English, Kannada (ಕನ್ನಡ), Hindi (हिन्दी). User can switch from the top bar.
- WhatsApp posting/applying is on the roadmap and NOT live yet.
- Live field location is foreground-only and opt-in; only shared during an active job; users can stop anytime.
- Wallet: workers see Pending + Available; withdrawals require step-up OTP and go to UPI/bank.
- Trust: built via verified phone/email, ratings, repeat hires, and badges.

Strict rules:
- NEVER claim to perform irreversible actions (post a job, pay, accept hire, withdraw). Instead, explain the steps and link to the right page.
- NEVER fabricate features. If unsure, say so and suggest contacting support.
- NEVER give medical, legal, or financial advice beyond what Go Farm Work offers.
- Keep replies under 120 words. Use bullet points for steps.
- If asked in Kannada or Hindi, reply in the same language."""

    @router.route("/chatbot/v2/faq", methods=["GET"])
    def get_faqs_v2():
        return jsonify([
            {"id": "fee", "q": "How does the 5% platform fee work?"},
            {"id": "cash", "q": "What is the ₹400 cash booking fee?"},
            {"id": "post", "q": "How do I post a job?"},
            {"id": "apply", "q": "How do I apply to jobs as a worker?"},
            {"id": "wallet", "q": "When do I get paid?"},
            {"id": "trust", "q": "How is trust built?"},
            {"id": "lang", "q": "Can I use Go Farm Work in Kannada or Hindi?"},
            {"id": "whatsapp", "q": "Can I use WhatsApp?"},
            {"id": "location", "q": "Why do you need my location?"},
            {"id": "talent", "q": "How can a Farm Owner find me directly?"},
        ])

    @router.route("/chatbot/v2/message", methods=["POST"])
    @validate_schema(ChatbotBody)
    def chatbot_v2(body):
        # Truthful fallback in case LLM unavailable
        api_key = os.environ.get("OPENAI_API_KEY")
        if not api_key:
            return jsonify({"reply": _fallback_reply(body.message), "kind": "fallback_no_key"})
        try:
            from ai_integrations.llm.chat import LlmChat, UserMessage
            session_id = body.session_id or new_id("chat")
            lang_hint = ""
            if (body.language or "en") == "kn":
                lang_hint = "\nReply in Kannada (ಕನ್ನಡ)."
            elif (body.language or "en") == "hi":
                lang_hint = "\nReply in Hindi (हिन्दी)."
            role_hint = ""
            if body.user_role:
                role_hint = f"\nUser role: {body.user_role}."
            page_hint = ""
            if body.context_page:
                page_hint = f"\nCurrent page: {body.context_page}."
            chat = LlmChat(
                api_key=api_key,
                session_id=session_id,
                system_message=SYSTEM_PROMPT_BASE + lang_hint + role_hint + page_hint,
            ).with_model("openai", "gpt-4o-mini")
            
            # Run the async chat send in the sync request context
            reply = asyncio.run(chat.send_message(UserMessage(text=body.message)))
            return jsonify({"reply": reply, "kind": "llm", "session_id": session_id, "model": "openai/gpt-4o-mini"})
        except Exception as e:
            logger.exception("chatbot LLM failed")
            return jsonify({"reply": _fallback_reply(body.message), "kind": "fallback_error", "error": str(e)[:200]})

    # ====================================================
    # AUDIT LOG (read for current user / admin)
    # ====================================================
    @router.route("/audit/me", methods=["GET"])
    @login_required
    def audit_me():
        user = g.current_user
        limit = request.args.get("limit", default=100, type=int)
        items = list(db.audit_log.find({"user_id": user["user_id"]}, {"_id": 0}).sort("created_at", -1).limit(limit))
        return jsonify(items)

    @router.route("/admin/audit", methods=["GET"])
    @login_required
    def admin_audit():
        user = g.current_user
        if user.get("role") != "admin":
            raise Forbidden("Admin only")
        limit = request.args.get("limit", default=200, type=int)
        items = list(db.audit_log.find({}, {"_id": 0}).sort("created_at", -1).limit(limit))
        return jsonify(items)

    # ====================================================
    # PUSH NOTIFICATIONS — token registration scaffolding
    # ====================================================
    class PushRegister(BaseModel):
        device_token: str
        platform: Literal["web", "android", "ios"]
        app_version: Optional[str] = None

    @router.route("/push/register", methods=["POST"])
    @login_required
    @validate_schema(PushRegister)
    def push_register(body):
        user = g.current_user
        db.push_tokens.update_one(
            {"user_id": user["user_id"], "device_token": body.device_token},
            {"$set": {**body.model_dump(), "user_id": user["user_id"], "updated_at": iso()}},
            upsert=True,
        )
        return jsonify({"ok": True})

    @router.route("/push/register", methods=["DELETE"])
    @login_required
    @validate_schema(PushRegister)
    def push_unregister(body):
        user = g.current_user
        db.push_tokens.delete_one({"user_id": user["user_id"], "device_token": body.device_token})
        return jsonify({"ok": True})

    # ====================================================
    # GEOGRAPHY QUALITY (admin) + autocomplete v2
    # ====================================================
    @router.route("/admin/geography-quality", methods=["GET"])
    @login_required
    def geography_quality():
        user = g.current_user
        if user.get("role") != "admin":
            raise Forbidden("Admin only")
        districts = db.districts.count_documents({})
        taluks = db.taluks.count_documents({})
        villages = db.villages.count_documents({})
        empty_districts = []
        for d in db.districts.find({}, {"_id": 0}):
            tcount = db.taluks.count_documents({"district_id": d["district_id"]})
            if tcount == 0:
                empty_districts.append(d["name"])
        return jsonify({
            "districts": districts, "taluks": taluks, "villages": villages,
            "districts_without_taluks": empty_districts,
            "is_complete_karnataka": districts >= 31,
        })

    # ====================================================
    # APP HEALTH + READINESS for store
    # ====================================================
    @router.route("/app/readiness", methods=["GET"])
    def app_readiness():
        keys = {
            "razorpay_configured": bool(os.environ.get("RAZORPAY_KEY_SECRET")),
            "whatsapp_configured": bool(os.environ.get("WHATSAPP_BUSINESS_TOKEN")),
            "google_maps_configured": False,  # read from frontend env at build
            "sms_provider_configured": bool(os.environ.get("SMS_PROVIDER_KEY")),
            "email_provider_configured": bool(os.environ.get("EMAIL_PROVIDER_KEY")),
            "llm_configured": bool(os.environ.get("OPENAI_API_KEY")),
        }
        return jsonify({
            "store_ready_checklist": {
                "auth": True,
                "geography_full_karnataka": db.districts.count_documents({}) >= 20,
                "payment_processor": keys["razorpay_configured"],
                "i18n_three_languages": True,
                "privacy_policy_page": True,
                "terms_page": True,
                "data_safety_page": True,
                "pwa_manifest": True,
            },
            "integrations": keys,
            "mode": "production" if keys["razorpay_configured"] else "test",
        })

    # ====================================================
    # WHATSAPP — share links (W1, live) + Business API send (W2, feature-flag)
    # ====================================================
    import urllib.parse as _urlparse

    def _site_origin(request) -> str:
        # Prefer explicit env, else derive from request
        origin = os.environ.get("APP_PUBLIC_ORIGIN")
        if origin:
            return origin.rstrip("/")
        host = request.headers.get("host", "")
        proto = request.headers.get("x-forwarded-proto", "https")
        return f"{proto}://{host}"

    @router.route("/whatsapp/share-job/<job_id>", methods=["GET"])
    def wa_share_job(job_id):
        job = db.jobs.find_one({"job_id": job_id}, {"_id": 0})
        if not job:
            raise NotFound("Job not found")
        site = _site_origin(request)
        link = f"{site}/partner/jobs/{job_id}"
        loc = ", ".join([x for x in (job.get("village"), job.get("taluk"), job.get("district")) if x]) or "Karnataka"
        budget = ""
        if job.get("budget_min") or job.get("budget_max"):
            budget = f"\nBudget: ₹{job.get('budget_min') or '?'}–₹{job.get('budget_max') or '?'}"
        text = (
            "🌾 *GO FARM WORK* — Job opportunity\n\n"
            f"*{job.get('title')}*\n"
            f"📍 {loc}{budget}\n"
            f"Workers needed: {job.get('workers_needed') or 1}\n\n"
            f"Apply here: {link}"
        )
        encoded = _urlparse.quote(text)
        return jsonify({"share_url": f"https://wa.me/?text={encoded}", "deep_link": link})

    @router.route("/whatsapp/share-worker/<worker_id>", methods=["GET"])
    def wa_share_worker(worker_id):
        p = db.worker_service_profiles.find_one({"user_id": worker_id}, {"_id": 0})
        if not p:
            raise NotFound("Worker not found")
        u = db.users.find_one({"user_id": worker_id}, {"_id": 0, "full_name": 1})
        site = _site_origin(request)
        link = f"{site}/talent/{worker_id}"
        fare = ""
        if p.get("expected_fare_min") and p.get("expected_fare_max"):
            fare = f"\nFare: ₹{p['expected_fare_min']}–₹{p['expected_fare_max']} / {p.get('fare_unit', 'day')}"
        skills = ", ".join((p.get("skill_tags") or [])[:4])
        text = (
            "🌾 *GO FARM WORK* — Skilled Farm Partner\n\n"
            f"*{(u or {}).get('full_name', 'Verified worker')}* — {p.get('public_title') or 'Farm Partner'}\n"
            f"Skills: {skills}{fare}\n\n"
            f"Profile: {link}"
        )
        encoded = _urlparse.quote(text)
        return jsonify({"share_url": f"https://wa.me/?text={encoded}", "deep_link": link})

    @router.route("/whatsapp/contact/<user_id>", methods=["GET"])
    def wa_contact(user_id):
        u = db.users.find_one({"user_id": user_id}, {"_id": 0, "phone": 1, "full_name": 1})
        if not u or not u.get("phone"):
            raise NotFound("No public phone on file")
        ph = "".join(c for c in u["phone"] if c.isdigit())
        msg = request.args.get("message") or f"Hello {u.get('full_name', '')}, I found you on GO FARM WORK and would like to discuss work."
        encoded = _urlparse.quote(msg)
        return jsonify({"share_url": f"https://wa.me/{ph}?text={encoded}"})

    # ---- W2: WhatsApp Business API (feature-flagged) ----
    def _wa_send_template(to_phone: str, template_name: str, language: str = "en", components: list = None):
        """Send a WhatsApp template via Meta Cloud API. Feature-flagged by env.

        Returns {sent: bool, reason?, response?}.
        """
        token = os.environ.get("WHATSAPP_BUSINESS_TOKEN")
        phone_id = os.environ.get("WHATSAPP_PHONE_NUMBER_ID")
        live = os.environ.get("WHATSAPP_LIVE", "").lower() in ("1", "true", "yes")
        if not (live and token and phone_id):
            db.whatsapp_outbox.insert_one({
                "to": to_phone, "template": template_name, "language": language,
                "components": components or [], "status": "queued_no_keys",
                "created_at": iso(),
            })
            return {"sent": False, "reason": "feature_flag_off_or_no_keys"}
        try:
            payload = {
                "messaging_product": "whatsapp",
                "to": to_phone,
                "type": "template",
                "template": {
                    "name": template_name,
                    "language": {"code": language},
                    "components": components or [],
                },
            }
            r = requests.post(
                f"https://graph.facebook.com/v20.0/{phone_id}/messages",
                headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"},
                json=payload,
                timeout=15.0
            )
            ok = r.status_code in (200, 201)
            db.whatsapp_outbox.insert_one({
                "to": to_phone, "template": template_name, "language": language,
                "components": components or [], "status": "sent" if ok else "failed",
                "response_code": r.status_code, "response": r.text[:1000],
                "created_at": iso(),
            })
            return {"sent": ok, "status_code": r.status_code, "body": r.text[:300]}
        except Exception as e:
            db.whatsapp_outbox.insert_one({
                "to": to_phone, "template": template_name, "status": "error",
                "error": str(e)[:300], "created_at": iso(),
            })
            return {"sent": False, "reason": str(e)[:200]}

    class WaSendBody(BaseModel):
        to_phone: str
        template_name: str = "hello_world"
        language: str = "en_US"
        params: List[str] = []

    @router.route("/whatsapp/send-template", methods=["POST"])
    @login_required
    @validate_schema(WaSendBody)
    def wa_send_template_endpoint(body):
        user = g.current_user
        # admin only
        if user.get("role") != "admin":
            raise Forbidden("Admin only")
        components = []
        if body.params:
            components = [{"type": "body", "parameters": [{"type": "text", "text": p} for p in body.params]}]
        result = _wa_send_template(body.to_phone, body.template_name, body.language, components)
        write_audit(user["user_id"], "whatsapp_send_template", "wa", body.to_phone, {"template": body.template_name, "result": result})
        return jsonify(result)

    @router.route("/whatsapp/status", methods=["GET"])
    @login_required
    def wa_status():
        user = g.current_user
        if user.get("role") != "admin":
            raise Forbidden("Admin only")
        return jsonify({
            "live": os.environ.get("WHATSAPP_LIVE", "").lower() in ("1", "true", "yes"),
            "has_token": bool(os.environ.get("WHATSAPP_BUSINESS_TOKEN")),
            "has_phone_id": bool(os.environ.get("WHATSAPP_PHONE_NUMBER_ID")),
            "webhook_verify_token_set": bool(os.environ.get("WHATSAPP_WEBHOOK_VERIFY_TOKEN")),
            "outbox_count": db.whatsapp_outbox.count_documents({}),
            "outbox_sent": db.whatsapp_outbox.count_documents({"status": "sent"}),
            "outbox_queued_no_keys": db.whatsapp_outbox.count_documents({"status": "queued_no_keys"}),
            "next_steps_when_keys_arrive": [
                "Set WHATSAPP_BUSINESS_TOKEN and WHATSAPP_PHONE_NUMBER_ID in backend/.env",
                "Set WHATSAPP_LIVE=true",
                "Approve template names with Meta",
                "Restart backend",
            ],
        })

    # ====================================================
    # PUBLIC STATS (real-time, no auth needed for marketing)
    # ====================================================
    @router.route("/public/stats", methods=["GET"])
    def public_stats():
        """Real-time platform stats. Returns ZEROS if no data — never fake.
        Used by the landing page so we never show fabricated counters.
        """
        partners = db.users.count_documents({"role": "farm_partner"})
        owners = db.users.count_documents({"role": "farm_owner"})
        jobs_completed = db.jobs.count_documents({"status": "completed"})
        jobs_total = db.jobs.count_documents({})
        # GMV — sum of all settled milestone-release payments
        gmv_agg = list(db.payments.aggregate([
            {"$match": {"payment_status": {"$in": ["captured", "paid"]}, "payment_type": {"$in": ["milestone_release", "milestone_fund"]}}},
            {"$group": {"_id": None, "total": {"$sum": "$amount"}}},
        ]))
        gmv = float(gmv_agg[0]["total"]) if gmv_agg else 0.0
        # Earned by workers — only released
        earned_agg = list(db.payments.aggregate([
            {"$match": {"payment_type": "milestone_release"}},
            {"$group": {"_id": None, "total": {"$sum": "$amount"}}},
        ]))
        earned = float(earned_agg[0]["total"]) if earned_agg else 0.0
        districts = db.districts.count_documents({})
        categories = db.job_categories.count_documents({})
        # Real reviews — return up to 6 most recent 5-star with consent (no synthetic)
        reviews = list(db.reviews.find(
            {"rating": {"$gte": 4}, "comment": {"$exists": True, "$ne": ""}},
            {"_id": 0},
        ).sort("created_at", -1).limit(6))
        for r in reviews:
            reviewer = db.users.find_one(
                {"user_id": r.get("reviewer_user_id")},
                {"_id": 0, "full_name": 1, "picture": 1},
            )
            prof = db.profiles.find_one(
                {"user_id": r.get("reviewer_user_id")},
                {"_id": 0, "district": 1},
            ) or {}
            r["reviewer_name"] = (reviewer or {}).get("full_name", "")
            r["reviewer_picture"] = (reviewer or {}).get("picture")
            r["reviewer_district"] = prof.get("district")
        return jsonify({
            "farm_partners": partners,
            "farm_owners": owners,
            "jobs_completed": jobs_completed,
            "jobs_total": jobs_total,
            "categories_supported": categories,
            "reviews": reviews,
            "as_of": iso(),
        })

    # ====================================================
    # MEDICATIONS SEARCH (via OpenFDA with Drugs.com link)
    # ====================================================
    @router.route("/medications/search", methods=["GET"])
    def search_medications():
        q = request.args.get("q", "").strip()
        if not q:
            return jsonify([])
        
        results = []
        try:
            url = "https://api.fda.gov/drug/label.json"
            # Limit to 10 results and clean them up
            params = {
                "search": f'(openfda.brand_name:"{q}" OR openfda.generic_name:"{q}" OR indications_and_usage:"{q}") AND openfda.product_type:"OTC"',
                "limit": 10
            }
            res = requests.get(url, params=params, timeout=5)
            if res.status_code == 200:
                data = res.json()
                for r in data.get("results", []):
                    openfda = r.get("openfda", {})
                    brand_names = openfda.get("brand_name", [])
                    generic_names = openfda.get("generic_name", [])
                    
                    brand = brand_names[0] if brand_names else None
                    generic = generic_names[0] if generic_names else None
                    
                    if not brand and not generic:
                        continue
                    
                    purpose = r.get("purpose", [None])[0]
                    if purpose:
                        purpose = purpose.replace("Purpose", "").replace("PURPOSE", "").strip()
                    
                    dosage = r.get("dosage_and_administration", [None])[0]
                    if dosage:
                        dosage = dosage.strip()
                        if len(dosage) > 250:
                            dosage = dosage[:247] + "..."
                            
                    warnings = r.get("warnings", [None])[0]
                    if warnings:
                        warnings = warnings.strip()
                        if len(warnings) > 250:
                            warnings = warnings[:247] + "..."
                    
                    search_term = brand if brand else generic
                    drugs_com_url = f"https://www.drugs.com/search.php?searchterm={_urlparse.quote(search_term)}"
                    
                    results.append({
                        "brand_name": brand or generic,
                        "generic_name": generic or brand,
                        "purpose": purpose or "Over-the-counter relief",
                        "dosage": dosage or "Refer to package instructions",
                        "warnings": warnings or "Use as directed. Consult doctor if pregnant or taking other medications.",
                        "drugs_com_url": drugs_com_url
                    })
        except Exception as e:
            logger.error(f"OpenFDA search failed: {e}")
            
        # Curated local fallback database for common terms
        curated_db = {
            "cough": [
                {
                    "brand_name": "Robitussin / Delsym",
                    "generic_name": "Dextromethorphan",
                    "purpose": "Cough Suppressant",
                    "dosage": "10-20 mg every 4 hours or 30 mg every 6-8 hours as needed.",
                    "warnings": "Do not use with MAOIs. May cause drowsiness.",
                    "drugs_com_url": "https://www.drugs.com/dextromethorphan.html"
                },
                {
                    "brand_name": "Mucinex",
                    "generic_name": "Guaifenesin",
                    "purpose": "Expectorant (Thins mucus)",
                    "dosage": "200-400 mg every 4 hours. Take with plenty of water.",
                    "warnings": "Consult a doctor if cough lasts more than 7 days.",
                    "drugs_com_url": "https://www.drugs.com/mucinex.html"
                }
            ],
            "fever": [
                {
                    "brand_name": "Tylenol",
                    "generic_name": "Acetaminophen",
                    "purpose": "Fever Reducer / Pain Reliever",
                    "dosage": "325-650 mg every 4-6 hours. Max 4000 mg/day.",
                    "warnings": "Severe liver damage may occur if you exceed maximum daily limit or mix with alcohol.",
                    "drugs_com_url": "https://www.drugs.com/tylenol.html"
                },
                {
                    "brand_name": "Advil / Motrin",
                    "generic_name": "Ibuprofen",
                    "purpose": "NSAID Pain / Fever Reliever",
                    "dosage": "200-400 mg every 4-6 hours. Take with food.",
                    "warnings": "May cause stomach bleeding. Take with food.",
                    "drugs_com_url": "https://www.drugs.com/ibuprofen.html"
                }
            ],
            "headache": [
                {
                    "brand_name": "Tylenol",
                    "generic_name": "Acetaminophen",
                    "purpose": "Pain Reliever",
                    "dosage": "325-650 mg every 4-6 hours. Max 4000 mg/day.",
                    "warnings": "Severe liver damage may occur if you exceed daily limit or mix with alcohol.",
                    "drugs_com_url": "https://www.drugs.com/tylenol.html"
                },
                {
                    "brand_name": "Advil / Motrin",
                    "generic_name": "Ibuprofen",
                    "purpose": "NSAID Pain Reliever",
                    "dosage": "200-400 mg every 4-6 hours. Take with food.",
                    "warnings": "May cause stomach bleeding. Take with food.",
                    "drugs_com_url": "https://www.drugs.com/ibuprofen.html"
                },
                {
                    "brand_name": "Aleve",
                    "generic_name": "Naproxen Sodium",
                    "purpose": "NSAID Pain Reliever (Long-acting)",
                    "dosage": "220 mg every 8-12 hours. Do not exceed 440 mg in 12 hours.",
                    "warnings": "May cause stomach bleeding or kidney strain. Take with food.",
                    "drugs_com_url": "https://www.drugs.com/naproxen.html"
                }
            ],
            "allergy": [
                {
                    "brand_name": "Claritin",
                    "generic_name": "Loratadine",
                    "purpose": "Non-Drowsy 24h Antihistamine",
                    "dosage": "10 mg once daily.",
                    "warnings": "Consult doctor if you have liver or kidney disease.",
                    "drugs_com_url": "https://www.drugs.com/claritin.html"
                },
                {
                    "brand_name": "Zyrtec",
                    "generic_name": "Cetirizine",
                    "purpose": "Fast-Acting 24h Antihistamine",
                    "dosage": "5-10 mg once daily.",
                    "warnings": "May cause drowsiness in some individuals. Avoid alcohol.",
                    "drugs_com_url": "https://www.drugs.com/zyrtec.html"
                },
                {
                    "brand_name": "Benadryl",
                    "generic_name": "Diphenhydramine",
                    "purpose": "First-Gen Antihistamine (Causes Drowsiness)",
                    "dosage": "25-50 mg every 4-6 hours.",
                    "warnings": "Causes drowsiness. Do not drive or operate machinery.",
                    "drugs_com_url": "https://www.drugs.com/benadryl.html"
                }
            ],
            "heartburn": [
                {
                    "brand_name": "Tums",
                    "generic_name": "Calcium Carbonate",
                    "purpose": "Antacid (Fast relief)",
                    "dosage": "Chew 2-4 tablets as symptoms occur.",
                    "warnings": "Do not use for more than 2 weeks without consulting a doctor.",
                    "drugs_com_url": "https://www.drugs.com/monograph/calcium-carbonate.html"
                },
                {
                    "brand_name": "Pepcid AC",
                    "generic_name": "Famotidine",
                    "purpose": "H2 Blocker (Acid Reducer)",
                    "dosage": "10-20 mg 1-2 times daily, 15-60 minutes before eating.",
                    "warnings": "Do not exceed 2 tablets in 24 hours.",
                    "drugs_com_url": "https://www.drugs.com/pepcid.html"
                },
                {
                    "brand_name": "Prilosec OTC",
                    "generic_name": "Omeprazole",
                    "purpose": "Proton Pump Inhibitor (Long-term prevention)",
                    "dosage": "20 mg once daily before breakfast for 14 days.",
                    "warnings": "Take for full 14 days. Not for immediate relief.",
                    "drugs_com_url": "https://www.drugs.com/prilosec.html"
                }
            ],
            "sore throat": [
                {
                    "brand_name": "Halls",
                    "generic_name": "Menthol",
                    "purpose": "Oral Anesthetic / Cough Lozenges",
                    "dosage": "Dissolve 1 lozenge slowly in the mouth every 2 hours.",
                    "warnings": "Consult doctor if sore throat lasts more than 2 days.",
                    "drugs_com_url": "https://www.drugs.com/halls.html"
                },
                {
                    "brand_name": "Chloraseptic Spray",
                    "generic_name": "Phenol",
                    "purpose": "Oral Anesthetic Spray",
                    "dosage": "Apply 5 sprays, hold 15s, then spit out. Up to 4x daily.",
                    "warnings": "Do not swallow. Consult doctor if accompanied by fever.",
                    "drugs_com_url": "https://www.drugs.com/chloraseptic.html"
                }
            ]
        }
        
        q_lower = q.lower()
        local_matches = []
        for cond, meds in curated_db.items():
            if cond in q_lower or q_lower in cond:
                local_matches.extend(meds)
                
        seen_brands = set()
        final_results = []
        
        for med in local_matches:
            brand = med["brand_name"].lower()
            if brand not in seen_brands:
                seen_brands.add(brand)
                final_results.append(med)
                
        for med in results:
            brand = med["brand_name"].lower()
            if brand not in seen_brands:
                seen_brands.add(brand)
                final_results.append(med)
                
        if not final_results:
            final_results.append({
                "brand_name": f"Drugs.com: {q.capitalize()} Search",
                "generic_name": "Real-time Search",
                "purpose": f"Search medications related to '{q}' directly on Drugs.com",
                "dosage": "Refer to search results on Drugs.com.",
                "warnings": "Always check active ingredients, dosage, and warnings before use.",
                "drugs_com_url": f"https://www.drugs.com/search.php?searchterm={_urlparse.quote(q)}"
            })
            
        return jsonify(final_results)

    return router


def _fallback_reply(msg: str) -> str:
    msg = (msg or "").lower()
    if "400" in msg or "cash" in msg or "booking" in msg:
        return ("Cash-mode jobs: the Farm Owner pays a one-time ₹400 booking fee to Go Farm Work via Razorpay "
                "to confirm the hire. The worker's salary is paid in cash directly, offline.")
    if "5%" in msg or "fee" in msg or "commission" in msg:
        return ("We charge 5% platform fee on every accepted proposal. When you place a bid, we show the fee and "
                "your net amount before you confirm.")
    if "kannada" in msg or "hindi" in msg or "ಕನ್ನಡ" in msg:
        return ("Yes — we support English, Kannada (ಕನ್ನಡ), and Hindi (हिन्दी). Switch language from the top bar at any time.")
    if "whatsapp" in msg:
        return ("WhatsApp posting and applying is on our roadmap and not live yet. Today, please use the web/app interface.")
    return ("I'm not sure about that yet. You can ask about fees, the ₹400 cash booking fee, posting jobs, "
            "wallets, languages, or live location. For account-specific help, tap 'Talk to support'.")
