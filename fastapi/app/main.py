"""
Main entry point for FastAPI LDAP Authentication Service.
"""
from fastapi import FastAPI, HTTPException, status
from ldap3.core.exceptions import LDAPSocketOpenError

from app.config import settings
from app.schemas import LoginRequest, UserProfile, HealthResponse
from app.ldap import LDAPService

app = FastAPI(
    title=settings.app_title,
    description="Containerized FastAPI + OpenLDAP authentication service",
    version=settings.app_version,
)

ldap_service = LDAPService()


@app.get(
    "/health",
    response_model=HealthResponse,
    summary="Health Check",
    tags=["Monitoring"],
)
def health():
    """
    Check application and LDAP service connectivity status.
    """
    is_ldap_up = ldap_service.ping()
    return HealthResponse(
        status="ok" if is_ldap_up else "degraded",
        ldap_connected=is_ldap_up,
    )


@app.post(
    "/login",
    response_model=UserProfile,
    summary="Authenticate User against LDAP",
    tags=["Authentication"],
)
def login(request: LoginRequest):
    """
    Authenticate user credentials against OpenLDAP directory.
    Returns user profile and group memberships on success.
    """
    try:
        profile = ldap_service.authenticate_and_get_profile(
            username=request.username,
            password=request.password,
        )
    except LDAPSocketOpenError:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="LDAP directory server is unreachable",
        )
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Unexpected error occurred during authentication",
        )

    if profile is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid username or password",
        )

    return profile
