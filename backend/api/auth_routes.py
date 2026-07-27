"""
Authentication API Routes

Endpoints for:
- User login with credentials
- Face recognition login
- New user registration
- Face registration for existing users
"""

import hashlib
import secrets
from datetime import datetime, timedelta
from typing import Optional, List
from pydantic import BaseModel
from fastapi import APIRouter, HTTPException, Depends, status
import structlog

from config import settings

logger = structlog.get_logger(__name__)
router = APIRouter(prefix="/api/auth", tags=["Authentication"])


# ============================================================================
# Pydantic Models
# ============================================================================

class LoginRequest(BaseModel):
    """Credential-based login request."""
    username: str
    password: str


class FaceLoginRequest(BaseModel):
    """Face recognition login request."""
    image_data: str  # Base64 encoded camera image


class RegisterRequest(BaseModel):
    """New user registration request."""
    username: str
    password: str
    face_image: Optional[str] = None  # Optional base64 face image


class FaceRegisterRequest(BaseModel):
    """Register face for existing user."""
    username: str
    password: str  # Verify credentials first
    face_image: str  # Base64 face image


class AuthResponse(BaseModel):
    """Authentication response."""
    success: bool
    message: str
    token: Optional[str] = None
    username: Optional[str] = None
    user_id: Optional[str] = None


class UserInfo(BaseModel):
    """User information."""
    username: str
    has_face: bool
    created_at: str


# ============================================================================
# In-Memory User Store (replaced by Supabase in production)
# ============================================================================

# Temp in-memory store until Supabase is connected
_users_db = {
    "admin": {
        "id": "user_admin_001",
        "username": "admin",
        "password_hash": hashlib.sha256("admin123".encode()).hexdigest(),
        "face_embedding": None,
        "created_at": datetime.utcnow().isoformat()
    }
}

_sessions = {}  # token -> user_id mapping

# Pre-registered reference image path
REFERENCE_PHOTO_PATH = "Hemanth-photo.jpg"

async def preload_reference_user():
    """Pre-load Hemanth from reference photo for face recognition."""
    import os
    
    # Check if reference photo exists
    photo_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "..", REFERENCE_PHOTO_PATH)
    if not os.path.exists(photo_path):
        # Try absolute path
        photo_path = os.path.join("c:/Users/acer/Downloads/ai-embodied-agent", REFERENCE_PHOTO_PATH)
    
    if not os.path.exists(photo_path):
        logger.warning("Reference photo not found", path=REFERENCE_PHOTO_PATH)
        return
    
    # Check if hemanth user already exists with face
    if "hemanth" in _users_db and _users_db["hemanth"].get("face_embedding"):
        logger.info("Reference user already registered")
        return
    
    try:
        from ml.face_recognition import get_face_service
        face_service = await get_face_service()
        
        # Register face from file
        face_embedding = await face_service.register_face(photo_path)
        
        if face_embedding:
            _users_db["hemanth"] = {
                "id": "user_hemanth_ref",
                "username": "hemanth",
                "password_hash": hash_password("hemanth123"),  # Default password
                "face_embedding": face_embedding,
                "created_at": datetime.utcnow().isoformat()
            }
            logger.info("Pre-registered reference user 'hemanth' from photo", embedding_dim=len(face_embedding))
        else:
            logger.warning("Could not extract face from reference photo")
    except Exception as e:
        logger.error("Failed to pre-register reference user", error=str(e))


def hash_password(password: str) -> str:
    """Hash password using SHA-256."""
    return hashlib.sha256(password.encode()).hexdigest()


def generate_token() -> str:
    """Generate secure session token."""
    return secrets.token_urlsafe(32)


def verify_password(password: str, password_hash: str) -> bool:
    """Verify password against hash."""
    return hash_password(password) == password_hash


# ============================================================================
# Supabase Integration
# ============================================================================

async def get_user_from_supabase(username: str) -> Optional[dict]:
    """Get user from Supabase."""
    try:
        from data.supabase_service import get_supabase_service
        supabase = await get_supabase_service()
        
        if not supabase._initialized:
            return None
        
        response = supabase._client.table("users").select("*").eq("username", username).execute()
        if response.data and len(response.data) > 0:
            return response.data[0]
        return None
    except Exception as e:
        logger.warning("Supabase user lookup failed, using local", error=str(e))
        return None


