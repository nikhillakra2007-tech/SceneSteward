# SCENESTEWARD — FINAL DEMONSTRATION & JUDGING GUIDE

**Project:** SceneSteward — Documentary Ethics, Participant Agency & Clearance Platform  
**Target Audience:** Hackathon Judges, Documentary Filmmakers, Legal Counsel  
**Time Required:** 5–7 minutes  
**Live Site:** https://scenesteward.vercel.app  
**Local Test Environment:** `http://localhost:3000` (Frontend) & `http://localhost:8000` (FastAPI)  

---

## 1. The Core Problem & Value Proposition (30 Seconds)

> *"In documentary filmmaking, trust is everything. But productions often rely on paper release forms signed years before release. When a project goes to a streaming platform, or creates marketing trailers, or explores generative AI voice dubbing, who checks whether the participant agreed to that specific use?*  
> *SceneSteward solves this: **Silence is never agreement. Consent given for an interview does not travel to synthetic likeness or marketing.** And no AI model can approve footage clearance without a human signing their name to the record."*

---

## 2. Step-by-Step Demonstration Walkthrough

### Step 1: Open the Application & Authenticate as Director
1. Navigate to `http://localhost:3000` (or `https://scenesteward.vercel.app`).
2. Point out the editorial documentary ledger aesthetic: Fraunces display typography, warm brass and slate palette, and the clear statement of non-negotiable principles.
3. Click the **Key icon** in the top navigation bar.
4. Select **Olivia Director** (`olivia@example.com`) to sign in instantly via JWT session token.

### Step 2: Explore the Projects Workspace
1. Click **Projects** in the navigation bar (`/projects`).
2. Show the active documentary project: **"Voices of the Watershed"** (or create a new project via the `+ New Project` button).
3. Click on the project title to enter the **Project Workspace** (`/projects/[id]`).

### Step 3: Roster of Participants & Transparency Tokens
1. Click the **Participants** tab.
2. Observe participant **Dr. Miriam Kalu (fictional)**.
3. Highlight that every participant has an assigned preferred language, preferred communication channel, and a unique cryptographic portal access token.

### Step 4: The 15 Canonical Consent Categories & Non-Transitive Invariants
1. Click the **Consent Records** tab.
2. Show that consent is not a binary yes/no checkbox. It is tracked across **15 distinct canonical categories**:
   - `interview_recording`: **Agreed**
   - `documentary_appearance`: **Agreed**
   - `promotional_clips`: **Needs Clarification**
   - `voice_cloning`: **Declined**
   - `synthetic_likeness`: **Declined**
   - `new_story_context`: **Not Discussed**
3. Highlight the core invariant: **"Silence is never consent. An interview is not permission for a synthetic voice."**

### Step 5: Proposed Footage Use & AI Comparison Engine
1. Click the **Proposed Uses** tab.
2. Select or propose a use: **"Festival Promotional Trailer & Social Teaser"**.
3. Point out that the automated comparison engine flagged that `voice_cloning` is declined and `promotional_clips` requires participant discussion.

### Step 6: Mandatory Human Review Gate (AI is Advisory Only)
1. Click the **Human Reviews** tab.
2. Show the pending review in queue.
3. Note the explicit banner: **"Human Authority Gate: AI recommendations are advisory only. A written rationale is mandatory."**
4. Click **Record Human Decision**.
5. Note that the decision buttons remain disabled until you type a written rationale.
6. Enter: *"Approved for film festival submission; voice cloning strictly prohibited per participant decline."*
7. Click **Needs Discussion** or **Approve with Conditions**.
8. Notice the decision immediately commits to the permanent record. Duplicate decisions are rejected by the backend state machine.

### Step 7: Immutable Audit History
1. Click the **Audit Timeline** tab.
2. Point out the chronological ledger of actions (`review.human_decision`, `consent.confirmed`, `participant.registered`).
3. Explain that every entry is cryptographically linked with SHA-256 hashes to guarantee tamper detection.

### Step 8: The Participant Transparency Portal (Bilingual English / Hindi)
1. Open a new browser tab and navigate to `/participant/[sample-id]` (accessible via the "Open Portal" link in the participants tab).
2. Show the dignity guarantee banner.
3. Click **हिन्दी** in the top-right corner:
   - Notice the entire interface, including all 15 categories, switches into respectful Hindi (`अहस्तांतरणीय सहमति गारंटी`, `आवाज क्लोनिंग`, `सिंथेटिक समानता`).
4. Click **Formal Consent Withdrawal**:
   - Demonstrate the subject's agency to withdraw consent at any time before picture lock with an immediate notification dispatch to the production care team.

### Step 9: Live Switch Collaboration Workflow
1. Open the local **Switch Console** connected to port 64432.
2. Navigate to the room **SceneSteward — Footage Clearance**.
3. Send the clearance query:
   ```text
   @scenesteward-clearance Check clearance for Dr. Miriam Kalu for the upcoming theatrical festival trailer.
   ```
4. The SceneSteward Clearance Agent evaluates the 15 categories live, highlights boundary conditions, and routes the action back to the human review gate in SceneSteward.

---

## 3. Key Takeaways for Judges

1. **Genuinely Full-Stack**: Real FastAPI backend, real PostgreSQL 18 with RLS, real Next.js 14 frontend, real Switch Core integration.
2. **Zero Fake Data Invariants**: All status badges and reviews reflect verified database state.
3. **Ethical Innovation**: Translates complex legal and ethical dilemmas into automated non-transitive protections with mandatory human accountability.
