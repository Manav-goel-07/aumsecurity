from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime

# User Schemas
class UserCreate(BaseModel):
    username: str
    password: str
    role: str = "viewer"

class User(BaseModel):
    id: int
    username: str
    role: str
    is_active: bool

    class Config:
        from_attributes = True

# Person Schemas
class PersonCreate(BaseModel):
    name: str
    category: str
    expiry: Optional[datetime] = None
    contact: Optional[str] = None
    image_base64: Optional[str] = ""  # Optional, not used

class Person(BaseModel):
    id: int
    name: str  # Decrypted
    category: str
    expiry: Optional[datetime] = None
    contact: Optional[str] = None  # Decrypted
    created_at: Optional[datetime] = None

    class Config:
        from_attributes = True

# Camera Schemas
class CameraCreate(BaseModel):
    name: str
    rtsp_url: str

class Camera(BaseModel):
    id: int
    name: str
    rtsp_url: str
    created_at: Optional[datetime] = None

    class Config:
        from_attributes = True

# Event Schemas
class EventCreate(BaseModel):
    camera_id: int
    category: str
    similarity: Optional[float] = None
    snapshot_key: Optional[str] = None
    person_id: Optional[int] = None

class Event(BaseModel):
    id: int
    camera_id: int
    category: str
    similarity: Optional[float] = None
    snapshot_key: Optional[str] = None
    person_id: Optional[int] = None
    created_at: Optional[datetime] = None

    class Config:
        from_attributes = True