"""
Authentication & User API Pydantic Schemas (FastAPI Data Transfer Objects).

Defines validation models for user registration, login credentials, JWT bearer tokens,
and authenticated user profile responses across the HTTP presentation layer.
"""

from typing import Optional
from pydantic import BaseModel, ConfigDict, EmailStr, Field


class UserCreate(BaseModel):
    """
    Validation schema for new user registration requests.

    Attributes:
        email: Valid email address string (lowercased automatically by service layer).
        password: Plain text password candidate (min 8 characters).
        full_name: Optional human-readable full display name.
    """

    email: EmailStr = Field(..., description="User's email address.")
    password: str = Field(..., min_length=8, description="User password (minimum 8 characters).")
    full_name: Optional[str] = Field(None, description="Optional full name of the user.")


class UserLogin(BaseModel):
    """
    Validation schema for JSON-based user login requests.

    Attributes:
        email: Registered user email address.
        password: Candidate plain text password for verification.
    """

    email: EmailStr = Field(..., description="Registered email address.")
    password: str = Field(..., description="Plain text password candidate.")


class Token(BaseModel):
    """
    OAuth2 compatible bearer token payload schema returned upon successful login.

    Attributes:
        access_token: Encoded JWT string containing user subject and expiration claim.
        token_type: Token scheme identifier (defaults to 'bearer').
    """

    access_token: str = Field(..., description="Signed JWT access token string.")
    token_type: str = Field("bearer", description="Token protocol type (Bearer).")


class UserResponse(BaseModel):
    """
    Public user profile response DTO.

    Excludes sensitive fields (such as password hashes) to guarantee zero leakage.

    Attributes:
        id: Unique UUID string identifying the user.
        email: Registered email address.
        full_name: Display name or None.
        is_active: Flag indicating whether account is active.
    """

    id: str = Field(..., description="Unique UUID identifier for the user.")
    email: EmailStr = Field(..., description="Registered email address.")
    full_name: Optional[str] = Field(None, description="User's full display name.")
    is_active: bool = Field(True, description="Account active status flag.")

    model_config = ConfigDict(from_attributes=True)
