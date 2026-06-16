"""
Go Farm Work - Flask backend
All routes prefixed with /api.
"""
from flask import Flask, Blueprint, request, jsonify, make_response, g
from werkzeug.exceptions import HTTPException, NotFound, Forbidden, BadRequest, Unauthorized
from dotenv import load_dotenv
from flask_cors import CORS
from pymongo import MongoClient
from pydantic import BaseModel, Field, EmailStr
from typing import List, Optional, Literal
from datetime import datetime, timezone, timedelta
from pathlib import Path
import os
import logging
import uuid
import random

from auth import (
    hash_password, verify_password, create_jwt, decode_jwt,
    exchange_google_session, get_current_user, new_user_id, new_id,
    login_required, admin_required, validate_schema
)
from seed import seed_database
from v2_routes import make_v2_router
from routes_v3 import make_v3_router

ROOT_DIR = Path(__file__).parent
load_dotenv(ROOT_DIR / ".env")

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("gofarmwork")

# ---------- DB ----------
mongo_url = os.environ.get("MONGO_URL", "mongodb://localhost:27017")
client = MongoClient(mongo_url)
db = client[os.environ.get("DB_NAME", "gofarmwork")]

# Create Flask Application
app = Flask(__name__, static_folder=None)
app.db = db  # Attach db to current_app

CORS(app, supports_credentials=True, origins=os.environ.get("CORS_ORIGINS", "*").split(","))

api = Blueprint("api", __name__, url_prefix="/api")


def iso(dt: datetime | None = None) -> str:
    return (dt or datetime.now(timezone.utc)).isoformat()


# ======================================================
# Flask Error Handlers
# ======================================================
@app.errorhandler(HTTPException)
def handle_http_exception(e):
    return jsonify({"detail": e.description}), e.code

@app.errorhandler(Exception)
def handle_generic_exception(e):
    logger.exception("Unhandled server exception")
    return jsonify({"detail": str(e)}), 500


# ======================================================
# Pydantic Schemas
# ======================================================
class SignupBody(BaseModel):
    email: EmailStr
    password: str = Field(min_length=6)
    full_name: str = Field(min_length=1)


class LoginBody(BaseModel):
    email: EmailStr
    password: str


class GoogleSessionBody(BaseModel):
    session_id: str


class RoleBody(BaseModel):
    role: Literal["farm_owner", "farm_partner"]


class OnboardingBody(BaseModel):
    role: Literal["farm_owner", "farm_partner"]
    full_name: str
    phone: Optional[str] = None
    district: Optional[str] = None
    taluk: Optional[str] = None
    village: Optional[str] = None
    preferred_language: Optional[str] = "en"
    # owner
    farm_name: Optional[str] = None
    main_crops: Optional[List[str]] = []
    farm_type: Optional[str] = None
    # partner
    skills: Optional[List[str]] = []
    work_categories: Optional[List[str]] = []
    availability: Optional[str] = None
    languages_spoken: Optional[List[str]] = []


class JobCreate(BaseModel):
    title: str
    description: str
    category_id: str
    crop_type: Optional[str] = None
    work_type: Optional[str] = None
    land_size: Optional[str] = None
    budget_type: Literal["fixed", "daily", "hourly", "milestone", "seasonal"] = "fixed"
    budget_min: Optional[float] = None
    budget_max: Optional[float] = None
    urgency: Optional[Literal["low", "normal", "urgent"]] = "normal"
    start_date: Optional[str] = None
    end_date: Optional[str] = None
    district: Optional[str] = None
    taluk: Optional[str] = None
    village: Optional[str] = None
    lat: Optional[float] = None
    lng: Optional[float] = None
    workers_needed: Optional[int] = 1
    media: Optional[List[str]] = []
    status: Optional[str] = "draft"


class ProposalCreate(BaseModel):
    bid_amount: float
    message: str
    estimated_days: Optional[int] = None
    availability_date: Optional[str] = None


class MilestoneCreate(BaseModel):
    title: str
    description: Optional[str] = None
    amount: float
    due_date: Optional[str] = None


class ReviewCreate(BaseModel):
    reviewee_user_id: str
    contract_id: Optional[str] = None
    rating: int = Field(ge=1, le=5)
    comment: Optional[str] = None


class TicketCreate(BaseModel):
    subject: str
    body: str
    category: Optional[str] = "general"


# ======================================================
# AUTH ROUTES
# ======================================================
@api.route("/auth/signup", methods=["POST"])
@validate_schema(SignupBody)
def auth_signup(body):
    existing = db.users.find_one({"email": body.email.lower()}, {"_id": 0})
    if existing:
        raise BadRequest("Email already registered")
    uid = new_user_id()
    doc = {
        "user_id": uid,
        "email": body.email.lower(),
        "password_hash": hash_password(body.password),
        "full_name": body.full_name,
        "role": None,
        "auth_provider": "email",
        "onboarded": False,
        "preferred_language": "en",
        "created_at": iso(),
    }
    db.users.insert_one(doc)
    doc.pop("_id", None)
    token = create_jwt(uid)
    return jsonify({"token": token, "user": {k: v for k, v in doc.items() if k != "password_hash"}})


