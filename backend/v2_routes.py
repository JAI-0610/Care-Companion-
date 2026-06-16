"""
Go Farm Work v2 — expanded marketplace features:
- 5% bid fee calculator + fee snapshots
- ₹400 cash-mode booking fee flow
- Workers-filled / auto-close logic
- Worker service profiles (Talent Marketplace / "Hire Me")
- Counter-offer / negotiation engine
- Wallet ledger
- Chatbot FAQ
"""
from flask import Blueprint, request, jsonify, g
from pydantic import BaseModel, Field
from typing import Optional, List, Literal
from datetime import datetime, timezone
import uuid
from werkzeug.exceptions import NotFound, Forbidden, BadRequest

from auth import login_required, validate_schema, new_id

PLATFORM_FEE_PERCENT = 5.0
CASH_BOOKING_FEE_MIN = 400.0

def iso():
    return datetime.now(timezone.utc).isoformat()


def make_v2_router(db):
    """Factory creating the v2 router with closed-over db handle."""
    router = Blueprint("v2", __name__, url_prefix="/api")

    # ===================================================================
    # FEE CALCULATOR
    # ===================================================================
    class FeeCalcBody(BaseModel):
        bid_amount: float = Field(ge=0)
        owner_offered_amount: Optional[float] = None

    @router.route("/proposals/calculate-fee", methods=["POST"])
    @login_required
    @validate_schema(FeeCalcBody)
    def calculate_fee(body):
        fee = round(body.bid_amount * PLATFORM_FEE_PERCENT / 100.0, 2)
        net = round(body.bid_amount - fee, 2)
        return jsonify({
            "bid_amount": body.bid_amount,
            "owner_offered_amount": body.owner_offered_amount,
            "fee_percent": PLATFORM_FEE_PERCENT,
            "fee_amount": fee,
            "worker_net_amount": net,
            "currency": "INR",
        })

    # ===================================================================
    # COUNTER OFFERS
    # ===================================================================
    class CounterBody(BaseModel):
        amount: float = Field(ge=0)
        note: Optional[str] = None

    @router.route("/proposals/<proposal_id>/counter", methods=["POST"])
    @login_required
    @validate_schema(CounterBody)
    def counter_offer(body, proposal_id):
        user = g.current_user
        prop = db.proposals.find_one({"proposal_id": proposal_id}, {"_id": 0})
        if not prop:
            raise NotFound("Proposal not found")
        job = db.jobs.find_one({"job_id": prop["job_id"]}, {"_id": 0})
        if not job:
            raise NotFound("Job not found")
        is_owner = job["owner_user_id"] == user["user_id"]
        is_partner = prop["partner_user_id"] == user["user_id"]
        if not (is_owner or is_partner):
            raise Forbidden("Forbidden")
        from_side = "owner" if is_owner else "partner"
        db.negotiations.insert_one({
            "negotiation_id": new_id("neg"),
            "proposal_id": proposal_id,
            "from_user_id": user["user_id"],
            "from_side": from_side,
            "amount": body.amount,
            "note": body.note,
            "status": "pending",
            "created_at": iso(),
        })
        db.proposals.update_one(
            {"proposal_id": proposal_id},
            {"$set": {
                "negotiation_status": "awaiting_partner" if is_owner else "awaiting_owner",
                "last_counter_amount": body.amount,
                "updated_at": iso(),
            }},
        )
        return jsonify({"ok": True, "amount": body.amount, "from": from_side})

    @router.route("/proposals/<proposal_id>/negotiations", methods=["GET"])
    @login_required
    def list_negotiations(proposal_id):
        items = list(db.negotiations.find({"proposal_id": proposal_id}, {"_id": 0}).sort("created_at", 1).limit(200))
        return jsonify(items)

    @router.route("/proposals/<proposal_id>/accept-counter", methods=["POST"])
    @login_required
    def accept_counter(proposal_id):
        user = g.current_user
        prop = db.proposals.find_one({"proposal_id": proposal_id}, {"_id": 0})
        if not prop:
            raise NotFound("Proposal not found")
        latest = db.negotiations.find_one(
            {"proposal_id": proposal_id, "status": "pending"},
            {"_id": 0}, sort=[("created_at", -1)],
        )
        if not latest:
            raise BadRequest("No counter offer pending")
        new_amount = latest["amount"]
        fee = round(new_amount * PLATFORM_FEE_PERCENT / 100.0, 2)
        db.proposals.update_one(
            {"proposal_id": proposal_id},
            {"$set": {
                "bid_amount": new_amount,
                "fee_amount_snapshot": fee,
                "worker_net_amount_snapshot": round(new_amount - fee, 2),
                "negotiation_status": "agreed",
                "updated_at": iso(),
            }},
        )
        db.negotiations.update_one(
            {"negotiation_id": latest["negotiation_id"]},
            {"$set": {"status": "accepted"}},
        )
        return jsonify({"ok": True, "agreed_amount": new_amount})

    # ===================================================================
    # CASH-MODE BOOKING FEE (₹400)
    # ===================================================================
    @router.route("/jobs/<job_id>/booking-fee-status", methods=["GET"])
    @login_required
    def booking_fee_status(job_id):
        job = db.jobs.find_one({"job_id": job_id}, {"_id": 0})
        if not job:
            raise NotFound("Job not found")
        return jsonify({
            "payment_mode": job.get("payment_mode", "online"),
            "cash_booking_fee_required": job.get("payment_mode") == "cash",
            "cash_booking_fee_amount": CASH_BOOKING_FEE_MIN,
            "cash_booking_fee_status": job.get("cash_booking_fee_status", "not_required" if job.get("payment_mode") != "cash" else "pending"),
        })

    @router.route("/jobs/<job_id>/pay-booking-fee", methods=["POST"])
    @login_required
    def pay_booking_fee(job_id):
        """Mock Razorpay payment for ₹400 booking fee. Marks status=paid."""
        user = g.current_user
        job = db.jobs.find_one({"job_id": job_id}, {"_id": 0})
        if not job:
            raise NotFound("Job not found")
        if job["owner_user_id"] != user["user_id"]:
            raise Forbidden("Only the Farm Owner can pay")
        if job.get("payment_mode") != "cash":
            raise BadRequest("Booking fee only applies to cash-mode jobs")
        order_id = f"order_{uuid.uuid4().hex[:14]}"
        payment_id = f"pay_{uuid.uuid4().hex[:14]}"
        amount = CASH_BOOKING_FEE_MIN
        db.jobs.update_one(
            {"job_id": job_id},
            {"$set": {
                "cash_booking_fee_status": "paid",
                "cash_booking_fee_amount": amount,
                "cash_booking_fee_payment_id": payment_id,
                "cash_booking_fee_paid_at": iso(),
            }},
        )
        db.payments.insert_one({
            "payment_id": new_id("pmt"),
            "job_id": job_id,
            "payer_user_id": user["user_id"],
            "razorpay_order_id": order_id,
            "razorpay_payment_id": payment_id,
            "amount": amount,
            "currency": "INR",
            "payment_status": "captured",
            "payment_type": "cash_booking_fee",
            "created_at": iso(),
        })
        # Platform-side ledger entry (revenue)
        db.wallet_ledger.insert_one({
            "ledger_id": new_id("ledg"),
            "wallet_owner": "platform",
            "user_id": user["user_id"],
            "entry_type": "booking_fee",
            "direction": "credit",
            "amount": amount,
            "currency": "INR",
            "reference_type": "job",
            "reference_id": job_id,
            "status": "settled",
            "created_at": iso(),
        })
        return jsonify({"ok": True, "order_id": order_id, "payment_id": payment_id, "amount": amount})

    @router.route("/jobs/<job_id>/mark-cash-paid", methods=["POST"])
    @login_required
    def mark_cash_paid(job_id):
        """Owner marks that they've handed cash to the worker offline (audit only)."""
        user = g.current_user
        job = db.jobs.find_one({"job_id": job_id}, {"_id": 0})
        if not job:
            raise NotFound("Job not found")
        if job["owner_user_id"] != user["user_id"]:
            raise Forbidden("Forbidden")
        db.jobs.update_one(
            {"job_id": job_id},
            {"$set": {"cash_offline_marked_paid": True, "cash_offline_paid_at": iso()}},
        )
        return jsonify({"ok": True})

    # ===================================================================
    # WORKER SERVICE PROFILES / TALENT MARKETPLACE
    # ===================================================================
    class WorkerProfile(BaseModel):
        public_title: Optional[str] = None
        short_pitch: Optional[str] = None
        skill_tags: List[str] = []
        service_categories: List[str] = []
        expected_fare_min: Optional[float] = None
        expected_fare_max: Optional[float] = None
        fare_unit: Optional[Literal["day", "hour", "job", "month"]] = "day"
        travel_radius_km: Optional[int] = 25
        profile_visibility: Literal["public", "invite_only", "hidden"] = "public"
        open_to_work_status: Literal["immediate", "this_week", "seasonal", "unavailable"] = "immediate"
        portfolio_media: List[str] = []
        languages: List[str] = []
        equipment: List[str] = []

    @router.route("/workers/profile/me", methods=["GET"])
    @login_required
    def get_my_worker_profile():
        user = g.current_user
        prof = db.worker_service_profiles.find_one(
            {"user_id": user["user_id"]}, {"_id": 0}
        )
        return jsonify(prof or {})

    @router.route("/workers/profile", methods=["POST"])
    @login_required
    @validate_schema(WorkerProfile)
    def upsert_worker_profile(body):
        user = g.current_user
        if user.get("role") not in ("farm_partner", "admin"):
            raise Forbidden("Only Farm Partners can publish a service profile")
        doc = body.model_dump()
        doc["user_id"] = user["user_id"]
        doc["updated_at"] = iso()
        existing = db.worker_service_profiles.find_one({"user_id": user["user_id"]}, {"_id": 0})
        if existing:
            db.worker_service_profiles.update_one({"user_id": user["user_id"]}, {"$set": doc})
        else:
            doc["created_at"] = iso()
            doc["profile_completeness_score"] = _score_profile(doc)
            db.worker_service_profiles.insert_one(doc)
        out = db.worker_service_profiles.find_one({"user_id": user["user_id"]}, {"_id": 0})
        return jsonify(out)

    @router.route("/workers", methods=["GET"])
    def list_workers():
        q = request.args.get("q")
        category = request.args.get("category")
        district = request.args.get("district")
        availability = request.args.get("availability")
        limit = request.args.get("limit", default=50, type=int)

        f: dict = {"profile_visibility": "public"}
        if availability:
            f["open_to_work_status"] = availability
        if category:
            f["service_categories"] = category
        profs = list(db.worker_service_profiles.find(f, {"_id": 0}).limit(limit))
        # Hydrate with user info + location filter
        out = []
        for p in profs:
            u = db.users.find_one(
                {"user_id": p["user_id"]},
                {"_id": 0, "password_hash": 0, "email": 0},
            )
            pf = db.profiles.find_one({"user_id": p["user_id"]}, {"_id": 0}) or {}
            if district and pf.get("district") and pf.get("district") != district:
                continue
            if q:
                ql = q.lower()
                hay = " ".join([
                    p.get("public_title") or "",
                    p.get("short_pitch") or "",
                    " ".join(p.get("skill_tags") or []),
                    u.get("full_name") if u else "",
                ]).lower()
                if ql not in hay:
                    continue
            # Rating snapshot
            agg = list(db.reviews.aggregate([
                {"$match": {"reviewee_user_id": p["user_id"]}},
                {"$group": {"_id": None, "avg": {"$avg": "$rating"}, "count": {"$sum": 1}}},
            ]))
            p["user"] = u
            p["location"] = {"district": pf.get("district"), "taluk": pf.get("taluk"), "village": pf.get("village")}
            p["rating"] = {"avg": (agg[0]["avg"] if agg else 0) or 0, "count": (agg[0]["count"] if agg else 0)}
            p["badges"] = _compute_badges(p, p["rating"])
            out.append(p)
        return jsonify(out)

    @router.route("/workers/<worker_id>", methods=["GET"])
    def get_worker(worker_id):
        p = db.worker_service_profiles.find_one({"user_id": worker_id}, {"_id": 0})
        if not p:
            raise NotFound("Worker profile not found")
        u = db.users.find_one({"user_id": worker_id}, {"_id": 0, "password_hash": 0, "email": 0})
        pf = db.profiles.find_one({"user_id": worker_id}, {"_id": 0}) or {}
        agg = list(db.reviews.aggregate([
            {"$match": {"reviewee_user_id": worker_id}},
            {"$group": {"_id": None, "avg": {"$avg": "$rating"}, "count": {"$sum": 1}}},
        ]))
        reviews = list(db.reviews.find({"reviewee_user_id": worker_id}, {"_id": 0}).sort("created_at", -1).limit(20))
        rating = {"avg": (agg[0]["avg"] if agg else 0) or 0, "count": (agg[0]["count"] if agg else 0)}
        return jsonify({
            "profile": p,
            "user": u,
            "location": {"district": pf.get("district"), "taluk": pf.get("taluk"), "village": pf.get("village")},
            "rating": rating,
            "badges": _compute_badges(p, rating),
            "reviews": reviews,
        })

    @router.route("/workers/<worker_id>/save", methods=["POST"])
    @login_required
    def save_worker(worker_id):
        user = g.current_user
        existing = db.saved_workers.find_one({"user_id": user["user_id"], "worker_id": worker_id})
        if existing:
            db.saved_workers.delete_one({"user_id": user["user_id"], "worker_id": worker_id})
            return jsonify({"saved": False})
        db.saved_workers.insert_one({
            "user_id": user["user_id"], "worker_id": worker_id, "created_at": iso(),
        })
        return jsonify({"saved": True})

    class InviteBody(BaseModel):
        job_id: str
        message: Optional[str] = None

    @router.route("/workers/<worker_id>/invite", methods=["POST"])
    @login_required
    @validate_schema(InviteBody)
    def invite_worker(body, worker_id):
        user = g.current_user
        if user.get("role") != "farm_owner":
            raise Forbidden("Only Farm Owners can invite")
        job = db.jobs.find_one({"job_id": body.job_id}, {"_id": 0})
        if not job or job["owner_user_id"] != user["user_id"]:
            raise Forbidden("Job not yours")
        db.notifications.insert_one({
            "notif_id": new_id("notif"),
            "user_id": worker_id,
            "type": "invitation",
            "title": f"You've been invited to: {job['title']}",
            "body": body.message or "A Farm Owner invited you to apply.",
            "link": f"/partner/jobs/{body.job_id}",
            "read": False,
            "created_at": iso(),
        })
        return jsonify({"ok": True})

    # ===================================================================
    # WALLET / LEDGER
    # ===================================================================
    def _get_wallet_data(user):
        ledger = list(db.wallet_ledger.find(
            {"user_id": user["user_id"]}, {"_id": 0}
        ).sort("created_at", -1).limit(500))
        held = sum(e["amount"] for e in ledger if e.get("direction") == "credit" and e.get("status") == "held")
        avail = sum(e["amount"] for e in ledger if e.get("direction") == "credit" and e.get("status") == "settled")
        avail -= sum(e["amount"] for e in ledger if e.get("direction") == "debit" and e.get("status") in ("settled", "withdrawn"))
        return {
            "held_balance": round(max(0, held), 2),
            "available_balance": round(max(0, avail), 2),
            "currency": "INR",
        }

    @router.route("/wallet", methods=["GET"])
    @login_required
    def get_wallet():
        user = g.current_user
        return jsonify(_get_wallet_data(user))

    @router.route("/wallet/ledger", methods=["GET"])
    @login_required
    def get_ledger():
        user = g.current_user
        items = list(db.wallet_ledger.find(
            {"user_id": user["user_id"]}, {"_id": 0}
        ).sort("created_at", -1).limit(500))
        return jsonify(items)

    class WithdrawBody(BaseModel):
        amount: float = Field(gt=0)
        method: Literal["upi", "bank"] = "upi"
        destination: Optional[str] = None

    @router.route("/wallet/withdraw", methods=["POST"])
    @login_required
    @validate_schema(WithdrawBody)
    def request_withdrawal(body):
        user = g.current_user
        wallet_res = _get_wallet_data(user)
        if body.amount > wallet_res["available_balance"]:
            raise BadRequest("Amount exceeds available balance")
        wd_id = new_id("wd")
        db.wallet_withdrawals.insert_one({
            "withdrawal_id": wd_id,
            "user_id": user["user_id"],
            "amount": body.amount,
            "method": body.method,
            "destination": body.destination,
            "status": "requested",
            "created_at": iso(),
        })
        db.wallet_ledger.insert_one({
            "ledger_id": new_id("ledg"),
            "user_id": user["user_id"],
            "entry_type": "withdrawal_request",
            "direction": "debit",
            "amount": body.amount,
            "currency": "INR",
            "reference_type": "withdrawal",
            "reference_id": wd_id,
            "status": "settled",
            "created_at": iso(),
        })
        return jsonify({"withdrawal_id": wd_id, "status": "requested"})

    # ===================================================================
    # CHATBOT FAQ
    # ===================================================================
    FAQS = [
        {"id": "fee", "q": "How does the platform fee work?", "a": "Go Farm Work charges a 5% platform fee on every accepted proposal. When you submit a bid, we show the fee and your net amount before you confirm."},
        {"id": "cash", "q": "What is the ₹400 cash booking fee?", "a": "If a Farm Owner chooses to pay the worker in cash offline, they must pay a one-time ₹400 booking fee to Go Farm Work to confirm the hire. The salary itself is still paid in cash directly between the owner and worker."},
        {"id": "post", "q": "How do I post a job?", "a": "Sign up as a Farm Owner → tap 'Post Work' → fill out the 4-step wizard (category, details, location, payment) → publish. Workers nearby will see it instantly."},
        {"id": "apply", "q": "How do I apply to jobs as a worker?", "a": "Sign up as a Farm Partner → go to 'Find Work' → open a job → tap 'Send Proposal' → enter your bid and a short message. You can see the 5% fee and your net pay before sending."},
        {"id": "wallet", "q": "When do I get paid?", "a": "Once the Farm Owner releases your milestone, the amount appears in your wallet as 'Available'. You can then request a withdrawal to UPI or bank."},
        {"id": "trust", "q": "How is trust built?", "a": "Mobile verification, ID checks, skill endorsements, repeat hires, on-time scores, and ratings from past Farm Owners build your Trust Score."},
        {"id": "lang", "q": "Can I use Go Farm Work in Kannada or Hindi?", "a": "Yes — switch language anytime from the top bar. We support English, Kannada (ಕನ್ನಡ), and Hindi (हिन्दी)."},
        {"id": "whatsapp", "q": "Can I use WhatsApp to post or find jobs?", "a": "WhatsApp posting and applying is on our roadmap and not live yet. Today, please use the web/app interface."},
        {"id": "location", "q": "Why do you need my location?", "a": "We use your district/taluk/village to match you with nearby work. Live field location is only shared when you start an active job, and you can stop it anytime."},
        {"id": "talent", "q": "How can a Farm Owner find me directly?", "a": "Build your 'Hire Me' profile from your dashboard — add skills, fare range, availability, and equipment. Owners can search the Talent directory and invite you to apply."},
    ]

    @router.route("/chatbot/faq", methods=["GET"])
    def get_faqs():
        return jsonify(FAQS)

    class ChatbotMessage(BaseModel):
        message: str
        context_page: Optional[str] = None
        language: Optional[str] = "en"

    @router.route("/chatbot/message", methods=["POST"])
    @validate_schema(ChatbotMessage)
    def chatbot_message(body):
        msg = (body.message or "").lower()
        # Truthful keyword router — no fake AI claims
        best = None
        keywords = {
            "cash": ["cash", "400", "booking fee", "offline pay", "रुपये"],
            "whatsapp": ["whatsapp", "wa.me", "ವಾಟ್ಸ್"],
            "wallet": ["wallet", "withdraw", "payout", "earnings", "balance"],
            "talent": ["talent", "hire me", "directory", "find worker"],
            "trust": ["trust", "rating", "verified", "badge", "review"],
            "location": ["location", "gps", "live tracking", "field pin"],
            "lang": ["kannada", "hindi", "language", "ಕನ್ನಡ", "हिन्दी"],
            "post": ["post a job", "create job", "publish", "hire someone"],
            "apply": ["apply", "proposal", "bid", "send offer"],
            "fee": ["5%", "platform fee", "commission", "charges", "fee"],
        }
        for fid, kws in keywords.items():
            if any(k in msg for k in kws):
                best = fid
                break
        if best:
            faq = next(f for f in FAQS if f["id"] == best)
            return jsonify({"reply": faq["a"], "matched_faq": faq["id"], "kind": "faq"})
        return jsonify({
            "reply": "I'm not sure about that yet. You can browse the FAQ below or tap 'Talk to support' to reach a human.",
            "kind": "fallback",
            "suggestions": [{"id": f["id"], "q": f["q"]} for f in FAQS[:5]],
        })

    return router


def _score_profile(p: dict) -> int:
    score = 0
    if p.get("public_title"): score += 15
    if p.get("short_pitch") and len(p["short_pitch"]) > 30: score += 15
    if p.get("skill_tags") and len(p["skill_tags"]) >= 3: score += 20
    if p.get("service_categories"): score += 10
    if p.get("expected_fare_min") and p.get("expected_fare_max"): score += 10
    if p.get("travel_radius_km"): score += 5
    if p.get("languages"): score += 10
    if p.get("equipment"): score += 10
    if p.get("portfolio_media"): score += 5
    return min(100, score)


def _compute_badges(p: dict, rating: dict) -> List[str]:
    badges = []
    if (p.get("profile_completeness_score") or 0) >= 80:
        badges.append("complete_profile")
    if p.get("open_to_work_status") == "immediate":
        badges.append("available_now")
    if p.get("open_to_work_status") == "this_week":
        badges.append("available_this_week")
    if p.get("equipment"):
        badges.append("equipment_ready")
    if (rating.get("avg") or 0) >= 4.5 and (rating.get("count") or 0) >= 3:
        badges.append("top_rated")
    if (rating.get("count") or 0) >= 1 and (rating.get("count") or 0) < 3:
        badges.append("rising_talent")
    return badges
