# backend/app/main.py
from fastapi import FastAPI, Depends, HTTPException, File, UploadFile, Form, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session
from typing import Optional, List
import uvicorn
from datetime import datetime, timedelta
import os
import shutil
import requests  # For calling ML service
import numpy as np
from sklearn.metrics.pairwise import cosine_similarity  # For similarity computation (pip install scikit-learn)
import traceback  # For detailed error logging
import json  # For embedding handling

# Correct imports: database for get_db and Base; schemas, crud, auth
from app.database import get_db, Base, engine  # get_db and Base/engine for tables
from app import schemas, crud
from app.auth import (  # All auth utils
    authenticate_user, create_access_token, verify_token, Token, TokenData,
    ACCESS_TOKEN_EXPIRE_MINUTES
)

app = FastAPI(title="AUMSecurity API")

# CORS for frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Create tables on startup (users, persons, cameras, events)
Base.metadata.create_all(bind=engine)

# ML Service URL (ensure ML service is running on port 5001)
ML_SERVICE_URL = "http://localhost:5001/embed"

@app.get("/")
def root():
    return {"message": "AUMSecurity Backend Running! Auth & ML Integrated."}

# Login: Authenticate user → Return JWT token
@app.post("/login", response_model=Token)
def login_for_access_token(
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: Session = Depends(get_db)
):
    user = authenticate_user(db, form_data.username, form_data.password)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"sub": user.username, "role": user.role}, expires_delta=access_token_expires
    )
    return {"access_token": access_token, "token_type": "bearer"}