@api.route("/auth/login", methods=["POST"])
@validate_schema(LoginBody)
def auth_login(body):
    user = db.users.find_one({"email": body.email.lower()}, {"_id": 0})
    if not user or not user.get("password_hash"):
        raise Unauthorized("Invalid email or password")
    if not verify_password(body.password, user["password_hash"]):
        raise Unauthorized("Invalid email or password")
    token = create_jwt(user["user_id"])
    user.pop("password_hash", None)
    return jsonify({"token": token, "user": user})


@api.route("/auth/google/session", methods=["POST"])
@validate_schema(GoogleSessionBody)
def auth_google_session(body):
    data = exchange_google_session(body.session_id)
    email = (data.get("email") or "").lower()
    if not email:
        raise BadRequest("Missing email from provider")

    existing = db.users.find_one({"email": email}, {"_id": 0})
    if existing:
        user_id = existing["user_id"]
        db.users.update_one(
            {"user_id": user_id},
            {"$set": {"name": data.get("name"), "picture": data.get("picture")}},
        )
    else:
        user_id = new_user_id()
        db.users.insert_one({
            "user_id": user_id,
            "email": email,
            "full_name": data.get("name"),
            "picture": data.get("picture"),
            "role": None,
            "auth_provider": "google",
            "onboarded": False,
            "preferred_language": "en",
            "created_at": iso(),
        })

    session_token = data.get("session_token") or f"st_{uuid.uuid4().hex}"
    db.user_sessions.insert_one({
        "user_id": user_id,
        "session_token": session_token,
        "expires_at": datetime.now(timezone.utc) + timedelta(days=7),
        "created_at": datetime.now(timezone.utc),
    })
    
    user = db.users.find_one({"user_id": user_id}, {"_id": 0, "password_hash": 0})
    resp = make_response(jsonify({"user": user, "session_token": session_token}))
    resp.set_cookie(
        key="session_token", value=session_token,
        httponly=True, secure=True, samesite="none", path="/",
        max_age=7 * 24 * 60 * 60,
    )
    return resp


@api.route("/auth/me", methods=["GET"])
@login_required
def auth_me():
    return jsonify(g.current_user)


@api.route("/auth/logout", methods=["POST"])
def auth_logout():
    token = request.cookies.get("session_token")
    if token:
        db.user_sessions.delete_one({"session_token": token})
    resp = make_response(jsonify({"ok": True}))
    resp.delete_cookie("session_token", path="/")
    return resp


@api.route("/auth/role", methods=["PATCH"])
@login_required
@validate_schema(RoleBody)
def set_role(body):
    user = g.current_user
    db.users.update_one({"user_id": user["user_id"]}, {"$set": {"role": body.role}})
    u = db.users.find_one({"user_id": user["user_id"]}, {"_id": 0, "password_hash": 0})
    return jsonify(u)


@api.route("/auth/onboarding", methods=["POST"])
@login_required
@validate_schema(OnboardingBody)
def complete_onboarding(body):
    user = g.current_user
    profile = body.model_dump()
    profile["onboarded"] = True
    profile["updated_at"] = iso()
    db.users.update_one(
        {"user_id": user["user_id"]},
        {"$set": {
            "role": body.role,
            "full_name": body.full_name,
            "phone": body.phone,
            "preferred_language": body.preferred_language or "en",
            "onboarded": True,
        }},
    )
    db.profiles.update_one(
        {"user_id": user["user_id"]},
        {"$set": {**profile, "user_id": user["user_id"]}},
        upsert=True,
    )
    u = db.users.find_one({"user_id": user["user_id"]}, {"_id": 0, "password_hash": 0})
    return jsonify(u)


# ======================================================
# PROFILE ROUTES
# ======================================================
@api.route("/profile/me", methods=["GET"])
@login_required
def profile_me():
    user = g.current_user
    prof = db.profiles.find_one({"user_id": user["user_id"]}, {"_id": 0})
    return jsonify({"user": user, "profile": prof or {}})


@api.route("/profile/me", methods=["PATCH"])
@login_required
def profile_update():
    user = g.current_user
    data = request.get_json() or {}
    data.pop("user_id", None)
    data["updated_at"] = iso()
    db.profiles.update_one(
        {"user_id": user["user_id"]}, {"$set": {**data, "user_id": user["user_id"]}}, upsert=True
    )
    if "full_name" in data or "preferred_language" in data or "phone" in data:
        patch = {k: v for k, v in data.items() if k in ("full_name", "preferred_language", "phone")}
        if patch:
            db.users.update_one({"user_id": user["user_id"]}, {"$set": patch})
    prof = db.profiles.find_one({"user_id": user["user_id"]}, {"_id": 0})
    return jsonify(prof)


