# Containerized FastAPI + OpenLDAP Authentication Lab

A containerized, production-aligned authentication service integrating **FastAPI**, **OpenLDAP**, and **phpLDAPadmin** orchestrated via Docker Compose.

---

## Architecture Overview

```
                      +-------------------+
                      |   Client / CURL   |
                      +---------+---------+
                                |
               +----------------+----------------+
               | :8000                           | :8080
               v                                 v
      +-----------------+              +--------------------+
      |   FastAPI API   |              |    phpLDAPadmin    |
      |   (ldap-api)    |              |   (phpldapadmin)   |
      +--------+--------+              +---------+----------+
               |                                 |
               | ldap://openldap:389             | ldap://openldap:389
               +----------------+----------------+
                                |
                                v
                      +-------------------+
                      |     OpenLDAP      |
                      |    (openldap)     |
                      |  :389 (LDAP)      |
                      |  :636 (LDAPS)     |
                      +-------------------+
```

### Key Technical Improvements
1. **Automated LDIF Bootstrap:** Sample directory entries in `ldap/users.ldif` are imported automatically on first container initialization without requiring manual `docker cp` or `ldapadd` commands.
2. **Container Healthchecks:** OpenLDAP includes an automated health check using `ldapwhoami`. Dependent services (`api`, `phpldapadmin`) wait for OpenLDAP to be healthy before starting (`condition: service_healthy`).
3. **Robust Search-then-Bind Authentication:**
   - Queries directory metadata via a service bind.
   - Sanitizes username input using `ldap3.utils.conv.escape_filter_chars` to defend against LDAP injection.
   - Resolves the exact user Distinguished Name (DN) dynamically.
   - Verifies credentials via a dedicated user bind.
   - Queries and returns user group memberships (e.g., `developers`).
4. **Resilient Error Handling:** Returns HTTP 503 for directory communication failures, HTTP 401 for invalid credentials, and HTTP 422 for malformed payloads.
5. **Decoupled Configuration:** Environment settings managed through `.env` and `.env.example`.

---

## Project Structure

```text
.
├── .env.example             # Template for environment variables
├── .env                     # Local environment configuration
├── docker-compose.yml       # Docker service orchestrator with healthchecks
├── README.md                # Technical documentation
├── fastapi/
│   ├── Dockerfile           # Minimal Python 3.11-slim container image
│   ├── requirements.txt     # Python dependencies (fastapi, uvicorn, ldap3, pydantic)
│   └── app/
│       ├── __init__.py      # Package identifier
│       ├── config.py        # Centralized settings loader
│       ├── schemas.py       # Pydantic request and response schemas
│       ├── ldap.py          # LDAP directory client and authentication logic
│       └── main.py          # FastAPI application routing and endpoints
└── ldap/
    └── users.ldif           # Bootstrap directory entries (OUs, users, groups)
```

---

## Quick Start

### 1. Configure Environment
Copy the sample environment variables:
```bash
cp .env.example .env
```

### 2. Start Services
Launch all services in detached mode:
```bash
docker compose up -d --build
```

### 3. Verify Container Status
Check that all containers are running and healthy:
```bash
docker compose ps
```

Expected output:
```text
NAME           IMAGE                        STATUS                   PORTS
openldap       osixia/openldap:1.5.0        Up (healthy)             0.0.0.0:389->389/tcp, 0.0.0.0:636->636/tcp
ldap-api       ldap-api                     Up                       0.0.0.0:8000->8000/tcp
phpldapadmin   osixia/phpldapadmin:latest   Up                       0.0.0.0:8080->80/tcp
```

---

## API Endpoints

Interactive Swagger documentation is available at:
`http://localhost:8000/docs`

### Health Check: `GET /health`
Monitors both API uptime and live connectivity to the LDAP server.

**Request:**
```bash
curl http://localhost:8000/health
```

**Response (HTTP 200):**
```json
{
  "status": "ok",
  "ldap_connected": true
}
```

---

### User Authentication: `POST /login`
Authenticates user credentials, sanitizes input, and retrieves user attributes and groups.

**Request (Alice):**
```bash
curl -X POST http://localhost:8000/login \
  -H "Content-Type: application/json" \
  -d '{"username":"alice","password":"alice123"}'
```

**Response (HTTP 200 OK):**
```json
{
  "authenticated": true,
  "username": "alice",
  "dn": "uid=alice,ou=users,dc=example,dc=com",
  "full_name": "Alice Smith",
  "email": "alice@example.com",
  "groups": [
    "developers"
  ]
}
```

**Request (Invalid Credentials):**
```bash
curl -X POST http://localhost:8000/login \
  -H "Content-Type: application/json" \
  -d '{"username":"alice","password":"invalidpassword"}'
```

**Response (HTTP 401 Unauthorized):**
```json
{
  "detail": "Invalid username or password"
}
```

---

## LDAP Directory Management

### phpLDAPadmin Web Interface
Access the administrative web GUI at:
`http://localhost:8080`

- **Login DN:** `cn=admin,dc=example,dc=com`
- **Password:** `adminpassword`

### Direct CLI Verification

Verify administrative authentication:
```bash
docker exec openldap ldapwhoami \
  -x \
  -H ldap://localhost \
  -D "cn=admin,dc=example,dc=com" \
  -w adminpassword
```

Search users in the directory:
```bash
docker exec openldap ldapsearch \
  -x \
  -H ldap://localhost \
  -D "cn=admin,dc=example,dc=com" \
  -w adminpassword \
  -b "ou=users,dc=example,dc=com" \
  "(objectClass=inetOrgPerson)"
```

Search group memberships:
```bash
docker exec openldap ldapsearch \
  -x \
  -H ldap://localhost \
  -D "cn=admin,dc=example,dc=com" \
  -w adminpassword \
  -b "ou=groups,dc=example,dc=com" \
  "(objectClass=groupOfNames)"
```

---

## Sample Credentials

| Username | Password | Full Name | Group |
|---|---|---|---|
| `alice` | `alice123` | Alice Smith | `developers` |
| `bob` | `bob123` | Bob Johnson | `developers` |
| `admin` | `adminpassword` | LDAP Administrator | Directory Admin |

---

## Stopping and Teardown

To stop containers while preserving LDAP data volumes:
```bash
docker compose down
```

To stop containers and completely remove volumes (resetting directory data):
```bash
docker compose down -v
```

---

## Security Considerations

- **Transport Security:** For production deployments across untrusted networks, replace unencrypted LDAP (port 389) with **LDAPS (port 636)** or **StartTLS** with valid TLS certificates.
- **Service Account Permissions:** Use a dedicated read-only service account rather than `cn=admin` for directory lookups.
- **Secret Management:** Never commit plaintext passwords in `.env` files to source control. Use secret management tools (Docker Secrets, Vault, or AWS Secrets Manager) in production.
