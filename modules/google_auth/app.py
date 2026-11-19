"""
Standalone FastAPI Microservice for Google Authentication Sandbox.
Runs independently without affecting the primary tracking application.
"""

from typing import Optional
import os
from fastapi import FastAPI, Depends, HTTPException, Header, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse, FileResponse
from fastapi.staticfiles import StaticFiles

from modules.google_auth.config import config
from modules.google_auth.models import (
    GoogleAuthRequest,
    AuthSessionResponse,
    GoogleUserProfile,
    StatusResponse,
)
from modules.google_auth.verifier import (
    GoogleTokenVerifier,
    InvalidTokenError,
    ExpiredTokenError,
    InvalidAudienceError,
    EmailNotVerifiedError,
)
from modules.google_auth.session import session_manager

app = FastAPI(
    title="Standalone Google Authentication Sandbox",
    description="Isolated testing environment for Google Identity Services / OAuth 2.0 flow.",
    version="1.0.0",
)

# Enable CORS for local testing origins
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://127.0.0.1:5173",
        "http://localhost:8000",
        "http://127.0.0.1:8000",
        "http://localhost:8088",
        "http://127.0.0.1:8088",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

verifier = GoogleTokenVerifier(client_id=config.GOOGLE_CLIENT_ID)
STATIC_DIR = os.path.join(os.path.dirname(__file__), "static")


def get_current_user_claims(authorization: Optional[str] = Header(None)) -> dict:
    """Dependency that extracts and validates the bearer session token."""
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing or invalid Authorization header. Expected 'Bearer <token>'.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    token = authorization.split(" ")[1]
    claims = session_manager.verify_session(token)
    if not claims:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Session token is invalid, expired, or has been revoked.",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return claims


@app.get("/", response_class=HTMLResponse)
async def serve_test_ui():
    """Serve the standalone interactive Google Sign-In test page."""
    index_file = os.path.join(STATIC_DIR, "index.html")
    if os.path.isfile(index_file):
        return FileResponse(index_file)
    return HTMLResponse("<h1>Google Auth Sandbox Server Running. static/index.html not found.</h1>")


@app.get("/auth/config")
async def get_public_config():
    """Return public client configuration for frontend initialization."""
    return {
        "client_id": config.GOOGLE_CLIENT_ID,
        "mode": "standalone_sandbox",
    }


@app.post("/auth/google", response_model=AuthSessionResponse)
async def authenticate_with_google(request: GoogleAuthRequest):
    """
    Primary Google Authentication Endpoint.
    Validates Google ID Token, verifies claims, and issues an authenticated session token.
    """
    try:
        # Cryptographically verify the Google ID token
        profile = verifier.verify_token(request.credential)

        # Issue an independent session JWT token
        session_info = session_manager.create_session(profile)

        return AuthSessionResponse(
            access_token=session_info["access_token"],
            token_type=session_info["token_type"],
            expires_in_seconds=session_info["expires_in_seconds"],
            user=profile,
        )

    except ExpiredTokenError as err:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=str(err),
        )
    except InvalidAudienceError as err:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=str(err),
        )
    except EmailNotVerifiedError as err:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=str(err),
        )
    except InvalidTokenError as err:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=str(err),
        )
    except Exception as err:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Internal authentication error: {err}",
        )


@app.get("/auth/me")
async def get_authenticated_profile(claims: dict = Depends(get_current_user_claims)):
    """Retrieve verified profile information for the currently active session."""
    return {
        "sub": claims["sub"],
        "email": claims["email"],
        "name": claims.get("name"),
        "picture": claims.get("picture"),
        "session_id": claims.get("jti"),
    }


@app.post("/auth/logout", response_model=StatusResponse)
async def logout(authorization: Optional[str] = Header(None)):
    """
    Revoke the current session token (Logout).
    Blacklists the token from future authorized requests.
    """
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Authorization header required to perform logout.",
        )

    token = authorization.split(" ")[1]
    success = session_manager.revoke_session(token)
    if success:
        return StatusResponse(
            status="success",
            message="Session successfully revoked and logged out.",
        )
    return StatusResponse(
        status="warning",
        message="Session was not found or already expired.",
    )


@app.get("/auth/google/callback")
async def oauth_callback(code: Optional[str] = None, state: Optional[str] = None, error: Optional[str] = None):
    """
    Handle Google OAuth authorization code redirect (if code flow is used).
    """
    if error:
        return HTMLResponse(
            f"<h3>Google OAuth Error:</h3><p style='color:red;'>{error}</p>",
            status_code=400,
        )
    if code:
        return {
            "status": "code_received",
            "message": "OAuth authorization code received successfully.",
            "code_preview": f"{code[:12]}...",
            "state": state,
        }
    return {"status": "ready", "message": "Google OAuth callback endpoint ready."}