@api.route("/profile/<user_id>", methods=["GET"])
def profile_public(user_id):
    u = db.users.find_one(
        {"user_id": user_id}, {"_id": 0, "password_hash": 0, "email": 0}
    )
    if not u:
        raise NotFound("User not found")
    prof = db.profiles.find_one({"user_id": user_id}, {"_id": 0})
    rating = list(db.reviews.aggregate([
        {"$match": {"reviewee_user_id": user_id}},
        {"$group": {"_id": None, "avg": {"$avg": "$rating"}, "count": {"$sum": 1}}},
    ]))
    rating_info = rating[0] if rating else {"avg": 0, "count": 0}
    rating_info.pop("_id", None)
    return jsonify({"user": u, "profile": prof or {}, "rating": rating_info})


# ======================================================
# REFERENCE DATA ROUTES
# ======================================================
@api.route("/locations/districts", methods=["GET"])
def list_districts():
    return jsonify(list(db.districts.find({}, {"_id": 0}).limit(1000)))


@api.route("/locations/taluks", methods=["GET"])
def list_taluks():
    district_id = request.args.get("district_id")
    return jsonify(list(db.taluks.find({"district_id": district_id}, {"_id": 0}).limit(1000)))


@api.route("/locations/villages", methods=["GET"])
def list_villages():
    taluk_id = request.args.get("taluk_id")
    return jsonify(list(db.villages.find({"taluk_id": taluk_id}, {"_id": 0}).limit(1000)))


@api.route("/categories", methods=["GET"])
def list_categories():
    return jsonify(list(db.job_categories.find({}, {"_id": 0}).limit(500)))


@api.route("/crops", methods=["GET"])
def list_crops():
    return jsonify(list(db.crops.find({}, {"_id": 0}).limit(500)))


@api.route("/skills", methods=["GET"])
def list_skills():
    return jsonify(list(db.skills.find({}, {"_id": 0}).limit(500)))


# ======================================================
# JOBS ROUTES
# ======================================================
@api.route("/jobs", methods=["POST"])
@login_required
@validate_schema(JobCreate)
def create_job(body):
    user = g.current_user
    if user.get("role") not in ("farm_owner", "admin"):
        raise Forbidden("Only Farm Owners can post work")
    job_id = new_id("job")
    doc = body.model_dump()
    doc.update({
        "job_id": job_id,
        "owner_user_id": user["user_id"],
        "workers_filled": 0,
        "cash_booking_fee_status": "pending" if doc.get("payment_mode") == "cash" else "not_required",
        "cash_booking_fee_amount": 400.0 if doc.get("payment_mode") == "cash" else 0,
        "created_at": iso(),
        "updated_at": iso(),
    })
    db.jobs.insert_one(doc)
    doc.pop("_id", None)
    return jsonify(doc)


@api.route("/jobs", methods=["GET"])
def list_jobs():
    q = request.args.get("q")
    category_id = request.args.get("category_id")
    district = request.args.get("district")
    status = request.args.get("status", default="published")
    urgency = request.args.get("urgency")
    budget_type = request.args.get("budget_type")
    limit = request.args.get("limit", default=50, type=int)

    f: dict = {}
    if status:
        f["status"] = status
    if category_id:
        f["category_id"] = category_id
    if district:
        f["district"] = district
    if urgency:
        f["urgency"] = urgency
    if budget_type:
        f["budget_type"] = budget_type
    if q:
        f["$or"] = [{"title": {"$regex": q, "$options": "i"}}, {"description": {"$regex": q, "$options": "i"}}]
    jobs = list(db.jobs.find(f, {"_id": 0}).sort("created_at", -1).limit(limit))
    return jsonify(jobs)


@api.route("/jobs/mine", methods=["GET"])
@login_required
def my_jobs():
    user = g.current_user
    jobs = list(db.jobs.find({"owner_user_id": user["user_id"]}, {"_id": 0}).sort("created_at", -1).limit(500))
    return jsonify(jobs)


@api.route("/jobs/nearby", methods=["GET"])
def jobs_nearby():
    district = request.args.get("district")
    limit = request.args.get("limit", default=20, type=int)
    f = {"status": "published"}
    if district:
        f["district"] = district
    jobs = list(db.jobs.find(f, {"_id": 0}).sort("created_at", -1).limit(limit))
    return jsonify(jobs)


@api.route("/jobs/recommended", methods=["GET"])
@login_required
def jobs_recommended():
    user = g.current_user
    prof = db.profiles.find_one({"user_id": user["user_id"]}, {"_id": 0}) or {}
    f = {"status": "published"}
    if prof.get("district"):
        f["district"] = prof["district"]
    jobs = list(db.jobs.find(f, {"_id": 0}).sort("created_at", -1).limit(30))
    return jsonify(jobs)


@api.route("/jobs/<job_id>", methods=["GET"])
def get_job(job_id):
    job = db.jobs.find_one({"job_id": job_id}, {"_id": 0})
    if not job:
        raise NotFound("Job not found")
    owner = db.users.find_one(
        {"user_id": job["owner_user_id"]},
        {"_id": 0, "password_hash": 0, "email": 0},
    )
    prop_count = db.proposals.count_documents({"job_id": job_id})
    return jsonify({"job": job, "owner": owner, "proposal_count": prop_count})