# Enroll person: Protected with auth (admin only)
@app.post("/enroll", response_model=dict)
def enroll_person(
    name: str = Form(...),
    category: str = Form(...),  # 'Family', 'Temporary', 'Random'
    expiry: Optional[str] = Form(None),
    contact: Optional[str] = Form(None),
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user = Depends(verify_token)  # Returns user object (with role)
):
    try:
        if current_user.role != "admin":
            raise HTTPException(status_code=403, detail="Admin access required")
        
        if not file.content_type or not file.content_type.startswith('image/'):
            raise HTTPException(status_code=400, detail="Invalid image file type")
        
        print("Starting enrollment process...")
        
        # Save uploaded file to uploads/
        os.makedirs("uploads", exist_ok=True)
        file_path = f"uploads/{file.filename or 'unknown.jpg'}"
        with open(file_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
        
        print(f"Image saved to: {file_path}")
        
        # Call ML service for real face embedding
        with open(file_path, 'rb') as f:
            ml_response = requests.post(
                ML_SERVICE_URL,
                files={'image': (file.filename, f, file.content_type)},
                timeout=30
            )
        
        print(f"ML Response Status: {ml_response.status_code}")
        if ml_response.status_code != 200:
            raise HTTPException(status_code=400, detail=f"ML Service Error: {ml_response.text}")
        
        embedding_data = ml_response.json()
        print(f"ML Response Preview: {str(embedding_data)[:200]}...")
        
        if not embedding_data.get('success', False):
            raise HTTPException(status_code=400, detail="No face detected in uploaded image. Use a clear, front-facing photo.")
        
        embedding = np.array(embedding_data['embedding'])
        if embedding.shape != (512,):
            raise HTTPException(status_code=400, detail=f"Invalid embedding shape: expected 512, got {embedding.shape}")
        
        print(f"Enrollment successful: Embedding shape {embedding.shape}, first 5 values: {embedding[:5]}")
        
        # Prepare person data (expiry as string → datetime in crud)
        person_data = schemas.PersonCreate(
            name=name,
            category=category,
            expiry=expiry,  # String like "2024-12-31T00:00:00" or None
            contact=contact,
            image_base64=""  # Not used; ML handles image
        )
        
        # Create person in DB with real embedding and owner_id
        db_person = crud.create_person(db, person_data, embedding, owner_id=current_user.id)
        if not db_person:
            raise HTTPException(status_code=500, detail="Failed to store person in database")
        
        # Get decrypted person for response
        decrypted_person = crud.get_person(db, db_person.id)
        
        return {
            "id": db_person.id,
            "name": decrypted_person.name,
            "category": db_person.category,
            "expiry": db_person.expiry.isoformat() if db_person.expiry else None,
            "contact": decrypted_person.contact,
            "message": "Enrolled successfully with real face embedding!",
            "file_saved": file_path,
            "embedding_shape": 512
        }
    
    except requests.exceptions.RequestException as e:
        print(f"ML Service Connection Error: {str(e)}")
        raise HTTPException(status_code=500, detail=f"ML Service unavailable: {str(e)}")
    except (ValueError, KeyError) as e:
        print(f"Embedding Extraction Error: {str(e)}")
        raise HTTPException(status_code=400, detail=f"Embedding extraction failed: {str(e)}")
    except Exception as e:
        print(f"Unexpected Enrollment Error: {str(e)}")
        print(f"Full Traceback: {traceback.format_exc()}")
        raise HTTPException(status_code=500, detail=f"Enrollment failed: {str(e)}")

# Recognize face: Protected (admin or viewer)
@app.post("/recognize", response_model=dict)
def recognize_face(
    file: UploadFile = File(...),  # Single image for recognition (simulates camera frame)
    db: Session = Depends(get_db),
    current_user = Depends(verify_token)  # Returns user object
):
    temp_path = None
    try:
        # Role check
        if current_user.role not in ["admin", "viewer"]:
            raise HTTPException(status_code=403, detail="Access denied")
        
        if not file.content_type or not file.content_type.startswith('image/'):
            raise HTTPException(status_code=400, detail="Invalid image file type")
        
        print("Starting recognition process...")
        
        # Temp save for ML processing
        temp_filename = f"temp_recognize_{file.filename or 'unknown.jpg'}"
        os.makedirs("temp", exist_ok=True)
        temp_path = f"temp/{temp_filename}"
        with open(temp_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
        
        print(f"Temp image saved to: {temp_path}")
        
        # Call ML service for query embedding
        with open(temp_path, 'rb') as f:
            ml_response = requests.post(
                ML_SERVICE_URL,
                files={'image': (file.filename, f, file.content_type)},
                timeout=30
            )
        
        print(f"ML Response Status: {ml_response.status_code}")
        if ml_response.status_code != 200:
            raise HTTPException(status_code=400, detail=f"ML Service Error: {ml_response.text}")
        
        embedding_data = ml_response.json()
        print(f"ML Response Preview: {str(embedding_data)[:200]}...")
        
        if not embedding_data.get('success', False):
            return {
                "name": "Unknown",
                "action": "Alert Guard - No Face Detected",
                "confidence": 0.0,
                "contact": None
            }
        
        query_embedding = np.array(embedding_data['embedding']).reshape(1, -1)  # Shape: (1, 512)
        if query_embedding.shape[1] != 512:
            raise HTTPException(status_code=400, detail=f"Invalid query embedding shape: {query_embedding.shape}")
        
        print(f"Recognition query: Embedding shape {query_embedding.shape}, first 5 values: {query_embedding[0][:5]}")
        
        # Get all stored embeddings from DB (list of {'embedding': np.array, 'id': int})
        all_emb_data = crud.get_all_embeddings(db)
        if len(all_emb_data) == 0:
            return {
                "name": "Unknown",
                "action": "Alert Guard - No Enrolled Persons",
                "confidence": 0.0,
                "contact": None
            }
        
        # Extract embeddings for similarity computation
        stored_embeddings = np.array([d['embedding'] for d in all_emb_data])
        similarities = cosine_similarity(query_embedding, stored_embeddings)[0]  # Shape: (N,)
        max_sim_idx = np.argmax(similarities)
        max_confidence = float(similarities[max_sim_idx])
        
        print(f"Max similarity: {max_confidence} (to person ID {all_emb_data[max_sim_idx]['id']})")
        
        # Decision logic based on confidence thresholds (tuned for cross-image matching)
        person_id = all_emb_data[max_sim_idx]['id']
        matched_person = crud.get_person(db, person_id)
        
        if max_confidence > 0.8:  # Strong match (Family or high-confidence Temporary)
            if crud.is_person_expired(db, person_id):
                action = "Renew Access - Expired"
            else:
                action = "Allow Entry" if matched_person.category == "Family" else "Verify Temporary"
            return {
                "name": matched_person.name,
                "action": action,
                "confidence": max_confidence,
                "contact": matched_person.contact
            }
        elif max_confidence > 0.6:  # Medium match (Temporary or partial match)
            action = "Verify Identity - Low Confidence"
            return {
                "name": matched_person.name,
                "action": action,
                "confidence": max_confidence,
                "contact": matched_person.contact
            }
        else:  # No match (Random/Unknown)
            return {
                "name": "Unknown",
                "action": "Alert Guard",
                "confidence": max_confidence,
                "contact": None
            }
    
    except requests.exceptions.RequestException as e:
        print(f"ML Service Connection Error: {str(e)}")
        raise HTTPException(status_code=500, detail=f"ML Service unavailable: {str(e)}")
    except (ValueError, KeyError, np.linalg.LinAlgError) as e:
        print(f"Recognition Processing Error: {str(e)}")
        raise HTTPException(status_code=400, detail=f"Recognition failed: {str(e)}")
    except Exception as e:
        print(f"Unexpected Recognition Error: {str(e)}")
        print(f"Full Traceback: {traceback.format_exc()}")
        raise HTTPException(status_code=500, detail=f"Recognition failed: {str(e)}")
    finally:
        # Cleanup temp file
        if temp_path and os.path.exists(temp_path):
            os.remove(temp_path)
            temp_dir = "temp"
            if os.path.exists(temp_dir) and not os.listdir(temp_dir):
                os.rmdir(temp_dir)

# Get all persons: Protected (admin only for full list; viewers see limited)
@app.get("/persons", response_model=List[dict])
def read_persons(
    skip: int = 0, 
    limit: int = 100, 
    db: Session = Depends(get_db),
    current_user = Depends(verify_token)  # Returns user
):
    try:
        if current_user.role == "viewer":
            limit = min(limit, 10)  # Viewers see limited results
        persons = crud.get_persons(db, skip=skip, limit=limit)
        decrypted_persons = []
        for person in persons:
            decrypted_persons.append({
                "id": person.id,
                "name": person.name,  # Already decrypted in get_persons
                "category": person.category,
                "expiry": person.expiry.isoformat() if person.expiry else None,
                "contact": person.contact,
                "created_at": person.created_at.isoformat() if person.created_at else None
            })
        return decrypted_persons
    except Exception as e:
        print(f"Persons Read Error: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to fetch persons: {str(e)}")

# Create camera: Admin only
@app.post("/cameras", response_model=schemas.Camera)
def create_camera(
    name: str = Form(...),
    rtsp_url: str = Form(...),
    db: Session = Depends(get_db),
    current_user = Depends(verify_token)
):
    try:
        if current_user.role != "admin":
            raise HTTPException(status_code=403, detail="Admin access required")
        camera_data = schemas.CameraCreate(name=name, rtsp_url=rtsp_url)
        return crud.create_camera(db, camera_data)
    except Exception as e:
        print(f"Camera Create Error: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to create camera: {str(e)}")

# Get cameras: Viewer+ access
@app.get("/cameras", response_model=List[schemas.Camera])
def read_cameras(
    skip: int = 0, 
    limit: int = 100, 
    db: Session = Depends(get_db),
    current_user = Depends(verify_token)
):
    try:
        return crud.get_cameras(db, skip=skip, limit=limit)
    except Exception as e:
        print(f"Cameras Read Error: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to fetch cameras: {str(e)}")

# Create event: Admin only (for logging recognition results)
@app.post("/events", response_model=schemas.Event)
def create_event_endpoint(
    camera_id: int = Form(...),
    category: str = Form(...),
    similarity: Optional[float] = Form(None),
    snapshot_key: Optional[str] = Form(None),
    person_id: Optional[int] = Form(None),
    db: Session = Depends(get_db),
    current_user = Depends(verify_token)
):
    try:
        if current_user.role != "admin":
            raise HTTPException(status_code=403, detail="Admin access required")
        event_data = schemas.EventCreate(
            camera_id=camera_id,
            category=category,
            confidence=similarity,  # Maps to Float confidence
            image_path=snapshot_key,  # Maps to image_path
            person_id=person_id
        )
        return crud.create_event(db, event_data)
    except Exception as e:
        print(f"Event Create Error: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to create event: {str(e)}")

# Get events
@app.get("/events", response_model=List[schemas.Event])
def read_events(skip: int = 0, limit: int = 100, db: Session = Depends(get_db), current_user = Depends(verify_token)):
    try:
        return crud.get_events(db, skip=skip, limit=limit)
    except Exception as e:
        print(f"Events Read Error: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to fetch events: {str(e)}")

# Temporary endpoint: Create initial admin user (REMOVE AFTER USE!)
@app.post("/create-admin", response_model=dict)
def create_initial_admin(
    username: str = Form("admin"),  # Default for ease
    password: str = Form("password123"),  # Default—change it!
    db: Session = Depends(get_db)
):
    try:
        # Check if user exists
        existing_user = crud.get_user_by_username(db, username)
        if existing_user:
            return {"message": f"User  '{username}' already exists. Use /login instead."}
        
        # Create user
        user_create = schemas.UserCreate(
            username=username,
            password=password,
            role="admin"  # Full access
        )
        new_user = crud.create_user(db, user_create)
        return {
            "message": "Admin user created successfully!",
            "user_id": new_user.id,
            "username": new_user.username,
            "role": new_user.role,
            "warning": "Remove this endpoint after use and change the password!"
        }
    except Exception as e:
        print(f"Admin Creation Error: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to create admin: {str(e)}")

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)