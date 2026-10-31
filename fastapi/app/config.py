"""
Application configuration management using environment variables.
"""
import os
from pydantic import BaseModel, Field


class Settings(BaseModel):
    app_title: str = "LDAP Authentication API"
    app_version: str = "1.0.0"
    ldap_host: str = Field(default_factory=lambda: os.getenv("LDAP_HOST", "openldap"))
    ldap_port: int = Field(default_factory=lambda: int(os.getenv("LDAP_PORT", "389")))
    ldap_base_dn: str = Field(default_factory=lambda: os.getenv("LDAP_BASE_DN", "dc=example,dc=com"))
    ldap_admin_dn: str = Field(default_factory=lambda: os.getenv("LDAP_ADMIN_DN", "cn=admin,dc=example,dc=com"))
    ldap_admin_password: str = Field(default_factory=lambda: os.getenv("LDAP_ADMIN_PASSWORD", "adminpassword"))
    ldap_users_ou: str = Field(default_factory=lambda: os.getenv("LDAP_USERS_OU", "ou=users"))
    ldap_groups_ou: str = Field(default_factory=lambda: os.getenv("LDAP_GROUPS_OU", "ou=groups"))


settings = Settings()