@api.route("/jobs/<job_id>", methods=["PATCH"])
@login_required
def update_job(job_id):
    user = g.current_user
    data = request.get_json() or {}
    job = db.jobs.find_one({"job_id": job_id}, {"_id": 0})
    if not job:
        raise NotFound("Job not found")
    if job["owner_user_id"] != user["user_id"] and user.get("role") != "admin":
        raise Forbidden("Forbidden")
    data.pop("job_id", None)
    data.pop("owner_user_id", None)
    data["updated_at"] = iso()
    db.jobs.update_one({"job_id": job_id}, {"$set": data})
    job = db.jobs.find_one({"job_id": job_id}, {"_id": 0})
    return jsonify(job)


@api.route("/jobs/<job_id>", methods=["DELETE"])
@login_required
def delete_job(job_id):
    user = g.current_user
    job = db.jobs.find_one({"job_id": job_id}, {"_id": 0})
    if not job:
        raise NotFound("Job not found")
    if job["owner_user_id"] != user["user_id"] and user.get("role") != "admin":
        raise Forbidden("Forbidden")
    db.jobs.delete_one({"job_id": job_id})
    return jsonify({"ok": True})


@api.route("/jobs/<job_id>/publish", methods=["POST"])
@login_required
def publish_job(job_id):
    user = g.current_user
    job = db.jobs.find_one({"job_id": job_id}, {"_id": 0})
    if not job:
        raise NotFound("Job not found")
    if job["owner_user_id"] != user["user_id"]:
        raise Forbidden("Forbidden")
    db.jobs.update_one({"job_id": job_id}, {"$set": {"status": "published", "published_at": iso()}})
    return jsonify({"ok": True})


@api.route("/jobs/<job_id>/save", methods=["POST"])
@login_required
def toggle_save_job(job_id):
    user = g.current_user
    existing = db.saved_jobs.find_one({"user_id": user["user_id"], "job_id": job_id})
    if existing:
        db.saved_jobs.delete_one({"user_id": user["user_id"], "job_id": job_id})
        return jsonify({"saved": False})
    db.saved_jobs.insert_one({
        "user_id": user["user_id"], "job_id": job_id, "created_at": iso(),
    })
    return jsonify({"saved": True})


@api.route("/saved/jobs", methods=["GET"])
@login_required
def get_saved_jobs():
    user = g.current_user
    saved = list(db.saved_jobs.find({"user_id": user["user_id"]}, {"_id": 0}).limit(200))
    job_ids = [s["job_id"] for s in saved]
    jobs = list(db.jobs.find({"job_id": {"$in": job_ids}}, {"_id": 0}).limit(200))
    return jsonify(jobs)


# ======================================================
# PROPOSALS ROUTES
# ======================================================
@api.route("/jobs/<job_id>/proposals", methods=["POST"])
@login_required
@validate_schema(ProposalCreate)
def submit_proposal(body, job_id):
    user = g.current_user
    if user.get("role") != "farm_partner":
        raise Forbidden("Only Farm Partners can propose")
    job = db.jobs.find_one({"job_id": job_id}, {"_id": 0})
    if not job:
        raise NotFound("Job not found")
    existing = db.proposals.find_one({"job_id": job_id, "partner_user_id": user["user_id"]})
    if existing:
        raise BadRequest("Already proposed")
    pid = new_id("prop")
    doc = body.model_dump()
    doc.update({
        "proposal_id": pid, "job_id": job_id,
        "partner_user_id": user["user_id"], "status": "pending",
        "created_at": iso(), "updated_at": iso(),
    })
    db.proposals.insert_one(doc)
    # Notification for owner
    db.notifications.insert_one({
        "notif_id": new_id("notif"), "user_id": job["owner_user_id"],
        "type": "proposal_received", "title": "New proposal received",
        "body": f"{user.get('full_name') or 'A Farm Partner'} proposed on your job",
        "link": f"/owner/jobs/{job_id}", "read": False, "created_at": iso(),
    })
    doc.pop("_id", None)
    return jsonify(doc)


@api.route("/jobs/<job_id>/proposals", methods=["GET"])
@login_required
def list_job_proposals(job_id):
    user = g.current_user
    job = db.jobs.find_one({"job_id": job_id}, {"_id": 0})
    if not job:
        raise NotFound("Job not found")
    if job["owner_user_id"] != user["user_id"] and user.get("role") != "admin":
        raise Forbidden("Forbidden")
    proposals = list(db.proposals.find({"job_id": job_id}, {"_id": 0}).limit(500))
    # Attach partner info
    for p in proposals:
        partner = db.users.find_one(
            {"user_id": p["partner_user_id"]},
            {"_id": 0, "password_hash": 0, "email": 0},
        )
        p["partner"] = partner
    return jsonify(proposals)


@api.route("/proposals/mine", methods=["GET"])
@login_required
def my_proposals():
    user = g.current_user
    props = list(db.proposals.find({"partner_user_id": user["user_id"]}, {"_id": 0}).sort("created_at", -1).limit(500))
    for p in props:
        p["job"] = db.jobs.find_one({"job_id": p["job_id"]}, {"_id": 0})
    return jsonify(props)


