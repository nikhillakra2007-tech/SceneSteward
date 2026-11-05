# SceneSteward — Final Master Architecture Report

**Date:** November 2026  
**Auditor:** Principal Software Architect & Infrastructure Lead  
**Repository:** `nikhillakra2007-tech/SceneSteward`  

---

## 1. System Topology Overview

SceneSteward is architected as an asynchronous, event-driven, multi-tenant documentary consent platform. It features a hardened separation of concerns across presentation, API routing, business logic, persistence, and worker execution.

```
                             +-------------------------+
                             |   Next.js 14 Frontend   |
                             | (Participant & Staff UI)|
                             +------------+------------+
                                          |
                                    HTTPS / WSS
                                          |
                                          v
+-----------------------------------------------------------------------------------+
|                            FastAPI Application Gateway                            |
|                                                                                   |
|  [Rate Limiter] ---> [Auth / HMAC Verifier] ---> [Tenant & RLS Scope Injector]    |
|                                 |                                                 |
|                                 v                                                 |
|     +---------------------------+---------------------------+                     |
|     |                           |                           |                     |
|  [Projects & Members]    [Consent Engine]       [Document Intelligence]           |
|     |                           |                           |                     |
|     | (15 Categories)           | (Advisory Gate)           | (Prompt Defense)    |
|     v                           v                           v                     |
|  [Event Bus]             [Human Reviews]        [Storage / Antivirus]             |
+-----+---------------------------+---------------------------+---------------------+
      |                           |                           |
      |                           v                           |
      |             +---------------------------+             |
      +------------>| PostgreSQL 18 + RLS + HMAC|             |
      |             | (20 Tables, 212 Triggers) |             |
      |             +---------------------------+             |
      |                           ^                           |
      |                           |                           |
      v                           |                           v
+---------------------------+     |               +-----------------------+
|  Outbox Worker (Async)    |-----+               | ClamAV Antivirus Daemon|
|  (Transactional Dispatch) |                     +-----------------------+
+---------------------------+
```

---

## 2. Component Architecture

### 2.1 FastAPI Application Engine
- ASGI asynchronous web framework executing under Python 3.12 with Uvicorn.
- Dependency injection architecture for database sessions, authenticated users, tenant memberships, and pagination.
- Cryptographic session establishment: every database session initiates an HMAC-SHA256 signature to set `app.user_id` and `app.is_system`.

### 2.2 Next.js 14 Frontend Client
- Production App Router application built on React 18 and Tailwind CSS.
- Strongly typed TypeScript API client (`frontend/src/lib/api.ts`) synchronized with backend Pydantic schemas.
- Participant Transparency Portal with bilingual localization (English / Hindi), real-time consent badge visualizers, and direct withdrawal workflows.

### 2.3 PostgreSQL 18 & Row-Level Security
- 20 relational tables managing projects, memberships, participants, release documents, consent records, proposed uses, and immutable audit logs.
- RLS enabled across 18 project-scoped tables, ensuring tenant data separation at the database engine level.
- Composite foreign keys `(project_id, participant_id)` guaranteeing zero cross-project leakage.

### 2.4 Document Intelligence & Adversarial Resistance
- Multi-page document parser supporting PDF, TXT, MD, and DOCX containers.
- Sanitization pipeline neutralizing prompt injection attempts, smuggled zero-width characters, and role-impersonation delimiters.
- Fine-grained clause detection mapping 15 canonical categories with line numbers, page numbers, and quoted snippets.
- Advisory architecture: all findings must be confirmed by human reviewers before taking legal or workflow effect.

### 2.5 Event Bus & Outbox Worker
- Transactional event publishing logging all domain mutations to `audit_events` and `outbox_events`.
- Asynchronous worker process polling events with exponential backoff and dead-letter handling.
