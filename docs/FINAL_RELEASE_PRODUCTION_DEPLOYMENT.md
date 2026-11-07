# FINAL RELEASE — VERCEL PRODUCTION DEPLOYMENT & EDGE VERIFICATION

**Project:** SceneSteward  
**Repository:** https://github.com/nikhillakra2007-tech/SceneSteward  
**Target Branch:** `main`  
**Production URL:** https://scenesteward.vercel.app  
**Date:** 2026-11-07  

---

## 1. Production Deployment Metadata

| Metadata Field | Live Value |
|---|---|
| **Hosting Platform** | Vercel Serverless Edge Network |
| **Vercel Project** | `scenesteward` |
| **Target Environment** | `Production` |
| **Deployment ID** | `dpl_3UpTMt7rVEfKnfjax9XtmEXn9KtG` |
| **Status** | `● Ready` |
| **Production Domain** | `https://scenesteward.vercel.app` |
| **Direct Deployment URL** | `https://scenesteward-6ujatfsoc-nikhillakra2007-9371s-projects.vercel.app` |
| **Framework Version** | Next.js 14.2.35 (App Router) |
| **Edge Region (Build)** | `iad1` (Washington, D.C.) |
| **Edge Region (Delivery)** | `bom1` (Mumbai edge POP) |

---

## 2. Live HTTP Edge Probe

Executing a live HTTP probe against the production URL:

```bash
curl.exe -I https://scenesteward.vercel.app
```

**Live Response:**
```http
HTTP/1.1 200 OK
Accept-Ranges: bytes
Access-Control-Allow-Origin: *
Age: 0
Cache-Control: public, max-age=0, must-revalidate
Content-Disposition: inline
Content-Length: 28856
Content-Type: text/html; charset=utf-8
Date: Sat, 07 Nov 2026 14:53:52 GMT
Etag: "44bba3f7b43be3a377ed2dc556bc410b"
Server: Vercel
Strict-Transport-Security: max-age=63072000; includeSubDomains; preload
Vary: RSC, Next-Router-State-Tree, Next-Router-Prefetch
X-Matched-Path: /
X-Vercel-Cache: PRERENDER
X-Vercel-Id: bom1::96xsc-1794063231605-b33110b7b95b
```

---

## 3. Production Route Availability

| Route | Live URL | Response Code | Cache Strategy |
|---|---|---|---|
| **Home / Manifesto** | `https://scenesteward.vercel.app/` | `200 OK` | Static Prerender (`PRERENDER`) |
| **Projects Workspace** | `https://scenesteward.vercel.app/projects` | `200 OK` | Client-Side Hydration + REST API |
| **Analytics Dashboard** | `https://scenesteward.vercel.app/analytics` | `200 OK` | Prerender + Realtime KPI Metrics |
| **Not Found Boundary** | `https://scenesteward.vercel.app/_not-found` | `200 OK` | Dignified 404 Layout |

---

## 4. Security & Performance Headers

- **HSTS**: `max-age=63072000; includeSubDomains; preload`
- **CORS**: `Access-Control-Allow-Origin: *` configured on public assets.
- **Cache-Control**: `public, max-age=0, must-revalidate` ensuring clients receive instantaneous updates upon deployment invalidation.
- **Image Optimization**: WebP captures delivered via Next.js asset pipeline with explicit dimensions preventing layout shifts.