@api.route("/proposals/<proposal_id>/accept", methods=["POST"])
@login_required
def accept_proposal(proposal_id):
    user = g.current_user
    prop = db.proposals.find_one({"proposal_id": proposal_id}, {"_id": 0})
    if not prop:
        raise NotFound("Proposal not found")
    job = db.jobs.find_one({"job_id": prop["job_id"]}, {"_id": 0})
    if job["owner_user_id"] != user["user_id"]:
        raise Forbidden("Forbidden")
    db.proposals.update_one({"proposal_id": proposal_id}, {"$set": {"status": "accepted", "updated_at": iso()}})
    # Create contract
    contract_id = new_id("contract")
    contract = {
        "contract_id": contract_id,
        "job_id": prop["job_id"],
        "owner_user_id": user["user_id"],
        "partner_user_id": prop["partner_user_id"],
        "agreed_amount": prop["bid_amount"],
        "payment_model": job.get("budget_type", "fixed"),
        "start_date": prop.get("availability_date"),
        "status": "active",
        "created_at": iso(),
    }
    db.contracts.insert_one(contract)
    db.jobs.update_one({"job_id": prop["job_id"]}, {"$set": {"status": "in_progress"}})
    db.notifications.insert_one({
        "notif_id": new_id("notif"), "user_id": prop["partner_user_id"],
        "type": "proposal_accepted", "title": "Your proposal was accepted!",
        "body": f"You've been hired for '{job.get('title')}'",
        "link": f"/partner/contracts/{contract_id}", "read": False, "created_at": iso(),
    })
    contract.pop("_id", None)
    return jsonify(contract)


@api.route("/proposals/<proposal_id>/reject", methods=["POST"])
@login_required
def reject_proposal(proposal_id):
    user = g.current_user
    prop = db.proposals.find_one({"proposal_id": proposal_id}, {"_id": 0})
    if not prop:
        raise NotFound("Proposal not found")
    job = db.jobs.find_one({"job_id": prop["job_id"]}, {"_id": 0})
    if job["owner_user_id"] != user["user_id"]:
        raise Forbidden("Forbidden")
    db.proposals.update_one({"proposal_id": proposal_id}, {"$set": {"status": "rejected"}})
    return jsonify({"ok": True})


@api.route("/proposals/<proposal_id>/withdraw", methods=["POST"])
@login_required
def withdraw_proposal(proposal_id):
    user = g.current_user
    prop = db.proposals.find_one({"proposal_id": proposal_id}, {"_id": 0})
    if not prop:
        raise NotFound("Proposal not found")
    if prop["partner_user_id"] != user["user_id"]:
        raise Forbidden("Forbidden")
    db.proposals.update_one({"proposal_id": proposal_id}, {"$set": {"status": "withdrawn"}})
    return jsonify({"ok": True})


# ======================================================
# CONTRACTS ROUTES
# ======================================================
@api.route("/contracts", methods=["GET"])
@login_required
def list_contracts():
    user = g.current_user
    f = {"$or": [{"owner_user_id": user["user_id"]}, {"partner_user_id": user["user_id"]}]}
    contracts = list(db.contracts.find(f, {"_id": 0}).sort("created_at", -1).limit(500))
    for c in contracts:
        c["job"] = db.jobs.find_one({"job_id": c["job_id"]}, {"_id": 0})
        c["owner"] = db.users.find_one(
            {"user_id": c["owner_user_id"]}, {"_id": 0, "password_hash": 0, "email": 0}
        )
        c["partner"] = db.users.find_one(
            {"user_id": c["partner_user_id"]}, {"_id": 0, "password_hash": 0, "email": 0}
        )
    return jsonify(contracts)


@api.route("/contracts/<contract_id>", methods=["GET"])
@login_required
def get_contract(contract_id):
    user = g.current_user
    c = db.contracts.find_one({"contract_id": contract_id}, {"_id": 0})
    if not c:
        raise NotFound("Contract not found")
    if user["user_id"] not in (c["owner_user_id"], c["partner_user_id"]) and user.get("role") != "admin":
        raise Forbidden("Forbidden")
    c["job"] = db.jobs.find_one({"job_id": c["job_id"]}, {"_id": 0})
    c["milestones"] = list(db.milestones.find({"contract_id": contract_id}, {"_id": 0}).limit(100))
    return jsonify(c)


@api.route("/contracts/<contract_id>/milestones", methods=["POST"])
@login_required
@validate_schema(MilestoneCreate)
def add_milestone(body, contract_id):
    user = g.current_user
    c = db.contracts.find_one({"contract_id": contract_id}, {"_id": 0})
    if not c or c["owner_user_id"] != user["user_id"]:
        raise Forbidden("Forbidden")
    mid = new_id("ms")
    doc = body.model_dump()
    doc.update({"milestone_id": mid, "contract_id": contract_id, "status": "pending", "created_at": iso()})
    db.milestones.insert_one(doc)
    doc.pop("_id", None)
    return jsonify(doc)


