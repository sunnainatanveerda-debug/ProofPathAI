---
doc: checklist
status: approved
---

# Build Checklist

Build mode: learn (default for a beginner; explain each slice and pause for the learner check)

## Slices

- [x] **1. Core form and editable sample data**
  Becomes usable: A local home page leads to one editable form, with sample values and server-side validation for the required job description.
  Why now: Establishes the first runnable behavior and confirms the user can supply the information before connecting an external service.
  PRD ref: `prd.md > Home`, `prd.md > Guided input form`, `prd.md > Internship input and sample demo`
  Spec ref: `spec.md > Components > Home and input form`, `spec.md > File Structure`, `spec.md > Small build stages and checkpoints`
  Build: Completed. Added the Flask home/form, editable sample values, responsive styles, setup notes, and basic server-side validation.
  Verify (mechanical): Completed smoke checks for home, sample prefill, invalid-input preservation, and valid-length submission; Python compilation and `git diff --check` passed.
  Learner check: Completed. The learner confirmed that the homepage, sample prefill/editing, short-description warning, and preservation of other entries all worked.
  Commit: No commit or staging, per the learner's explicit instruction.

- [x] **2. Groq integration and response validation**
  Becomes usable: A valid form submission makes one request to the approved Groq Free plan model, validates the complete structured response, and reports a clear success or failure without presenting unvalidated analysis.
  Why now: This checks the project's central AI-service risk before building the detailed results interface. It keeps the approved model and free-tier constraints visible and testable.
  PRD ref: `prd.md > Requirements and skill-by-skill evidence assessment`, `prd.md > Seven-day portfolio plan`, `prd.md > States and Boundaries`
  Spec ref: `spec.md > Components > Analysis route and Groq client`, `spec.md > Components > Pydantic response validation`, `spec.md > External Services and Dependencies > GroqCloud inference API`, `spec.md > External Services and Dependencies > Structured result contract`, `spec.md > Important Failure Modes`, `spec.md > Small build stages and checkpoints`
  Build: Implemented `ai_service.py` for one Groq SDK call using only `openai/gpt-oss-20b`, strict JSON output, a 60-second timeout, and `max_retries=0`; added `models.py` with Pydantic schemas and consistency checks; updated `app.py` to load the local key, call the service, map failures, and add the separate sample-report route; added placeholder-only `.env.example`; extended `requirements.txt`; updated `README.md` with local key setup and privacy guidance; updated the existing form to preserve entries, show safe errors, offer a manual retry, and link to the separate sample report. The sample is never substituted for the user's analysis. The personalized results page remains Stage 3.
  Verify (mechanical): Python compilation and `pip check` passed. Flask test-client checks passed for home/sample form, short-input preservation, missing-key handling, invalid-response handling, and success confirmation without exposing result content. Pydantic checks accepted a valid shape and rejected an unordered plan and claim-only evidence. A mocked Groq client confirmed the selected model, strict schema, 60-second timeout, one request, and disabled retries; malformed JSON, a rate limit, and a timeout each failed safely. The local server started and returned HTTP 200 for `/` and `/sample-report`. `.env` remains ignored and absent; `.env.example` uses the existing allowed exception. The learner confirmed that a real Groq response passed structure and consistency checks. No paid service or model was used.
  Learner check: Completed per learner confirmation: a real Groq response passed the required structure and consistency checks. No key was shared.
  Commit: No staging or commit, per the learner's explicit instruction.

