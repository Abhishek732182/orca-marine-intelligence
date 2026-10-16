# ORCA Super Admin — Backend Integration & API Contract Specification

**Document Version:** 1.0.0  
**Target Architecture:** FastAPI Microservices & Collaborative Agent Mesh  
**Security Standard:** Bearer JWT Authentication with Role-Based Access Control (RBAC)  
**Frontend Consumer:** ORCA Single Page Application (`/admin/dashboard`)  

---

## 1. Executive Summary & Security Scheme

This document defines the authoritative API contracts required by the **ORCA Super Admin Console**. 

The frontend console has been built with strict operational fidelity:
- **No Synthetic Data:** Production screens never display simulated users, fake conversation histories, synthetic telemetry metrics, or mock mutation success.
- **Explicit Missing States:** When an administrative endpoint returns HTTP 404, 501, or connection failure, the frontend clearly captures the state as **"Backend Integration Required"** and presents the exact contract specification.
- **Draft Persistence Warnings:** When toggling agent runtime settings, feature flags, or maritime safety thresholds, client changes are flagged as **"Unpersisted Drafts"** until acknowledged and persisted by the backend service.
- **Zero Client Privacy Leakage:** Conversation audit traces are never extracted from browser local storage; audit inspection requires explicit server-side queries accompanied by mandatory audit justification headers.

### Authentication & Authorization Requirements

All administrative endpoints require an `Authorization` header containing a valid Bearer token issued during login:

```http
Authorization: Bearer <jwt_access_token>
```

#### Token Claims Specification:
```json
{
  "sub": "usr_admin_01",
  "email": "admin@orca.io",
  "role": "admin",
  "affiliation": "ORCA Maritime Defense & Operations",
  "iat": 1760520000,
  "exp": 1760606400
}
```

#### Authorization Enforcement Rules:
1. **HTTP 401 Unauthorized:** Returned if the `Authorization` header is missing, malformed, or the token signature / expiration has lapsed.
2. **HTTP 403 Forbidden:** Returned if the authenticated user has a non-admin role (e.g. `researcher`, `oceanographer`, `fleet_officer`). Client route guards (`ProtectedRoute requiredRole="admin"`) restrict UI rendering, but **the FastAPI backend must independently verify role claims on every administrative request**.

---

## 2. Administrative Endpoints Matrix

| Domain | Method | Endpoint Path | Role Required | Purpose |
| :--- | :--- | :--- | :--- | :--- |
| **Overview** | `GET` | `/api/admin/metrics` | `admin` | Real-time system telemetry, active workloads, and dispatch volumes |
| **Overview** | `GET` | `/api/health` | `public` / `admin` | Microservice liveness and reachability probe |
| **Users** | `GET` | `/api/admin/users` | `admin` | Paginated user accounts, RBAC roles, and status flags |
| **Users** | `PATCH` | `/api/admin/users/{userId}/role` | `admin` | Update user access role (`researcher`, `oceanographer`, `fleet_officer`, `admin`) |
| **Users** | `PATCH` | `/api/admin/users/{userId}/status` | `admin` | Suspend or activate user accounts with justification |
| **Users** | `DELETE` | `/api/admin/users/{userId}` | `admin` | Hard delete / GDPR purge of user account |
| **Conversations** | `GET` | `/api/admin/conversations/audit` | `admin` | Query audited conversation stream with `X-Audit-Reason` |
| **Conversations** | `GET` | `/api/admin/conversations/{id}/audit` | `admin` | Retrieve complete audited execution plan, tool calls, and evidence |
| **Agents** | `GET` | `/api/admin/agents` | `admin` | Query agent registry, timeouts, model routing, and operational status |
| **Agents** | `PATCH` | `/api/admin/agents/{agentId}` | `admin` | Persist agent timeout, model routing, cache TTL, and enable/disable flags |
| **Agents** | `POST` | `/api/agents/{agent}/analyze` | `admin` / `user` | Specialist agent microservice execution probe |
| **Features** | `GET` | `/api/admin/features` | `admin` | Query platform feature flags and rollout percentages |
| **Features** | `PATCH` | `/api/admin/features/{flagKey}` | `admin` | Persist feature flag state, rollout %, and environment target |
| **Marine APIs** | `GET` | `/api/admin/marine-sources` | `admin` | Open-Meteo, ECMWF, and CMEMS rate-limiting budgets and quota usage |
| **Marine APIs** | `POST` | `/api/admin/marine-sources/{provider}/probe` | `admin` | Execute active connectivity probe to external marine telemetry provider |
| **Security** | `GET` | `/api/admin/audit-logs` | `admin` | Retrieve immutable security event log stream |
| **Settings** | `GET` | `/api/admin/settings` | `admin` | Retrieve persistent maritime safety hazard limits and timeouts |
| **Settings** | `PATCH` | `/api/admin/settings` | `admin` | Persist safety thresholds (wind limits, wave heights, reef clearance) |

