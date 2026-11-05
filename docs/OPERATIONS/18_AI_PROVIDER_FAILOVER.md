# SceneSteward Runbook 18: AI Provider Failover

**Document ID:** `RB-18-AI-FAILOVER`  
**Target Environment:** Staging, Production  
**Audience:** AI Engineers, Backend Developers  

---

## 1. AI Integration Architecture
SceneSteward utilizes AI document extraction and advisory evaluation for documentary release forms:
- **Online Provider (`AI_PROVIDER=anthropic`)**: Anthropic Claude Messages API (`claude-sonnet-4-5`). Formats outputs according to strict JSON schemas.
- **Offline Provider (`AI_PROVIDER=offline`)**: Deterministic local rule engine analyzing 15 canonical categories of consent, evaluating invariants without network connectivity.

---

## 2. Automatic Fallback Behavior
- **Timeout Protection**: Anthropic API requests are bounded by `AI_TIMEOUT_SECONDS=45.0`.
- **Retry Policy**: Maximum 1 retry (`AI_MAX_RETRIES=1`) with backoff to prevent cascading failures.
- **Circuit Breaker / Deterministic Fallback**: If Anthropic API encounters rate limits, HTTP 529 overload, or network failure, extraction workflows fall back safely to deterministic rule evaluation rather than blocking documentary workflows.

---

## 3. Switching AI Provider at Runtime
To temporarily disable external AI calls during upstream API degradation:
1. Update `.env.production`:
   ```bash
   AI_PROVIDER=offline
   ```
2. Reload application processes:
   ```bash
   docker compose -f docker-compose.prod.yml restart api
   ```
3. Verify extraction endpoints continue functioning using deterministic rules.