- [ ] **3. Results and seven-day plan reveal**
  Becomes usable: The validated assessment appears first; the existing seven-day plan and final report can be revealed below it on the same page.
  Why now: Once the AI response is trustworthy enough to accept structurally, the app can present its content in the approved user journey.
  PRD ref: `prd.md > Results page`, `prd.md > Requirements and skill-by-skill evidence assessment`, `prd.md > Seven-day portfolio plan`, `prd.md > Final report and download`
  Spec ref: `spec.md > Components > Results page and plan reveal`, `spec.md > Look and Feel`
  Build: Implemented `templates/results.html` and render only a Pydantic-revalidated result. The page shows the role overview, evidence counts, explicit/preferred/inferred requirements, per-skill examples/gaps/next steps, and the exact claimed-skill label. The seven-day plan and final report use the same result object and reveal accessibly on the same page; the separate sample page has the exact disclaimer.
  Verify (mechanical): Offline tests cover successful assessment rendering, evidence categories and relationships in the UI, all seven ordered plan days, hidden-by-default reveal, no second analysis request, rejection of a constructed invalid model, sample disclaimer, and existing error form-value preservation. Full test suite and Python compilation passed. Learner browser check remains pending.
  Learner check: Open a successful sample analysis, review the assessment, reveal the plan, and report anything confusing or missing.
  Commit: No staging or commit, per the learner's explicit instruction.

- [ ] **4. On-demand Markdown download**
  Becomes usable: The learner can download the current validated result as a readable Markdown report generated in memory.
  Why now: The report is derived from the already displayed result, so the complete assessment and plan need to exist before adding download behavior.
  PRD ref: `prd.md > Final report and download`
  Spec ref: `spec.md > Components > Final report and Markdown download`, `spec.md > Data Model > Where information goes and what happens after navigation`
  Build: Add the report formatter and signed result form submission; recheck signature and Pydantic data before sending an in-memory attachment.
  Verify (mechanical): Confirm a valid download contains all required report sections; modify the submitted payload and signature and confirm Flask returns no report file.
  Learner check: Download a report, open it in a text editor, and confirm its headings and content are readable.
  Commit: No staging or commit, per the learner's explicit instruction.

- [ ] **5. Error, sample fallback, and accessibility review**
  Becomes usable: The complete local demo handles its approved failure and sample paths clearly and can be used with keyboard and assistive technology basics.
  Why now: This final pass checks the integrated experience, including the separately labeled sample report, after its real result and download flows are in place.
  PRD ref: `prd.md > States and Boundaries`, `prd.md > Look and Feel`, `prd.md > Final report and download`
  Spec ref: `spec.md > Labeled sample report`, `spec.md > Important Failure Modes`, `spec.md > Working-Demo Acceptance Checks`, `spec.md > Look and Feel`, `spec.md > Small build stages and checkpoints`
  Build: Finish the separate prewritten sample report and its clear label; review retry/error messages and form preservation; check keyboard operation, focus, heading order, labels, contrast, evidence text labels, and plan-reveal announcements.
  Verify (mechanical): Walk through missing-key, rate-limit, timeout, unavailable-service, invalid-response, and sample-report paths; confirm the sample is never presented as the learner's analysis; complete a keyboard and responsive-layout review.
  Learner check: Explore the complete app, use the keyboard for the main workflow, inspect the separately labeled demo example, and report any final corrections.
  Commit: No staging or commit, per the learner's explicit instruction.

## Hands-on Checkpoints

- [x] Early usable behavior explored — Stage 1 home page and editable form; learner completed and confirmed manual checks.
- [x] Stage 2 Groq integration and response validation explored — the learner confirmed a real response passed structure and consistency checks.
- [ ] Final kick-the-tires exploration and feedback completed.

## Final Review

- [ ] Final review complete — feedback resolved and learner confirms ready to ship.

## Code Tour and App Map

- [ ] Learning activity complete — guided route, focused alternative, prior practice connected, or brief recap.
- [ ] Optional edit and transfer reflection addressed — offered/declined/already covered/not applicable as appropriate.
- [ ] `devpost/app-map.html` generated from finished code, checked, and shown, including a project-grounded practice to reuse.

Activity and evidence: Stage 1 manual check and Stage 2 successful live response confirmed by learner; Stage 3 browser check and final review remain incomplete.
Route and stops: Not started.
Edit outcome: Not started.
Reflection: Not offered yet.
Activity mode: Learn mode planned; no code tour has happened.

## Revisions
