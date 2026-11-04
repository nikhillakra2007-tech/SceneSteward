# SceneSteward — Deployment Directory

This directory contains deployment specifications, database role configurations, and environment templates.

## Contents

- `db_roles.sql`: PostgreSQL bootstrap script for provisioning runtime and read-only roles (`scenesteward_app` and `scenesteward_readonly`) with `NOBYPASSRLS`.
- `docker-compose.staging.yml`: Production-like staging multi-container configuration (API, PostgreSQL 18, ClamAV, Worker, Migrations).

## Deployment Instructions

### 1. Database Provisioning
Run `db_roles.sql` against your target PostgreSQL database instance as an administrative user:
```bash
psql "postgresql://admin:password@host:5432/scenesteward" \
     -v app_password="YOUR_SECURE_APP_PASSWORD" \
     -v readonly_password="YOUR_SECURE_RO_PASSWORD" \
     -f deployment/db_roles.sql
```

### 2. Multi-Container Staging Stack
From the project root:
```bash
docker compose --env-file backend/.env.staging -f docker-compose.staging.yml up -d --build
```