@api.route("/milestones/<milestone_id>/fund", methods=["POST"])
@login_required
def fund_milestone(milestone_id):
    user = g.current_user
    ms = db.milestones.find_one({"milestone_id": milestone_id}, {"_id": 0})
    if not ms:
        raise NotFound("Not found")
    contract = db.contracts.find_one({"contract_id": ms["contract_id"]}, {"_id": 0})
    if not contract or contract["owner_user_id"] != user["user_id"]:
        raise Forbidden("Only the Farm Owner can fund milestones")
    
    order_id = f"order_{uuid.uuid4().hex[:14]}"
    payment_id = f"pay_{uuid.uuid4().hex[:14]}"
    db.milestones.update_one({"milestone_id": milestone_id}, {"$set": {"status": "funded", "funded_at": iso()}})
    db.payments.insert_one({
        "payment_id": new_id("pmt"),
        "milestone_id": milestone_id,
        "contract_id": ms["contract_id"],
        "payer_user_id": user["user_id"],
        "razorpay_order_id": order_id,
        "razorpay_payment_id": payment_id,
        "amount": ms["amount"],
        "currency": "INR",
        "fee_amount": round(ms["amount"] * 0.02, 2),
        "payment_status": "captured",
        "payment_type": "milestone_fund",
        "created_at": iso(),
    })
    return jsonify({"ok": True, "order_id": order_id, "payment_id": payment_id})


@api.route("/milestones/<milestone_id>/approve", methods=["POST"])
@login_required
def approve_milestone(milestone_id):
    user = g.current_user
    ms = db.milestones.find_one({"milestone_id": milestone_id}, {"_id": 0})
    if not ms:
        raise NotFound("Not found")
    contract = db.contracts.find_one({"contract_id": ms["contract_id"]}, {"_id": 0})
    if not contract or user["user_id"] not in (contract["owner_user_id"], contract["partner_user_id"]):
        raise Forbidden("Forbidden")
    db.milestones.update_one({"milestone_id": milestone_id}, {"$set": {"status": "approved", "approved_at": iso()}})
    return jsonify({"ok": True})


@api.route("/milestones/<milestone_id>/release", methods=["POST"])
@login_required
def release_milestone(milestone_id):
    user = g.current_user
    ms = db.milestones.find_one({"milestone_id": milestone_id}, {"_id": 0})
    if not ms:
        raise NotFound("Not found")
    c = db.contracts.find_one({"contract_id": ms["contract_id"]}, {"_id": 0})
    if not c or c["owner_user_id"] != user["user_id"]:
        raise Forbidden("Only the Farm Owner can release payment")
    db.milestones.update_one({"milestone_id": milestone_id}, {"$set": {"status": "released", "released_at": iso()}})
    db.payments.insert_one({
        "payment_id": new_id("pmt"), "milestone_id": milestone_id,
        "contract_id": ms["contract_id"],
        "payer_user_id": c["owner_user_id"], "payee_user_id": c["partner_user_id"],
        "amount": ms["amount"], "currency": "INR",
        "payment_status": "paid", "payment_type": "milestone_release",
        "created_at": iso(),
    })
    return jsonify({"ok": True})


# ======================================================
# PAYMENTS ROUTES
# ======================================================
@api.route("/payments/create-order", methods=["POST"])
@login_required
def create_order():
    data = request.get_json() or {}
    amount = data.get("amount", 0)
    return jsonify({
        "order_id": f"order_{uuid.uuid4().hex[:14]}",
        "amount": amount,
        "currency": "INR",
        "key_id_placeholder": "RAZORPAY_KEY_ID (set in backend/.env)",
        "mock": True,
    })


@api.route("/payments/history", methods=["GET"])
@login_required
def payment_history():
    user = g.current_user
    f = {"$or": [{"payer_user_id": user["user_id"]}, {"payee_user_id": user["user_id"]}]}
    items = list(db.payments.find(f, {"_id": 0}).sort("created_at", -1).limit(500))
    return jsonify(items)


# ======================================================
# CHATS ROUTES
# ======================================================
@api.route("/chats", methods=["GET"])
@login_required
def list_chats():
    user = g.current_user
    threads = list(db.chat_threads.find(
        {"participants": user["user_id"]}, {"_id": 0}
    ).sort("updated_at", -1).limit(200))
    for t in threads:
        other = [p for p in t["participants"] if p != user["user_id"]]
        t["other_user"] = None
        if other:
            t["other_user"] = db.users.find_one(
                {"user_id": other[0]}, {"_id": 0, "password_hash": 0, "email": 0}
            )
        t["job"] = db.jobs.find_one({"job_id": t.get("job_id")}, {"_id": 0})
    return jsonify(threads)


