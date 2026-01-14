import hashlib
import os
import streamlit as st
import jwt
import datetime
from .database import SessionLocal
from .models import User

# Secret key for signing tokens. In production, this should be in st.secrets
SECRET_KEY = st.secrets.get("auth", {}).get("secret_key", "dev_secret_key_CHANGE_ME")

def generate_salt():
    return os.urandom(16).hex()

def hash_password(password, salt):
    # Using pbkdf2_hmac with sha256
    password_bytes = password.encode('utf-8')
    salt_bytes = bytes.fromhex(salt)
    # 100,000 iterations is a reasonable default for pbkdf2
    hash_bytes = hashlib.pbkdf2_hmac('sha256', password_bytes, salt_bytes, 100000)
    return hash_bytes.hex()

def check_password(password, stored_hash, salt):
    new_hash = hash_password(password, salt)
    return new_hash == stored_hash

def create_token(username):
    """Generates a JWT token for the user."""
    expiration = datetime.datetime.utcnow() + datetime.timedelta(days=7)
    payload = {
        "sub": username,
        "exp": expiration
    }
    token = jwt.encode(payload, SECRET_KEY, algorithm="HS256")
    return token

def validate_token(token):
    """Validates the JWT token and returns the user object if valid."""
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=["HS256"])
        username = payload["sub"]
        
        # Verify user still exists
        db = SessionLocal()
        try:
            user = db.query(User).filter(User.username == username).first()
            return user
        finally:
            db.close()
            
    except jwt.ExpiredSignatureError:
        return None
    except jwt.InvalidTokenError:
        return None
    except Exception:
        return None

def create_user(username, password, name=None, role="user"):
    db = SessionLocal()
    try:
        if db.query(User).filter(User.username == username).first():
            return False, "Username already exists"
        
        salt = generate_salt()
        hashed_pw = hash_password(password, salt)
        
        new_user = User(
            username=username,
            name=name,
            data_hash=hashed_pw,
            salt=salt,
            role=role
        )
        db.add(new_user)
        db.commit()
        db.refresh(new_user)
        return True, new_user
    except Exception as e:
        db.rollback()
        return False, str(e)
    finally:
        db.close()

def login_user(username, password):
    db = SessionLocal()
    try:
        user = db.query(User).filter(User.username == username).first()
        if not user:
            return None
        
        if check_password(password, user.data_hash, user.salt):
            return user
        return None
    finally:
        db.close()

def get_all_users():
    db = SessionLocal()
    try:
        return db.query(User).all()
    finally:
        db.close()

def delete_user(username):
    db = SessionLocal()
    try:
        user = db.query(User).filter(User.username == username).first()
        if user:
            db.delete(user)
            db.commit()
            return True
        return False
    except Exception:
        db.rollback()
        return False
    finally:
        db.close()

def init_db_and_admin_if_needed():
    # Only import here to avoid circular dependency issues if called at top level
    from .database import engine, Base
    Base.metadata.create_all(bind=engine)
    
    # Check if we have any users, if not, create admin
    db = SessionLocal()
    try:
        if db.query(User).count() == 0:
            print("Creating default admin user...")
            create_user("admin", "admin123", "Administrator", "admin")
    finally:
        db.close()

def update_user(username, name=None, role=None):
    db = SessionLocal()
    try:
        user = db.query(User).filter(User.username == username).first()
        if not user:
            return False, "User not found"
        
        if name is not None:
            user.name = name
        if role is not None:
            user.role = role
            
        db.commit()
        return True, "User updated successfully"
    except Exception as e:
        db.rollback()
        return False, str(e)
    finally:
        db.close()

def reset_password(username, new_password):
    db = SessionLocal()
    try:
        user = db.query(User).filter(User.username == username).first()
        if not user:
            return False, "User not found"
        
        salt = generate_salt()
        hashed_pw = hash_password(new_password, salt)
        
        user.salt = salt
        user.data_hash = hashed_pw
        
        db.commit()
        return True, "Password reset successfully"
    except Exception as e:
        db.rollback()
        return False, str(e)
    finally:
        db.close()
