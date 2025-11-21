"""
Database Schemas for Student Schedule Organizer

Each Pydantic model represents a collection in MongoDB.
The collection name is the lowercase class name.

Example: class User -> "user" collection
"""

from pydantic import BaseModel, Field, EmailStr
from typing import Optional, List


class User(BaseModel):
    """Students collection schema -> collection: "user"""
    name: str = Field(..., min_length=2, max_length=80)
    email: EmailStr
    password_hash: str = Field(..., description="SHA256 hash of the password")
    major: Optional[str] = Field(None, max_length=80)
    year: Optional[str] = Field(None, description="e.g., Freshman, Sophomore")
    avatar: Optional[str] = Field(None, description="Avatar URL")


class Course(BaseModel):
    """Courses collection schema -> collection: "course"""
    code: str = Field(..., description="e.g., MATH101")
    title: str
    instructor: Optional[str] = None
    credits: Optional[int] = Field(None, ge=0, le=10)
    owner_email: EmailStr = Field(..., description="Owner user's email")


class Scheduleentry(BaseModel):
    """Schedule entries schema -> collection: "scheduleentry"""
    owner_email: EmailStr = Field(..., description="Owner user's email")
    title: str = Field(..., description="Class/Lab/Study Session title")
    day: str = Field(..., description="Mon, Tue, Wed, Thu, Fri, Sat, Sun")
    start_time: str = Field(..., description="24h format HH:MM")
    end_time: str = Field(..., description="24h format HH:MM")
    location: Optional[str] = None
    notes: Optional[str] = None
    color: Optional[str] = Field(None, description="Hex color for calendar UI")


class Announcement(BaseModel):
    """Announcements collection -> collection: "announcement"""
    title: str
    body: str
    visible: bool = True
