import os
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, EmailStr
from typing import List, Optional
from database import db, create_document, get_documents
from schemas import User, Course, Scheduleentry, Announcement
from pymongo.errors import DuplicateKeyError
from bson import ObjectId
import hashlib

app = FastAPI(title="Student Schedule Organizer API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Utility

def hash_password(password: str) -> str:
    return hashlib.sha256(password.encode("utf-8")).hexdigest()


# Ensure indexes for quick lookups and uniqueness
if db is not None:
    try:
        db["user"].create_index("email", unique=True)
        db["course"].create_index([("owner_email", 1)])
        db["scheduleentry"].create_index([("owner_email", 1), ("day", 1)])
    except Exception:
        pass


# Auth-like simple endpoints (no sessions, demo-level)
class RegisterPayload(BaseModel):
    name: str
    email: EmailStr
    password: str
    major: Optional[str] = None
    year: Optional[str] = None


@app.post("/api/register")
def register_user(payload: RegisterPayload):
    if db is None:
        raise HTTPException(status_code=503, detail="Database not available")

    user = User(
        name=payload.name,
        email=payload.email,
        password_hash=hash_password(payload.password),
        major=payload.major,
        year=payload.year,
    )

    try:
        user_id = create_document("user", user)
        return {"message": "Registered", "id": user_id}
    except DuplicateKeyError:
        raise HTTPException(status_code=400, detail="Email already registered")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


class LoginPayload(BaseModel):
    email: EmailStr
    password: str


@app.post("/api/login")
def login(payload: LoginPayload):
    if db is None:
        raise HTTPException(status_code=503, detail="Database not available")

    user = db["user"].find_one({"email": payload.email})
    if not user:
        raise HTTPException(status_code=401, detail="Invalid credentials")
    if user.get("password_hash") != hash_password(payload.password):
        raise HTTPException(status_code=401, detail="Invalid credentials")

    # Demo token (not secure): sha256(email)
    token = hash_password(payload.email)[:32]
    return {
        "message": "Logged in",
        "token": token,
        "profile": {
            "name": user.get("name"),
            "email": user.get("email"),
            "major": user.get("major"),
            "year": user.get("year"),
            "avatar": user.get("avatar"),
        },
    }


# Profile
class UpdateProfile(BaseModel):
    name: Optional[str] = None
    major: Optional[str] = None
    year: Optional[str] = None
    avatar: Optional[str] = None


@app.put("/api/profile/{email}")
def update_profile(email: str, payload: UpdateProfile):
    if db is None:
        raise HTTPException(status_code=503, detail="Database not available")

    update_data = {k: v for k, v in payload.model_dump().items() if v is not None}
    db["user"].update_one({"email": email}, {"$set": update_data})
    user = db["user"].find_one({"email": email}, {"password_hash": 0})
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    user["_id"] = str(user["_id"])  # jsonify
    return user


# Courses
class CoursePayload(BaseModel):
    code: str
    title: str
    instructor: Optional[str] = None
    credits: Optional[int] = None
    owner_email: EmailStr


@app.post("/api/courses")
def create_course(payload: CoursePayload):
    try:
        cid = create_document("course", payload.model_dump())
        return {"id": cid}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/courses/{owner_email}")
def list_courses(owner_email: str):
    try:
        items = get_documents("course", {"owner_email": owner_email})
        for it in items:
            it["_id"] = str(it["_id"])  # jsonify
        return items
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# Schedule entries
class SchedulePayload(BaseModel):
    owner_email: EmailStr
    title: str
    day: str
    start_time: str
    end_time: str
    location: Optional[str] = None
    notes: Optional[str] = None
    color: Optional[str] = None


@app.post("/api/schedule")
def add_schedule_entry(payload: SchedulePayload):
    try:
        sid = create_document("scheduleentry", payload.model_dump())
        return {"id": sid}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/schedule/{owner_email}")
def get_schedule(owner_email: str):
    try:
        items = get_documents("scheduleentry", {"owner_email": owner_email})
        for it in items:
            it["_id"] = str(it["_id"])  # jsonify
        return items
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# Announcements (public)
@app.get("/api/announcements")
def get_announcements():
    try:
        items = get_documents("announcement", {"visible": True}, limit=5)
        for it in items:
            it["_id"] = str(it["_id"])  # jsonify
        return items
    except Exception as e:
        # fallback demo announcements if db not available
        return [
            {"title": "Welcome to Campus Scheduler", "body": "Plan classes, labs, study sessions in one place."},
            {"title": "Tip", "body": "Drag across the grid to create a block of study time."},
        ]


@app.get("/")
def read_root():
    return {"message": "Student Schedule Organizer API"}


@app.get("/test")
def test_database():
    response = {
        "backend": "✅ Running",
        "database": "❌ Not Available",
        "database_url": None,
        "database_name": None,
        "connection_status": "Not Connected",
        "collections": [],
    }

    try:
        if db is not None:
            response["database"] = "✅ Available"
            response["database_url"] = "✅ Set" if os.getenv("DATABASE_URL") else "❌ Not Set"
            response["database_name"] = "✅ Set" if os.getenv("DATABASE_NAME") else "❌ Not Set"
            response["connection_status"] = "Connected"
            try:
                collections = db.list_collection_names()
                response["collections"] = collections[:10]
                response["database"] = "✅ Connected & Working"
            except Exception as e:
                response["database"] = f"⚠️  Connected but Error: {str(e)[:50]}"
        else:
            response["database"] = "⚠️  Available but not initialized"
    except Exception as e:
        response["database"] = f"❌ Error: {str(e)[:50]}"

    return response


if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)