async def create_user_in_supabase(username: str, password_hash: str, face_embedding: List[float] = None) -> Optional[str]:
    """Create user in Supabase."""
    try:
        from data.supabase_service import get_supabase_service
        supabase = await get_supabase_service()
        
        if not supabase._initialized:
            return None
        
        response = supabase._client.table("users").insert({
            "username": username,
            "password_hash": password_hash,
            "face_embedding": face_embedding
        }).execute()
        
        if response.data and len(response.data) > 0:
            return response.data[0].get("id")
        return None
    except Exception as e:
        logger.warning("Supabase user creation failed", error=str(e))
        return None


async def update_user_face_in_supabase(username: str, face_embedding: List[float]) -> bool:
    """Update user face embedding in Supabase."""
    try:
        from data.supabase_service import get_supabase_service
        supabase = await get_supabase_service()
        
        if not supabase._initialized:
            return False
        
        supabase._client.table("users").update({
            "face_embedding": face_embedding
        }).eq("username", username).execute()
        
        return True
    except Exception as e:
        logger.warning("Supabase face update failed", error=str(e))
        return False


# ============================================================================
# API Endpoints
# ============================================================================

@router.post("/login", response_model=AuthResponse)
async def login_with_credentials(request: LoginRequest):
    """
    Login with username and password.
    
    Returns session token on success.
    """
    username = request.username.lower()
    
    # Try Supabase first
    user = await get_user_from_supabase(username)
    
    # Fall back to local store
    if user is None:
        user = _users_db.get(username)
    
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid username or password"
        )
    
    if not verify_password(request.password, user.get("password_hash", "")):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid username or password"
        )
    
    # Generate session token
    token = generate_token()
    _sessions[token] = {
        "user_id": user.get("id", username),
        "username": username,
        "created_at": datetime.utcnow().isoformat()
    }
    
    logger.info("User logged in with credentials", username=username)
    
    return AuthResponse(
        success=True,
        message="Login successful",
        token=token,
        username=username,
        user_id=user.get("id", username)
    )


@router.post("/login/face", response_model=AuthResponse)
async def login_with_face(request: FaceLoginRequest):
    """
    Login with face recognition.
    
    Requires camera image in base64 format.
    Matches against all registered faces in database.
    """
    try:
        from ml.face_recognition import get_face_service
        face_service = await get_face_service()
    except Exception as e:
        logger.error("Face service unavailable", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Face recognition service unavailable"
        )
    
    # Get all users with face embeddings
    all_users = []
    
    # First check local users - always available
    local_users_with_face = 0
    for username, user in _users_db.items():
        if user.get("face_embedding"):
            all_users.append(user)
            local_users_with_face += 1
    
    logger.info("Local users with face", count=local_users_with_face)
    
    # Try Supabase as secondary
    supabase_users = 0
    try:
        from data.supabase_service import get_supabase_service
        supabase = await get_supabase_service()
        if supabase._initialized:
            response = supabase._client.table("users").select("*").not_.is_("face_embedding", "null").execute()
            if response.data:
                all_users.extend(response.data)
                supabase_users = len(response.data)
            logger.info("Supabase users with face", count=supabase_users)
    except Exception as e:
        logger.warning("Supabase face query failed", error=str(e))
    
    if not all_users:
        # More helpful error message
        total_local = len(_users_db)
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"No users with registered faces found. Total users: {total_local} (local). Register your face first."
        )
    
    # Try to match face against each user
    best_match = None
    best_similarity = 0.0
    
    for user in all_users:
        embedding = user.get("face_embedding")
        if not embedding:
            continue
        
        is_match, similarity = await face_service.verify_face(request.image_data, embedding)
        
        if is_match and similarity > best_similarity:
            best_match = user
            best_similarity = similarity
    
    if best_match is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Face not recognized"
        )
    
    # Generate session
    token = generate_token()
    username = best_match.get("username")
    _sessions[token] = {
        "user_id": best_match.get("id", username),
        "username": username,
        "created_at": datetime.utcnow().isoformat()
    }
    
    logger.info("User logged in with face", username=username, similarity=best_similarity)
    
    return AuthResponse(
        success=True,
        message=f"Face recognized with {best_similarity:.0%} confidence",
        token=token,
        username=username,
        user_id=best_match.get("id", username)
    )


