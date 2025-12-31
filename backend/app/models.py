from sqlalchemy import Boolean, Column, Integer, String, DateTime, ForeignKey, Text, LargeBinary, Float
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from .database import Base

class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    username = Column(String, unique=True, index=True)
    hashed_password = Column(String)
    is_active = Column(Boolean, default=True)
    role = Column(String, default="user")  # e.g., "admin", "user"
    created_at = Column(DateTime, default=func.now())

    # Relationship to persons (one user can own many persons)
    persons = relationship("Person", back_populates="owner")

class Person(Base):
    __tablename__ = "persons"

    id = Column(Integer, primary_key=True, index=True)
    name_encrypted = Column(LargeBinary, nullable=False)  # Encrypted name
    contact_encrypted = Column(LargeBinary, nullable=True)  # Encrypted contact
    category = Column(String, nullable=True)
    expiry = Column(DateTime, nullable=True)
    embedding = Column(Text, nullable=True)  # JSON-serialized 512D vector
    owner_id = Column(Integer, ForeignKey("users.id"), nullable=True)  # Allow nullable for flexibility
    created_at = Column(DateTime, default=func.now())

    # Relationships (FIXED: Removed trailing space in "User ")
    owner = relationship("User", back_populates="persons")
    events = relationship("Event", back_populates="person")

class Camera(Base):
    __tablename__ = "cameras"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, index=True)
    rtsp_url = Column(String, unique=True)  # Changed from ip_address to match usage
    location = Column(String)
    created_at = Column(DateTime, default=func.now())

    # Relationship to events (one camera can have many events)
    events = relationship("Event", back_populates="camera")

class Event(Base):
    __tablename__ = "events"

    id = Column(Integer, primary_key=True, index=True)
    person_id = Column(Integer, ForeignKey("persons.id"), nullable=True)
    camera_id = Column(Integer, ForeignKey("cameras.id"), nullable=False)
    category = Column(String, nullable=True)  # e.g., "Recognition", "Unknown"
    timestamp = Column(DateTime, default=func.now())
    confidence = Column(Float, nullable=True)  # Float for similarity score
    image_path = Column(String, nullable=True)  # Path to saved detection image

    # Relationships
    person = relationship("Person", back_populates="events")
    camera = relationship("Camera", back_populates="events")