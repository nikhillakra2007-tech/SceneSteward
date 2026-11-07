# SCENESTEWARD — FINAL DEPLOYMENT & REPRODUCIBILITY GUIDE
## Step-by-Step Instructions for Evaluators and Developers

**Date:** 2026-11-07  
**Platform:** Cross-Platform (Windows / Linux / macOS)  

---

## 1. System Requirements

- **Python:** 3.12+ with virtual environment support (`venv`)
- **Node.js:** 18.x or 20.x with `npm`
- **PostgreSQL:** 16+ (Running locally on port 5432 or via Docker)
- **Switch Core:** Switch Core native server or Switch Console

---

## 2. Environment Configuration

Copy the sample environment variables:
```bash
cp .env.example .env
```

Key environment settings:
```ini
# Backend API
BACKEND_HOST=127.0.0.1
BACKEND_PORT=8000
DATABASE_URL=postgresql://postgres:postgres@localhost:5432/scenesteward
JWT_SECRET=supersecret-demo-jwt-key-2026

# Switch Platform
SWITCH_BASE_URL=http://localhost:64432
SWITCH_REGISTRATION_TOKEN=op5x3bTAK7kx007-zgN68Dx9y48e78Hk
SWITCH_AGENT_ID=adf16e2a-4ce2-4598-baa7-ca8865ca4308
SWITCH_AGENT_API_KEY=IYaYTuAw1OU_SdPuUEEUqDPJ4fJp2WJjmysz5Gv-F1c
SWITCH_ROOM_ID=aeec10b9-781c-4625-a07a-692279393943

# Frontend
NEXT_PUBLIC_API_URL=http://localhost:8000
```

---

## 3. Quickstart: 4 Commands to Run Everything

### Step 1: Install Dependencies
```bash
# Backend dependencies
python -m venv backend/.venv
backend/.venv/bin/pip install -r backend/requirements.txt

# Frontend dependencies
cd frontend && npm install && cd ..
```

### Step 2: Initialize Database
```bash
# Run PostgreSQL migrations
backend/.venv/bin/alembic -c backend/alembic.ini upgrade head

# Seed initial documentary personas and test project
python backend/scripts/seed_database.py
```

### Step 3: Start Services
```bash
# Terminal 1 — Start SceneSteward FastAPI Backend:
python -m uvicorn app.main:app --app-dir backend --host 127.0.0.1 --port 8000

# Terminal 2 — Start SceneSteward Next.js Frontend:
npm --prefix frontend start

# Terminal 3 — Verify Switch Core Connection:
python scratch/verify_actual_switch_connection.py
```

### Step 4: Run Automated Tests
```bash
# Backend test suite (310 tests)
backend/.venv/bin/pytest backend/tests/ -k "not test_real_antigravity_acp_binary_handshake"

# Frontend Playwright E2E tests (14 journeys)
cd frontend && npx playwright test
```

---

## 4. Verification Checkpoints

1. **SceneSteward Web UI:** Open [http://localhost:3000](http://localhost:3000). You can immediately log in as `olivia@documentary.org` or click "Olivia (Director)" from the persona switcher.
2. **FastAPI Health & Swagger:** Open [http://localhost:8000/docs](http://localhost:8000/docs) to view full interactive OpenAPI documentation.
3. **Switch Core Status:** Open [http://localhost:64432/health](http://localhost:64432/health) to confirm Switch Core returns `{"status": "ok"}`.

