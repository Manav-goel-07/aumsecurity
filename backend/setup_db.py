#!/usr/bin/env python
from app.database import engine, get_db, Base
from app import models, schemas, crud
from app.auth import get_password_hash
from sqlalchemy import inspect

# Drop and create tables
Base.metadata.drop_all(bind=engine)
print("Dropped all tables.")
Base.metadata.create_all(bind=engine)
print("Created tables: users, persons, cameras, events.")

# Create user
db = next(get_db())
user_data = schemas.UserCreate(username="admin", password="password", role="admin")
created_user = crud.create_user(db, user_data)
if created_user:
    print(f"SUCCESS: User created - ID={created_user.id}, Username={created_user.username}")
    print(f"Hashed Password (first 10 chars): {created_user.hashed_password[:10]}...")
else:
    print("ERROR: User creation failed.")

# Verify
columns = [col['name'] for col in inspect(engine).get_columns('users')]
print(f"Users table columns: {columns}")
from app.auth import get_user
test_user = get_user(db, "admin")
if test_user:
    print(f"VERIFIED: User fetched - Username={test_user.username}, Hashed PW exists={bool(test_user.hashed_password)}")
db.close()
print("Setup complete!")