@api.route("/chats", methods=["POST"])
@login_required
def open_chat():
    user = g.current_user
    data = request.get_json() or {}
    other_id = data.get("other_user_id")
    job_id = data.get("job_id")
    if not other_id:
        raise BadRequest("other_user_id required")
    participants = sorted([user["user_id"], other_id])
    thread = db.chat_threads.find_one(
        {"participants": participants, "job_id": job_id}, {"_id": 0}
    )
    if thread:
        return jsonify(thread)
    tid = new_id("thread")
    thread = {
        "thread_id": tid, "participants": participants,
        "job_id": job_id, "created_at": iso(), "updated_at": iso(),
    }
    db.chat_threads.insert_one(thread)
    thread.pop("_id", None)
    return jsonify(thread)


@api.route("/chats/<thread_id>/messages", methods=["GET"])
@login_required
def get_messages(thread_id):
    user = g.current_user
    thread = db.chat_threads.find_one({"thread_id": thread_id}, {"_id": 0})
    if not thread or user["user_id"] not in thread["participants"]:
        raise Forbidden("Forbidden")
    msgs = list(db.messages.find({"thread_id": thread_id}, {"_id": 0}).sort("created_at", 1).limit(1000))
    return jsonify(msgs)


@api.route("/chats/<thread_id>/messages", methods=["POST"])
@login_required
def send_message(thread_id):
    user = g.current_user
    data = request.get_json() or {}
    thread = db.chat_threads.find_one({"thread_id": thread_id}, {"_id": 0})
    if not thread or user["user_id"] not in thread["participants"]:
        raise Forbidden("Forbidden")
    msg = {
        "message_id": new_id("msg"), "thread_id": thread_id,
        "sender_user_id": user["user_id"],
        "text": data.get("text", ""), "kind": data.get("kind", "text"),
        "attachments": data.get("attachments", []),
        "created_at": iso(),
    }
    db.messages.insert_one(msg)
    db.chat_threads.update_one(
        {"thread_id": thread_id},
        {"$set": {"updated_at": iso(), "last_message": msg["text"][:200]}},
    )
    msg.pop("_id", None)
    return jsonify(msg)


# ======================================================
# REVIEWS ROUTES
# ======================================================
@api.route("/reviews", methods=["POST"])
@login_required
@validate_schema(ReviewCreate)
def create_review(body):
    user = g.current_user
    rid = new_id("review")
    doc = body.model_dump()
    doc.update({
        "review_id": rid, "reviewer_user_id": user["user_id"],
        "created_at": iso(),
    })
    db.reviews.insert_one(doc)
    doc.pop("_id", None)
    return jsonify(doc)


@api.route("/reviews/<user_id>", methods=["GET"])
def list_reviews(user_id):
    items = list(db.reviews.find({"reviewee_user_id": user_id}, {"_id": 0}).sort("created_at", -1).limit(200))
    for r in items:
        r["reviewer"] = db.users.find_one(
            {"user_id": r["reviewer_user_id"]},
            {"_id": 0, "password_hash": 0, "email": 0},
        )
    return jsonify(items)


# ======================================================
# NOTIFICATIONS ROUTES
# ======================================================
@api.route("/notifications", methods=["GET"])
@login_required
def list_notifications():
    user = g.current_user
    items = list(db.notifications.find({"user_id": user["user_id"]}, {"_id": 0}).sort("created_at", -1).limit(100))
    return jsonify(items)


@api.route("/notifications/<notif_id>/read", methods=["PATCH"])
@login_required
def mark_read(notif_id):
    user = g.current_user
    db.notifications.update_one(
        {"notif_id": notif_id, "user_id": user["user_id"]}, {"$set": {"read": True}}
    )
    return jsonify({"ok": True})


@api.route("/notifications/mark-all-read", methods=["POST"])
@login_required
def mark_all_read():
    user = g.current_user
    db.notifications.update_many({"user_id": user["user_id"]}, {"$set": {"read": True}})
    return jsonify({"ok": True})


# ======================================================
# SUPPORT ROUTES
# ======================================================
@api.route("/support/tickets", methods=["POST"])
@login_required
@validate_schema(TicketCreate)
def create_ticket(body):
    user = g.current_user
    tid = new_id("ticket")
    doc = body.model_dump()
    doc.update({
        "ticket_id": tid, "user_id": user["user_id"],
        "status": "open", "created_at": iso(),
    })
    db.support_tickets.insert_one(doc)
    doc.pop("_id", None)
    return jsonify(doc)


@api.route("/support/tickets/mine", methods=["GET"])
@login_required
def my_tickets():
    user = g.current_user
    items = list(db.support_tickets.find({"user_id": user["user_id"]}, {"_id": 0}).sort("created_at", -1).limit(200))
    return jsonify(items)


# ======================================================
# MAPS ROUTES (mock)
# ======================================================
@api.route("/maps/autocomplete", methods=["GET"])
def maps_autocomplete():
    q = request.args.get("q", default="")
    q_lower = q.lower()
    districts = list(db.districts.find({}, {"_id": 0}).limit(100))
    villages = list(db.villages.find({}, {"_id": 0}).limit(200))
    results = []
    for d in districts:
        if q_lower in d["name"].lower():
            results.append({"label": d["name"] + ", Karnataka", "type": "district", "id": d["district_id"]})
    for v in villages:
        if q_lower in v["name"].lower():
            results.append({"label": f"{v['name']} (village), Karnataka", "type": "village", "id": v["village_id"]})
    return jsonify(results[:10])


