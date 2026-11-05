# 09. Container and Infrastructure Security

## Container Build Security

### 1. Build Context Hardening (`.dockerignore`)
The root `.dockerignore` was updated to explicitly exclude frontend artifacts, dependencies, and environment files:
```dockerignore
frontend
node_modules
**/node_modules
.next
**/.next
*.log
.git
.github
docs
```
**Benefits**:
- Drastically reduces Docker build context transfer size.
- Eliminates the risk of leaking local secrets, build caches, or node modules into the backend image layers.
- Prevents cache invalidation caused by uncommitted frontend edits.

### 2. Runtime Isolation & Privilege Dropping
- Backend `Dockerfile` uses non-root execution:
  ```dockerfile
  RUN groupadd -g 10001 scenesteward && \
      useradd -u 10001 -g scenesteward -s /bin/false scenesteward
  USER scenesteward:scenesteward
  ```
- No elevated capabilities (`CAP_SYS_ADMIN`) are requested or required.
- Staging and production configurations mandate separate networks for data and ingress tiers (`backend_net`, `data_net`).
