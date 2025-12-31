from sqlalchemy.orm import Session
from sqlalchemy import func, LargeBinary
import json
import numpy as np
from datetime import datetime
from dateutil import parser  # For robust ISO parsing (install if needed: pip install python-dateutil)
from app import models, schemas
from app.auth import encrypt_data, decrypt_data, get_password_hash  # Import encryption

# User CRUD
def create_user(db: Session, user: schemas.UserCreate):
    hashed_password = get_password_hash(user.password)
    db_user = models.User(
        username=user.username,
        hashed_password=hashed_password,
        role=user.role,
        is_active=True
    )
    db.add(db_user)
    db.commit()
    db.refresh(db_user)
    return db_user

def get_user_by_username(db: Session, username: str):
    return db.query(models.User).filter(models.User.username == username).first()

# Person CRUD
def create_person(db: Session, person_data: schemas.PersonCreate, embedding: np.ndarray, owner_id: int = 1):
    name_encrypted = encrypt_data(person_data.name)
    contact_encrypted = encrypt_data(person_data.contact) if person_data.contact else None
    embedding_json = json.dumps(embedding.tolist())

    # Parse expiry str to datetime (assumes ISO format; use parser for flexibility)
    expiry_dt = None
    if person_data.expiry:
        try:
            expiry_dt = datetime.fromisoformat(person_data.expiry.replace('Z', '+00:00'))  # Handle UTC 'Z'
        except ValueError:
            expiry_dt = parser.parse(person_data.expiry)  # Fallback

    db_person = models.Person(
        name_encrypted=name_encrypted,
        contact_encrypted=contact_encrypted,
        category=person_data.category,
        expiry=expiry_dt,
        embedding=embedding_json,
        owner_id=1  # Default to admin user ID 1; customize based on current_user
    )
    db.add(db_person)
    db.commit()
    db.refresh(db_person)
    return db_person

def get_person(db: Session, person_id: int):
    person = db.query(models.Person).filter(models.Person.id == person_id).first()
    if not person:
        return None
    # Decrypt PII (mutate object for response use)
    person.name = decrypt_data(person.name_encrypted).decode('utf-8')
    person.contact = decrypt_data(person.contact_encrypted).decode('utf-8') if person.contact_encrypted else None
    return person

def get_persons(db: Session, skip: int = 0, limit: int = 100):
    persons = db.query(models.Person).offset(skip).limit(limit).all()
    # Decrypt for each (inefficient for large lists; optimize later with separate schema)
    for p in persons:
        p.name = decrypt_data(p.name_encrypted).decode('utf-8')
        p.contact = decrypt_data(p.contact_encrypted).decode('utf-8') if p.contact_encrypted else None
    return persons

def is_person_expired(db: Session, person_id: int) -> bool:
    person = db.query(models.Person).filter(models.Person.id == person_id).first()
    if not person or not person.expiry:
        return False
    return person.expiry < datetime.utcnow()

def get_all_embeddings(db: Session) -> list:
    persons = db.query(models.Person).all()
    emb_data = []
    for p in persons:
        emb_json = p.embedding
        if emb_json:
            emb = np.array(json.loads(emb_json))
            emb_data.append({'embedding': emb, 'id': p.id})
    return emb_data

# Camera CRUD
def create_camera(db: Session, camera: schemas.CameraCreate):
    db_camera = models.Camera(**camera.dict())
    db.add(db_camera)
    db.commit()
    db.refresh(db_camera)
    return db_camera

def get_cameras(db: Session, skip: int = 0, limit: int = 100):
    return db.query(models.Camera).offset(skip).limit(limit).all()

# Event CRUD
def create_event(db: Session, event: schemas.EventCreate):
    db_event = models.Event(**event.dict())
    db.add(db_event)
    db.commit()
    db.refresh(db_event)
    return db_event

def get_events(db: Session, skip: int = 0, limit: int = 100):
    return db.query(models.Event).offset(skip).limit(limit).all()