---

## 3. Detailed Request & Response Schemas

### 3.1. Overview Telemetry (`GET /api/admin/metrics`)

#### Request Headers:
```http
GET /api/admin/metrics HTTP/1.1
Host: 127.0.0.1:8001
Authorization: Bearer <token>
Accept: application/json
```

#### Response (HTTP 200 OK):
```json
{
  "status": "ok",
  "timestamp": "2026-10-15T12:00:00Z",
  "server_uptime_seconds": 86400,
  "total_registered_users": 142,
  "active_sessions_count": 9,
  "total_agent_dispatches_24h": 3840,
  "average_latency_ms": 145.2,
  "active_feature_flags_count": 6,
  "system_load": {
    "cpu_usage_pct": 18.4,
    "memory_usage_mb": 512.8
  }
}
```

---

### 3.2. User Management (`/api/admin/users`)

#### 1. List Users (`GET /api/admin/users`)
- **Query Parameters:**
  - `role`: (string, optional) Filter by `researcher`, `oceanographer`, `fleet_officer`, `admin`
  - `search`: (string, optional) Search query matching name, email, or affiliation
  - `page`: (integer, default: 1)
  - `limit`: (integer, default: 20)

#### Response (HTTP 200 OK):
```json
{
  "users": [
    {
      "id": "usr_01",
      "fullName": "Dr. Rachel Carson",
      "email": "rachel.carson@orca-marine.org",
      "role": "oceanographer",
      "status": "active",
      "affiliation": "National Institute of Oceanography (NIO)",
      "createdAt": "2026-01-15T08:00:00Z"
    }
  ],
  "total": 1,
  "page": 1,
  "limit": 20
}
```

#### 2. Update User Role (`PATCH /api/admin/users/{userId}/role`)
- **Request Body (JSON):**
```json
{
  "role": "admin"
}
```
- **Response (HTTP 200 OK):**
```json
{
  "success": true,
  "userId": "usr_01",
  "updatedRole": "admin"
}
```

#### 3. Update User Status (`PATCH /api/admin/users/{userId}/status`)
- **Request Body (JSON):**
```json
{
  "status": "suspended",
  "reason": "SECURITY_POLICY_VIOLATION"
}
```
- **Response (HTTP 200 OK):**
```json
{
  "success": true,
  "userId": "usr_01",
  "status": "suspended"
}
```

---

### 3.3. Conversation Audit (`/api/admin/conversations/audit`)

#### 1. List Audited Sessions (`GET /api/admin/conversations/audit`)
- **Request Headers:**
  - `Authorization: Bearer <token>`
  - `X-Audit-Reason: COMPLIANCE_Q4_REVIEW` *(Required for auditing governance)*
- **Query Parameters:**
  - `agent_id`: (string, optional) e.g., `safety_risk`, `weather`, `orchestrator`
  - `user_id`: (string, optional) Filter by user ID
  - `search`: (string, optional) Search query in transcripts
  - `limit`: (integer, default: 50)

#### Response (HTTP 200 OK):
```json
{
  "conversations": [
    {
      "id": "conv_88921",
      "user_id": "usr_01",
      "user_email": "rachel.carson@orca-marine.org",
      "agent_name": "Safety/Risk Agent",
      "timestamp": "2026-10-15T11:45:00Z",
      "validation_status": "VERIFIED",
      "tool_invocations_count": 3,
      "summary": "Hazard analysis for vessel transit off Goa Shelf"
    }
  ],
  "total": 1
}
```

#### 2. Audit Trace Detail (`GET /api/admin/conversations/{id}/audit`)
- **Response (HTTP 200 OK):**
```json
{
  "id": "conv_88921",
  "user_id": "usr_01",
  "created_at": "2026-10-15T11:45:00Z",
  "plan": [
    {
      "step_id": 1,
      "description": "Evaluate atmospheric wind speed and Beaufort force",
      "status": "completed"
    }
  ],
  "tool_calls": [
    {
      "call_id": "call_weather_01",
      "tool_name": "fetch_open_meteo_marine",
      "status": "completed",
      "output": { "wind_speed_knots": 18.5, "wave_height_m": 1.4 }
    }
  ],
  "evidence_summary": {
    "sea_state_code": 3,
    "hazard_level": "LOW"
  }
}
```

---

### 3.4. Agent Management (`/api/admin/agents`)