@router.post("/register", response_model=AuthResponse)
async def register_user(request: RegisterRequest):
    """
    Register a new user.
    
    Optionally include face image for face recognition.
    """
    username = request.username.lower()
    
    # Check if username exists
    if username in _users_db:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Username already exists"
        )
    
    existing = await get_user_from_supabase(username)
    if existing:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Username already exists"
        )
    
    # Generate face embedding if image provided
    face_embedding = None
    if request.face_image:
        try:
            from ml.face_recognition import get_face_service
            face_service = await get_face_service()
            face_embedding = await face_service.register_face(request.face_image)
        except Exception as e:
            logger.warning("Face registration failed during signup", error=str(e))
    
    # Hash password
    password_hash = hash_password(request.password)
    
    # Create user
    user_id = await create_user_in_supabase(username, password_hash, face_embedding)
    
    if user_id is None:
        # Fall back to local storage
        user_id = f"user_{username}_{secrets.token_hex(4)}"
        _users_db[username] = {
            "id": user_id,
            "username": username,
            "password_hash": password_hash,
            "face_embedding": face_embedding,
            "created_at": datetime.utcnow().isoformat()
        }
    
    # Auto-login
    token = generate_token()
    _sessions[token] = {
        "user_id": user_id,
        "username": username,
        "created_at": datetime.utcnow().isoformat()
    }
    
    logger.info("New user registered", username=username, has_face=face_embedding is not None)
    
    return AuthResponse(
        success=True,
        message="Registration successful",
        token=token,
        username=username,
        user_id=user_id
    )


@router.post("/register/face", response_model=AuthResponse)
async def register_face(request: FaceRegisterRequest):
    """
    Register face for an existing user.
    
    Requires valid credentials to authenticate first.
    """
    username = request.username.lower()
    
    # Verify credentials first
    user = await get_user_from_supabase(username)
    if user is None:
        user = _users_db.get(username)
    
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid credentials"
        )
    
    if not verify_password(request.password, user.get("password_hash", "")):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid credentials"
        )
    
    # Generate face embedding
    try:
        from ml.face_recognition import get_face_service
        face_service = await get_face_service()
        face_embedding = await face_service.register_face(request.face_image)
    except Exception as e:
        logger.error("Face registration failed", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Face registration failed"
        )
    
    if face_embedding is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No face detected in image"
        )
    
    # Update user
    success = await update_user_face_in_supabase(username, face_embedding)
    
    if not success:
        # Update local store
        if username in _users_db:
            _users_db[username]["face_embedding"] = face_embedding
    
    logger.info("Face registered for user", username=username)
    
    return AuthResponse(
        success=True,
        message="Face registered successfully",
        username=username,
        user_id=user.get("id", username)
    )


@router.get("/verify")
async def verify_token(token: str):
    """Verify session token is valid."""
    session = _sessions.get(token)
    
    if session is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token"
        )
    
    return {
        "valid": True,
        "username": session.get("username"),
        "user_id": session.get("user_id")
    }


@router.post("/logout")
async def logout(token: str):
    """Invalidate session token."""
    if token in _sessions:
        del _sessions[token]
    
    return {"success": True, "message": "Logged out"}


@router.get("/users", response_model=List[UserInfo])
async def list_users():
    """List all users (admin only in production)."""
    users = []
    seen_usernames = set()
    
    # Local users
    for username, user in _users_db.items():
        users.append(UserInfo(
            username=username,
            has_face=user.get("face_embedding") is not None,
            created_at=user.get("created_at", "")
        ))
        seen_usernames.add(username)
    
    # Supabase users
    try:
        from data.supabase_service import get_supabase_service
        supabase = await get_supabase_service()
        if supabase._initialized:
            response = supabase._client.table("users").select("*").execute()
            for u in (response.data or []):
                if u.get("username") not in seen_usernames:
                    users.append(UserInfo(
                        username=u.get("username"),
                        has_face=u.get("face_embedding") is not None,
                        created_at=u.get("created_at", "")
                    ))
    except:
        pass
    
    return users
