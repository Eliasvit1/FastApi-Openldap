"""
Pydantic schemas for request and response models.
"""
from typing import List, Optional
from pydantic import BaseModel, Field


class LoginRequest(BaseModel):
    username: str = Field(..., min_length=1, max_length=128, description="LDAP user identifier (UID)")
    password: str = Field(..., min_length=1, description="LDAP user password")


class UserProfile(BaseModel):
    authenticated: bool = True
    username: str
    dn: str
    full_name: Optional[str] = None
    email: Optional[str] = None
    groups: List[str] = Field(default_factory=list)


class HealthResponse(BaseModel):
    status: str
    ldap_connected: bool