#### 1. List Agent Configurations (`GET /api/admin/agents`)
#### Response (HTTP 200 OK):
```json
{
  "agents": [
    {
      "id": "weather",
      "name": "Weather Agent",
      "endpoint": "/api/agents/weather/analyze",
      "is_enabled": true,
      "timeout_ms": 25000,
      "model_routing": "deepseek-r1-marine",
      "cache_ttl_seconds": 300
    },
    {
      "id": "ocean",
      "name": "Ocean Agent",
      "endpoint": "/api/agents/ocean/analyze",
      "is_enabled": true,
      "timeout_ms": 25000,
      "model_routing": "deepseek-r1-marine",
      "cache_ttl_seconds": 300
    },
    {
      "id": "fishing_zone",
      "name": "Fishing Zone Agent",
      "endpoint": "/api/agents/fishing-zone/analyze",
      "is_enabled": true,
      "timeout_ms": 25000,
      "model_routing": "llama-3.3-70b-maritime",
      "cache_ttl_seconds": 600
    },
    {
      "id": "route",
      "name": "Route Agent",
      "endpoint": "/api/agents/route/analyze",
      "is_enabled": true,
      "timeout_ms": 25000,
      "model_routing": "deterministic-geodesic",
      "cache_ttl_seconds": 1800
    },
    {
      "id": "safety_risk",
      "name": "Safety/Risk Agent",
      "endpoint": "/api/agents/safety-risk/analyze",
      "is_enabled": true,
      "timeout_ms": 25000,
      "model_routing": "deepseek-r1-marine",
      "cache_ttl_seconds": 120
    },
    {
      "id": "orchestrator",
      "name": "Orchestrator Agent",
      "endpoint": "/api/agents/orchestrator/analyze",
      "is_enabled": true,
      "timeout_ms": 40000,
      "model_routing": "deepseek-r1-marine",
      "cache_ttl_seconds": 0
    },
    {
      "id": "assistant",
      "name": "AI Workspace Assistant",
      "endpoint": "/api/agents/assistant/chat",
      "is_enabled": true,
      "timeout_ms": 35000,
      "model_routing": "gpt-4o-ocean-reasoning",
      "cache_ttl_seconds": 0
    }
  ]
}
```

#### 2. Update Agent Configuration (`PATCH /api/admin/agents/{agentId}`)
- **Request Body (JSON):**
```json
{
  "is_enabled": true,
  "timeout_ms": 30000,
  "model_routing": "deepseek-r1-marine",
  "cache_ttl_seconds": 300
}
```
- **Response (HTTP 200 OK):**
```json
{
  "success": true,
  "agentId": "weather",
  "persisted": true
}
```

---

### 3.5. Feature Management (`/api/admin/features`)

#### 1. List Feature Flags (`GET /api/admin/features`)
#### Response (HTTP 200 OK):
```json
{
  "features": [
    {
      "key": "autonomous_tool_execution",
      "name": "Autonomous Diagnostic Tool Execution",
      "is_enabled": false,
      "rollout_percentage": 0,
      "environment": "production"
    },
    {
      "key": "strict_marine_bounding_box",
      "name": "Strict Marine Bounding Box Enforcement",
      "is_enabled": true,
      "rollout_percentage": 100,
      "environment": "production"
    },
    {
      "key": "great_circle_geodesic_routing",
      "name": "Great-Circle Navigational Routing Channel Estimation",
      "is_enabled": true,
      "rollout_percentage": 100,
      "environment": "production"
    },
    {
      "key": "wmo_3700_deterministic_sea_state",
      "name": "WMO 3700 Deterministic Sea State Standard",
      "is_enabled": true,
      "rollout_percentage": 100,
      "environment": "production"
    },
    {
      "key": "artisanal_fisheries_advisories",
      "name": "Artisanal Fisheries Coastal Safety Alerts",
      "is_enabled": true,
      "rollout_percentage": 100,
      "environment": "production"
    },
    {
      "key": "evidence_deduplication_engine",
      "name": "Multi-Agent Evidence Deduplication Engine",
      "is_enabled": true,
      "rollout_percentage": 100,
      "environment": "production"
    }
  ]
}
```

#### 2. Update Feature Flag (`PATCH /api/admin/features/{flagKey}`)
- **Request Body (JSON):**
```json
{
  "is_enabled": true,
  "rollout_percentage": 50,
  "environment": "production"
}
```
- **Response (HTTP 200 OK):**
```json
{
  "success": true,
  "flagKey": "autonomous_tool_execution",
  "persisted": true
}
```

---

### 3.6. Marine Data & API Monitoring (`/api/admin/marine-sources`)

#### 1. List Marine Sources & Quota Telemetry (`GET /api/admin/marine-sources`)
#### Response (HTTP 200 OK):
```json
{
  "providers": [
    {
      "id": "open-meteo",
      "name": "Open-Meteo Marine Weather API",
      "status": "healthy",
      "requests_today": 1420,
      "rate_limit_per_minute": 600,
      "current_minute_usage": 18,
      "average_latency_ms": 185.4,
      "last_probe_timestamp": "2026-10-15T12:00:00Z"
    },
    {
      "id": "copernicus-cmems",
      "name": "Copernicus Marine Environment Service",
      "status": "healthy",
      "requests_today": 340,
      "rate_limit_per_minute": 120,
      "current_minute_usage": 4,
      "average_latency_ms": 420.1,
      "last_probe_timestamp": "2026-10-15T12:00:00Z"
    }
  ]
}
```

