# Haven Backend Authentication & RBAC

This document outlines the authentication and role-based access control (RBAC) mechanisms implemented in the Haven backend.

## Overview
The Haven backend uses **JWT (JSON Web Tokens)** for stateless authentication. Security dependencies enforce strict role-based access to endpoints. The system relies exclusively on the isolated internal backend database without requiring any upstream external HRMS connections.

## Role Permissions
The system enforces three strict roles natively:
1. **`EMPLOYEE`**: Can only access their own specific prediction and metrics records (enforced via strict `employee_hash` payload matching).
2. **`MANAGER`**: Can access prediction and employee records belonging strictly to their assigned `department`.
3. **`HR_ADMIN`**: Has unrestricted access to aggregate metrics, analytics, and broad model predictions.

## Environment Variables
The following environment variables must be configured in `.env` for authentication to function properly:
- `JWT_SECRET`: A strong, randomly generated cryptographic key. **Never hardcode this in production.**
- `JWT_ALGORITHM`: The encryption algorithm (default: `HS256`).
- `ACCESS_TOKEN_EXPIRE_MINUTES`: JWT validity duration in minutes (default: `15`).

## Setup Instructions
To generate a secure JWT secret:
```bash
openssl rand -hex 32
```
Add the output to your `.env` file:
```ini
JWT_SECRET="your-secure-secret-here"
```

## Example Authenticated Requests

### 1. Generating a Token (Login)
```bash
curl -X 'POST' \
  'http://localhost:8000/api/v1/auth/token' \
  -H 'Content-Type: application/x-www-form-urlencoded' \
  -d 'username=hr&password=your_secure_password'
```
**Response:**
```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIsInR5c...",
  "token_type": "bearer"
}
```

### 2. Accessing a Protected Endpoint
Use the generated `access_token` in the `Authorization` header as a Bearer token.
```bash
curl -X 'POST' \
  'http://localhost:8000/api/v1/predictions' \
  -H 'Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5c...' \
  -H 'Content-Type: application/json' \
  -d '{
  "metrics": {
    "employee_hash": "hash123",
    "week_start_date": "2023-10-01",
    "department": "Engineering"
  }
}'
```

## Security Handlers & Response Codes
The backend is designed to return specific HTTP codes without revealing sensitive payload mapping errors:
- **`401 Unauthorized`**: Returned if the token is missing, expired ("Token has expired"), or malformed ("Could not validate credentials").
- **`403 Forbidden`**: Returned if an active token is provided, but the assigned role lacks permissions for the endpoint, if a record boundary is breached (e.g. Employee reading another Employee's hash), or if the user account is marked as deactivated (`is_active=False`).