@api.route("/maps/nearby-jobs", methods=["GET"])
def maps_nearby():
    lat = request.args.get("lat", default=12.9716, type=float)
    lng = request.args.get("lng", default=77.5946, type=float)
    radius = request.args.get("radius", default=50, type=float)
    jobs = list(db.jobs.find({"status": "published"}, {"_id": 0}).limit(100))
    # Attach mock lat/lng if missing
    for j in jobs:
        if not j.get("lat"):
            j["lat"] = lat + random.uniform(-0.3, 0.3)
            j["lng"] = lng + random.uniform(-0.3, 0.3)
    return jsonify(jobs)


# ======================================================
# ADMIN ROUTES
# ======================================================
@api.route("/admin/overview", methods=["GET"])
@admin_required
def admin_overview():
    total_users = db.users.count_documents({})
    owners = db.users.count_documents({"role": "farm_owner"})
    partners = db.users.count_documents({"role": "farm_partner"})
    jobs = db.jobs.count_documents({})
    active_contracts = db.contracts.count_documents({"status": "active"})
    payments = list(db.payments.aggregate([
        {"$group": {"_id": None, "total": {"$sum": "$amount"}, "count": {"$sum": 1}}}
    ]))
    gmv = payments[0]["total"] if payments else 0
    
    try:
        pending_disputes = db.disputes.count_documents({"status": "open"})
    except Exception:
        pending_disputes = 0
        
    try:
        verifications_pending = db.user_verifications.count_documents({"status": "pending"})
    except Exception:
        verifications_pending = 0

    return jsonify({
        "total_users": total_users, "farm_owners": owners, "farm_partners": partners,
        "total_jobs": jobs, "active_contracts": active_contracts, "gmv": gmv,
        "pending_disputes": pending_disputes,
        "verifications_pending": verifications_pending,
    })


@api.route("/admin/users", methods=["GET"])
@admin_required
def admin_users():
    limit = request.args.get("limit", default=100, type=int)
    users = list(db.users.find({}, {"_id": 0, "password_hash": 0}).sort("created_at", -1).limit(limit))
    return jsonify(users)


@api.route("/admin/jobs", methods=["GET"])
@admin_required
def admin_jobs():
    limit = request.args.get("limit", default=100, type=int)
    jobs = list(db.jobs.find({}, {"_id": 0}).sort("created_at", -1).limit(limit))
    return jsonify(jobs)


@api.route("/admin/payments", methods=["GET"])
@admin_required
def admin_payments():
    limit = request.args.get("limit", default=100, type=int)
    items = list(db.payments.find({}, {"_id": 0}).sort("created_at", -1).limit(limit))
    return jsonify(items)


@api.route("/admin/analytics", methods=["GET"])
@admin_required
def admin_analytics():
    pipeline = [
        {"$group": {"_id": "$category_id", "count": {"$sum": 1}}},
        {"$sort": {"count": -1}},
        {"$limit": 10},
    ]
    cats = list(db.jobs.aggregate(pipeline))
    for c in cats:
        c["category_id"] = c.pop("_id")
    
    dist_pipeline = [
        {"$group": {"_id": "$district", "count": {"$sum": 1}}},
        {"$sort": {"count": -1}},
        {"$limit": 10},
    ]
    districts = list(db.jobs.aggregate(dist_pipeline))
    for d in districts:
        d["district"] = d.pop("_id")
    return jsonify({"categories": cats, "districts": districts})


# ======================================================
# Root / Health
# ======================================================
@api.route("/", methods=["GET"])
def root_api():
    return jsonify({"service": "Go Farm Work API", "status": "ok"})


@api.route("/health", methods=["GET"])
def health():
    return jsonify({"ok": True, "ts": iso()})


# Register Blueprints
app.register_blueprint(api)
app.register_blueprint(make_v2_router(db))
app.register_blueprint(make_v3_router(db))


# Run seed
try:
    seed_database(db)
    logger.info("Seed complete")
except Exception as e:
    logger.error(f"Seed failed: {e}")


# ======================================================
# FRONTEND STATIC FILES SERVING (React SPA)
# ======================================================
FRONTEND_DIR = Path(__file__).resolve().parent.parent / "frontend" / "build"

@app.route("/", defaults={"path_name": ""})
@app.route("/<path:path_name>")
def serve_frontend(path_name):
    # Exclude API endpoints just in case
    if path_name.startswith("api"):
        raise NotFound()
        
    if FRONTEND_DIR.exists():
        file_path = FRONTEND_DIR / path_name
        if file_path.is_file():
            from flask import send_from_directory
            return send_from_directory(str(FRONTEND_DIR), path_name)
        from flask import send_file
        return send_file(str(FRONTEND_DIR / "index.html"))
    else:
        logger.warning(f"Frontend build folder not found at {FRONTEND_DIR}. Frontend serving disabled.")
        return jsonify({"detail": "Frontend build not found"}), 404


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8000, debug=True)
