"""
Pydantic data schemas for Google Authentication and User Sessions.
"""

from typing import Optional
from pydantic import BaseModel, EmailStr, Field


class GoogleAuthRequest(BaseModel):
    """Payload received from Google Sign-In button on the frontend."""
    credential: str = Field(..., description="Google ID Token (JWT) returned by Google Identity Services")
    client_id: Optional[str] = Field(None, description="Client ID sent from frontend for cross-validation")


class GoogleUserProfile(BaseModel):
    """Verified user details extracted from Google's cryptographically signed ID token."""
    sub: str = Field(..., description="Unique immutable Google User Identifier")
    email: EmailStr = Field(..., description="Verified Google Account Email")
    name: Optional[str] = Field(None, description="User's Full Name")
    given_name: Optional[str] = Field(None, description="First Name")
    family_name: Optional[str] = Field(None, description="Last Name")
    picture: Optional[str] = Field(None, description="Google Profile Avatar URL")
    email_verified: bool = Field(True, description="Whether email has been verified by Google")


class AuthSessionResponse(BaseModel):
    """Response returned upon successful authentication containing session token and user profile."""
    access_token: str
    token_type: str = "bearer"
    expires_in_seconds: int
    user: GoogleUserProfile


class StatusResponse(BaseModel):
    """Generic status response for operations like logout, health, etc."""
    status: str
    message: str
