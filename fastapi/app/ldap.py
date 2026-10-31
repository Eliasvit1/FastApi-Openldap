"""
LDAP service handling user authentication and directory lookups.
"""
import logging
from typing import Optional
from ldap3 import Server, Connection, ALL, SUBTREE
from ldap3.core.exceptions import LDAPException, LDAPSocketOpenError
from ldap3.utils.conv import escape_filter_chars

from app.config import settings
from app.schemas import UserProfile

logger = logging.getLogger("ldap_service")


class LDAPService:
    def __init__(self):
        self.server = Server(
            host=settings.ldap_host,
            port=settings.ldap_port,
            get_info=ALL,
            connect_timeout=5,
        )

    def ping(self) -> bool:
        """
        Verify connectivity to LDAP server.
        """
        try:
            with Connection(
                self.server,
                user=settings.ldap_admin_dn,
                password=settings.ldap_admin_password,
                auto_bind=True,
                receive_timeout=5,
            ) as conn:
                return conn.bound
        except Exception as exc:
            logger.warning(f"LDAP ping failed: {exc}")
            return False

    def authenticate_and_get_profile(self, username: str, password: str) -> Optional[UserProfile]:
        """
        Perform Search-then-Bind authentication:
        1. Query user entry and metadata with service account.
        2. Validate credentials via simple bind as the user DN.
        3. Query user groups.
        """
        sanitized_username = escape_filter_chars(username.strip())
        search_base = f"{settings.ldap_users_ou},{settings.ldap_base_dn}"
        search_filter = f"(&(objectClass=inetOrgPerson)(uid={sanitized_username}))"

        # Step 1: Bind as service account and find the user DN and attributes
        try:
            with Connection(
                self.server,
                user=settings.ldap_admin_dn,
                password=settings.ldap_admin_password,
                auto_bind=True,
                receive_timeout=5,
            ) as admin_conn:
                admin_conn.search(
                    search_base=search_base,
                    search_filter=search_filter,
                    search_scope=SUBTREE,
                    attributes=["cn", "mail", "displayName", "uid"],
                )

                if not admin_conn.entries:
                    logger.info(f"User not found: {sanitized_username}")
                    return None

                user_entry = admin_conn.entries[0]
                user_dn = user_entry.entry_dn

                full_name = getattr(user_entry, "displayName", None) or getattr(user_entry, "cn", None)
                full_name_val = str(full_name.value) if full_name else None
                email = getattr(user_entry, "mail", None)
                email_val = str(email.value) if email else None

                # Step 2: Query user groups using admin connection
                groups_base = f"{settings.ldap_groups_ou},{settings.ldap_base_dn}"
                escaped_user_dn = escape_filter_chars(user_dn)
                group_filter = f"(&(objectClass=groupOfNames)(member={escaped_user_dn}))"
                admin_conn.search(
                    search_base=groups_base,
                    search_filter=group_filter,
                    search_scope=SUBTREE,
                    attributes=["cn"],
                )
                groups = [str(g.cn.value) for g in admin_conn.entries if hasattr(g, "cn")]

        except LDAPSocketOpenError as exc:
            logger.error(f"Cannot connect to LDAP server: {exc}")
            raise
        except LDAPException as exc:
            logger.error(f"LDAP directory lookup error: {exc}")
            raise

        # Step 3: Validate user credentials by attempting bind as the user
        try:
            with Connection(
                self.server,
                user=user_dn,
                password=password,
                auto_bind=False,
                receive_timeout=5,
            ) as user_conn:
                if not user_conn.bind():
                    logger.info(f"Invalid password for user: {user_dn}")
                    return None

        except LDAPSocketOpenError as exc:
            logger.error(f"Cannot connect to LDAP server during user bind: {exc}")
            raise
        except LDAPException as exc:
            logger.warning(f"User bind exception: {exc}")
            return None

        return UserProfile(
            authenticated=True,
            username=username,
            dn=user_dn,
            full_name=full_name_val,
            email=email_val,
            groups=groups,
        )