---

### 3.7. Security & Audit Logs (`/api/admin/audit-logs`)

#### 1. Retrieve Audit Events (`GET /api/admin/audit-logs`)
- **Query Parameters:**
  - `event_type`: (string, optional) `AUTH_LOGIN`, `ROLE_ELEVATION`, `AGENT_DISPATCH`, `CONFIG_CHANGE`
  - `severity`: (string, optional) `INFO`, `WARNING`, `CRITICAL`, `AUDIT`
  - `limit`: (integer, default: 50)

#### Response (HTTP 200 OK):
```json
{
  "logs": [
    {
      "timestamp": "2026-10-15T12:01:14Z",
      "severity": "AUDIT",
      "event_type": "ROLE_ELEVATION",
      "user_id": "usr_admin_01",
      "actor": "Chief Operations Admin",
      "message": "User usr_researcher_02 role elevated from researcher to oceanographer",
      "ip_address": "192.168.1.10"
    },
    {
      "timestamp": "2026-10-15T11:58:02Z",
      "severity": "INFO",
      "event_type": "AUTH_LOGIN",
      "user_id": "usr_researcher_01",
      "actor": "Dr. Rachel Carson",
      "message": "Successful researcher authentication via JWT",
      "ip_address": "192.168.1.14"
    }
  ],
  "total": 2
}
```

---

### 3.8. Platform Settings & Hazard Thresholds (`/api/admin/settings`)

#### 1. Retrieve Platform Settings (`GET /api/admin/settings`)
#### Response (HTTP 200 OK):
```json
{
  "safety_thresholds": {
    "max_wind_knots": 25.0,
    "max_wave_height_meters": 2.8,
    "reef_buffer_nm": 2.0,
    "monsoon_margin_pct": 15
  },
  "system_defaults": {
    "request_timeout_ms": 25000,
    "default_coordinate_precision": 4,
    "enforce_strict_marine_bounds": true,
    "operational_mode": "standard"
  }
}
```

#### 2. Persist Platform Settings (`PATCH /api/admin/settings`)
- **Request Body (JSON):**
```json
{
  "safety_thresholds": {
    "max_wind_knots": 28.0,
    "max_wave_height_meters": 3.0,
    "reef_buffer_nm": 2.5,
    "monsoon_margin_pct": 20
  },
  "system_defaults": {
    "request_timeout_ms": 30000,
    "default_coordinate_precision": 4,
    "enforce_strict_marine_bounds": true,
    "operational_mode": "high_risk_monsoon"
  }
}
```
- **Response (HTTP 200 OK):**
```json
{
  "success": true,
  "persisted": true,
  "updated_at": "2026-10-15T12:05:00Z"
}
```

---

## 4. Frontend Resilience & Fallback Behavior

The ORCA frontend is fully wired to consume these exact contracts:
1. When endpoints return **HTTP 200 OK**, the interface seamlessly populates live tables, cards, and audit inspectors.
2. When endpoints return **HTTP 404 / 501 / Connection Refused**, the UI renders a non-intrusive `BackendRequiredNotice` detailing:
   - The exact endpoint and HTTP method requested
   - The HTTP status or offline indicator
   - An interactive button launching `ContractSpecModal` with complete cURL commands and JSON schemas
   - A re-check button enabling real-time verification once backend routes are deployed
3. Mutations that fail backend persistence display an explicit warning:  
   *`"Unpersisted Draft Configuration: Backend returned HTTP 404. Setting is held in draft state only and will NOT alter live production behavior until enforced by backend."`*

---

## 5. Recommended Backend Implementation Path (FastAPI)

For backend engineers implementing these endpoints in the ORCA microservice:

```python
from fastapi import APIRouter, Depends, HTTPException, Header, status
from pydantic import BaseModel
from typing import Optional, List

router = APIRouter(prefix="/api/admin", tags=["Super Admin"])

def verify_admin_role(authorization: str = Header(...)):
    token = authorization.replace("Bearer ", "")
    # Validate JWT signature and check role == "admin"
    payload = decode_jwt(token)
    if payload.get("role") != "admin":

        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Admin role required")
    return payload

@router.get("/metrics")
async def get_admin_metrics(user=Depends(verify_admin_role)):
    return {
        "status": "ok",
        "total_registered_users": await count_users(),
        "active_sessions_count": await count_active_sessions(),
        "total_agent_dispatches_24h": await count_dispatches(),
        "avera
        ge_latency_ms": 142.0,
    }
```
