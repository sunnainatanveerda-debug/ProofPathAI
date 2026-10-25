---
doc: spec
status: approved
---

# ProofPath AI — Technical Specification

## How This Works, In Plain Language

ProofPath AI runs on your computer. Flask is a small Python web server: it serves the pages, accepts the form, sends one analysis request to Groq, checks the answer, and prepares the report download. The browser displays HTML pages styled with CSS. A small JavaScript file reveals the plan without asking Groq again.

The Groq key stays in a local `.env` file and is read only by Python. The job description, skills, and project examples are sent from Python to Groq after the user sees a privacy notice and submits the form. ProofPath AI does not save the inputs or results in a database or persistent application history. The result stays in the current browser page until the user leaves or refreshes it. Groq is still an external service that processes the submitted text.

The model returns structured JSON, which is data arranged in a predictable format. Pydantic checks that the fields and values match the app's rules. These checks can catch missing fields, invalid evidence labels, and a plan with the wrong number of days. They cannot prove that the model understood the job description correctly, so the app never describes the assessment as verified.

This is a local proof of concept: one Flask app, one external AI service, no accounts, no database, no background jobs, and no deployment requirement. It keeps the product's main idea—connecting job requirements to user-described evidence—while keeping setup manageable for a beginner.

## The Core Journey Through the System

Implements `prd.md > The Core Journey`.

```text
Browser                         Flask / Python                         Groq
   |                                  |                                  |
   | Open home page                   |                                  |
   |--------------------------------->| Render home and input form       |
   |                                  |                                  |
   | Submit JD + optional details     |                                  |
   |--------------------------------->| Validate JD; check API key       |
   |                                  | Show error if missing            |
   |                                  |                                  |
   |                                  | Send one structured request      |
   |                                  |--------------------------------->|
   |                                  | Assessment + 7 plan days         |
   |                                  |<---------------------------------|
   |                                  | Parse and validate with Pydantic  |
   |                                  | Reject invalid or incomplete data|
   | Results: summary + assessment   |                                  |
   |<---------------------------------|                                  |
   | Click plan action; JS reveals   | No additional request            |
   | plan and report below it        |                                  |
   |                                  |                                  |
   | Click Download Report           |                                  |
   |--------------------------------->| Revalidate current result data;  |
   | Download Markdown attachment   | build and return it in memory    |
   |<---------------------------------| No disk/database save             |
```

The sample internship button fills the same form with example information. If the live call fails, the app shows an error and a separate link to a prewritten sample report labeled **“Demo example — not based on your inputs.”** It never presents that sample as a personalized result.

## Stack

Versions below were checked against the maintainers' documentation on 2026-10-21. The build should use these versions or a compatible patch release; recheck Groq model availability and free-tier eligibility before recording the demo.

| Tool | Role in ProofPath AI | Why it fits |
|---|---|---|
| Python 3.11 or newer | Runs the application and analysis logic | One beginner-friendly language handles the server, Groq call, validation, and Markdown generation. |
| Flask 3.1.3 | Local web server and page routes | Small framework with templates and a built-in local development server. |
| HTML and Jinja templates | Page structure and server-rendered results | Keeps the workflow readable and lets Flask render the same validated analysis into the page. Jinja escapes normal template values by default. |
| CSS | Responsive layout, navy/teal palette, evidence labels | Direct control over the approved visual design without a front-end build tool. |
| JavaScript (browser built-in) | Reveals the already-generated plan and report | One small script; no separate JavaScript package is needed. |
| Groq Python library 1.7.0 | Sends the request to Groq from Python | Official client library; the key stays on the server. |
| Pydantic 2.14.1 | Checks AI response fields, values, and cross-field rules | Converts untrusted JSON into a typed Python object and rejects invalid data. |
| python-dotenv 1.2.4 | Loads local values from `.env` during development | Keeps the API key out of source code and browser code. |
| Python `venv` and `requirements.txt` | Isolates and records dependencies | `venv` is built into Python; installing this app's libraries will not change other projects. |
| Python standard library (`hmac`, `hashlib`, `secrets`, `json`, `io`) | Signs the current result payload and prepares the download in memory | Avoids another package for tamper checks and file delivery. |

No React, database, PDF renderer, authentication package, logging service, or deployment platform is needed for this demo. Flask includes its template engine and the Python standard library provides the Markdown text and in-memory download response, so these do not require separate packages.

Documentation:

- [Python `venv`](https://docs.python.org/3/library/venv.html)
- [Flask 3.1 Quickstart](https://flask.palletsprojects.com/en/stable/quickstart/)
- [Flask templates and autoescaping](https://flask.palletsprojects.com/en/stable/templating/)
- [Groq Python library](https://console.groq.com/docs/libraries)
- [Groq Structured Outputs](https://console.groq.com/docs/structured-outputs)
- [Pydantic models](https://docs.pydantic.dev/latest/concepts/models/)
- [python-dotenv](https://pypi.org/project/python-dotenv/)
- [Flask 3.1.3 on PyPI](https://pypi.org/project/Flask/3.1.3/)
- [Groq Python library 1.7.0 on PyPI](https://pypi.org/project/groq/1.7.0/)
- [Pydantic 2.14.1 on PyPI](https://pypi.org/project/pydantic/2.14.1/)
- [python-dotenv 1.2.4 on PyPI](https://pypi.org/project/python-dotenv/1.2.4/)

`requirements.txt` should contain only these runtime packages, pinned to the versions checked above:

```text
Flask==3.1.3
groq==1.7.0
pydantic==2.14.1
python-dotenv==1.2.4
```

These four releases are published on PyPI. Their package metadata supports Python 3.11: Flask requires Python 3.9+, and Groq 1.7.0, Pydantic 2.14.1, and python-dotenv 1.2.4 require Python 3.10+. The SDK's documented `client.chat.completions.create(...)` call remains the API shape used here. Resolve and install these pins together in the project `.venv` during the first build stage; if the resolver reports a conflict, stop and choose compatible free versions before implementing the AI call. Do not change the app to use an unapproved paid service or plan.

## Where It Runs and How Someone Tries It

### Local runtime

The app runs at `http://127.0.0.1:5000/` on the learner's Windows computer. The Flask development server listens on the local computer only. This is suitable for building and recording the required demo; it is not a production server. The local debug mode stays off when recording or sharing the computer.

The AI analysis requires a Groq developer account, an API key, and free-tier availability for the selected model. Groq's current services agreement requires the account holder to be at least 18. No paid subscription or payment method should be needed or enabled for development or demo use. If free access is unavailable or its limits are reached, the app reports the issue and can show only the separately labeled sample report.

### Windows Command Prompt setup

The build should put these steps in `README.md` and keep them accurate:

1. Install Python 3.11 or newer and confirm `py --version` works in Command Prompt.
2. Open Command Prompt in the project folder.
3. Create the project-local environment:

   ```bat
   py -3.11 -m venv .venv
   ```

4. Activate it:

   ```bat
   .venv\Scripts\activate.bat
   ```

   The prompt should begin with `(.venv)`.

5. Install only the dependencies listed by the project:

   ```bat
   python -m pip install --upgrade pip
   pip install -r requirements.txt
   ```

6. Make a private local key file and edit it:

   ```bat
   copy .env.example .env
   notepad .env
   ```

   Replace the placeholder with the Groq API key. Do not paste the key into source code, chat, screenshots, or the public repository. `.env.example` contains a placeholder only.

   The tracked `.env.example` should contain only:

   ```text
   GROQ_API_KEY=your_groq_api_key_here
   ```

7. Start the local app:

   ```bat
   flask --app app run
   ```

8. Open `http://127.0.0.1:5000/` in a browser. Stop the server with `Ctrl+C` in Command Prompt. To leave the environment, enter `deactivate`.

### Verify the setup and troubleshoot

The README should explain these beginner checks:

- The home page loads at the local address. If the terminal says port 5000 is already in use, stop the other local Flask process or use the alternate port documented in the README.
- Try the form with the sample internship and a configured free-tier key; a successful response shows the overview and assessment, then reveals seven plan days and the final report.
- Test the missing-key message by removing or blanking the local key, then restart the app. Do not print the key to check it.
- If `py` is not recognized, install Python with the Windows launcher enabled or use the installed `python` command in the documented venv steps.
- If `No module named ...` appears, confirm `(.venv)` is visible and run `pip install -r requirements.txt` again.
- If the API reports authentication, quota/rate-limit, network, timeout, or model-availability errors, keep the user's form filled, show the corresponding friendly message, and offer manual retry plus the separate sample report.
- A user can return to the form and retry. No automatic retry occurs.

The local setup instructions are also what the learner needs to record the required demo video. Public GitHub publication is part of the later hackathon ship stage; before publishing, confirm `.env` and `.venv/` are ignored and that the real key is absent from tracked files and screenshots. Online deployment is optional and deferred until the local app is complete and reviewed.

## Look and Feel

Implements `prd.md > Look and Feel`, `prd.md > Internship input and sample demo`, and `prd.md > Results page`.

- Use deep navy for headings and high-priority actions, teal for primary highlights, and white or light gray for the page background.
- Use a readable sans-serif system font, clear heading levels, a centered content column, generous spacing, and cards for the assessment and seven plan days.
- Keep evidence labels visible in text: **Evidence provided**, **Partial evidence**, and **Evidence not provided**. Color may reinforce a label but never replace it; ensure readable contrast.
- Show the home page headline, description, three-step explanation, **Analyze an Internship**, and **Try Sample Data Analyst Internship** actions.
- On the form, show clear field labels, example guidance, the required job-description marker, optional markers for skills/projects, and the Groq privacy disclosure before submission.
- On results, keep a readable overview and skill cards/table, with role, requirement type, evidence category, supporting example or its absence, missing details, and next step. Place the seven-day plan and final report below the assessment in the approved order.
- Use a visible loading message during the request and inline error/empty states. The loading copy should say that the app is analyzing the supplied text; it must not imply independent verification.
- Use keyboard-operable native form controls and clear focus styles. The plan reveal action must be keyboard accessible and announce its expanded state to assistive technology.
- Keep animation minimal. No charts are needed; evidence-category counts are optional and, if shown, count only categories.

## Components

### Home and input form

Renders the home page and same guided form. The sample action fills the editable job description, skills, and project fields. The form includes a notice that the submitted job description, skills, and project details will be sent to Groq for analysis and advises users not to enter names or confidential information. It explains the assessment is based on supplied information and does not verify actual ability.

The server requires a non-blank, usable job description and rejects obviously short input before making an API call. Skills and projects remain optional. Server-side validation is authoritative; client-side JavaScript may improve feedback but must not be the only validation. Validation and service errors render the form with the submitted text preserved.

Suggested pre-submit notice: “When you submit, your job description, skills, and project/work details will be sent to Groq for AI analysis. Please do not include names or confidential information. ProofPath AI does not save these details, but Groq processes them under its data practices.”

PRD ref: `prd.md > Internship input and sample demo`, `prd.md > States and Boundaries`.

### Analysis route and Groq client

Accepts the form submission, reads the key from process environment loaded from `.env`, sends one Groq request, and passes the reply to response validation. The Groq client must be configured with `max_retries=0` so its built-in automatic retry behavior is disabled. It does not log form content, response content, or the API key. If a key is missing, it does not make a request.

PRD ref: `prd.md > Requirements and skill-by-skill evidence assessment`, `prd.md > Seven-day portfolio plan`, `prd.md > States and Boundaries`.

### Pydantic response validation

Checks the full result before any personalized assessment appears. The result model contains a role summary, a single list of all identified skill assessments, exactly seven ordered plan-day records, and assumptions/limitations. Overview counts and final report summaries are computed in Python from this validated data so the page, report, and download stay consistent.

Each skill record includes: skill name; explicit or inferred requirement type; uncertainty flag and explanation; short basis from the job description; why it matters; evidence category; whether the user reported the skill; supporting project/work example text or blank; missing detail/evidence; practical next step; and priority. Each plan day includes: day number; task; deliverable; targeted evidence gap; why it helps; and completion criterion. User-facing copy must use plain language.

The response's example text must come from the submitted projects/work-examples field. Request a verbatim supporting excerpt in the JSON and check that the normalized excerpt exists in that field. If there is no excerpt, the record cannot be marked Evidence provided. If the user reports the skill but no supporting project/work excerpt is supplied, display the exact label **“Skill claimed — evidence not provided.”** This guards against treating a skill name alone as demonstrated work. The app still cannot establish that an example proves real-world ability; it describes only the submitted text.

Cross-field checks reject missing skill explanations, missing example/missing-evidence handling, missing next steps, unsupported evidence categories, gaps in day numbering, and extra or missing plan days. The single authoritative `skill_assessments` list combines requirement identification with its evidence assessment, so every returned skill has a complete assessment row. The prompt instructs Groq to include every explicit or reasonably inferred requirement. Pydantic cannot independently prove that the model did not overlook a skill in the job description; this is a semantic limitation, not a schema check. An invalid or incomplete response produces a clear error and is never rendered as a successful personalized report.

Pydantic checks schema and selected consistency rules; it cannot guarantee that skills were interpreted correctly or that a generated recommendation is factually sound. Structured JSON and strict schema compliance are not proof of factual correctness. The prompt must instruct the model to use only the description and user examples supplied, disclose uncertainty, avoid invented experience, and never claim to verify ability.

PRD ref: `prd.md > Requirements and skill-by-skill evidence assessment`, `prd.md > Seven-day portfolio plan`, `prd.md > Final report and download`.

### Results page and plan reveal

Renders personalized results only after the whole response has passed validation. The initial view shows the assessment summary and skill-by-skill assessment. The seven-day plan starts hidden. Clicking **Create My 7-Day Portfolio Plan** reveals the already-generated seven days and the final report directly below them, on the same page, without another Groq request or loss of the assessment. The browser JavaScript handles only this reveal and small accessibility improvements.

The plan is one coherent beginner project, with seven sequential tasks and deliverables. When personal context exists, focus on two or three highest-priority evidence gaps. When both skills and projects are blank, label it as a general beginner starting plan based on job requirements. It should not promise mastery in seven days.

PRD ref: `prd.md > Seven-day portfolio plan`, `prd.md > Final report and download`, `prd.md > States and Boundaries`.

### Final report and Markdown download

Builds the final report from the same validated analysis object: role summary, all identified job requirements, evidence-category labels, supporting examples or their absence, prioritized next steps, seven plan days and deliverables, uncertainty, assumptions, and limitations. Strengths may include only skill assessments classified as Evidence provided with a supporting project/work excerpt. The final report must not turn a self-reported skill into a demonstrated strength.

When the user clicks **Download Report**, the results page submits the serialized `AnalysisResult` JSON plus a signature in hidden form fields to Flask's `POST /download` route. The server signs the exact serialized bytes with an HMAC key generated in Python memory when the local app starts. That signing key is separate from `GROQ_API_KEY` and is never sent to the browser; the browser receives only the report JSON and its signature. Flask first checks the signature with a constant-time comparison, then parses and validates the JSON with Pydantic again. If either check fails, it returns a clear error page with no report attachment and a way back to the form. It does not log the submitted payload. For a valid payload, Flask creates a UTF-8 `.md` attachment in memory and sends it to the browser. It makes no Groq request and does not save a database record or persistent server file. The browser does not use local storage. A page left open after the Flask process restarts has a signature from the old process and must be re-analyzed before downloading; no result history is kept. If no valid personalized result is present, do not generate a personalized report; explain how to run an analysis or view the separate sample. The sample report has its own clearly labeled view and download path, and is used only when the user chooses it.

The Markdown includes clear headings, lists, and the required content. It is a simple reliable hackathon format; users can open it in a text editor or Markdown viewer and print it to PDF if they want a PDF copy.

PRD ref: `prd.md > Final report and download`.

### Labeled sample report

Stores a short, prewritten example in a Python data file and renders it using the same page layout and three evidence categories. It includes a complete seven-day plan and the same report sections. Its page heading and downloaded file prominently say **“Demo example — not based on your inputs.”** It contains no user submission and is never substituted into the personalized result route.

PRD ref: `prd.md > Internship input and sample demo`, `prd.md > States and Boundaries`.

## Data Model

There is no database, account, local history, or persistent report file.

### Submitted form data

`AnalysisRequest` is a short-lived Python object created from the POST form:

| Field | Required? | Use |
|---|---|---|
| `job_description` | Yes | Job text sent to Groq after server-side length/usability checks. |
| `current_skills` | No | Self-reported skills; kept separate from project examples. |
| `projects_and_work` | No | User-described examples; the only allowed source for supporting example excerpts. |

When a field is invalid or an API call fails, Flask re-renders the form with these values. They are held in the current request/page only, not written to disk or application history. Leaving or refreshing may lose them.

### Validated AI result

`AnalysisResult` is a Pydantic object held while Flask renders the response. It has:

- `role_title` and concise role/assessment summary.
- `skill_assessments[]` with requirement source, uncertainty, job-description basis, evidence category, claim status, verbatim example excerpt (or blank), missing evidence, next action, and priority.
- `plan_days[]`, numbered 1 through 7, each with task, deliverable, gap targeted, relevance, and completion criterion.
- `assumptions_and_limitations` and a flag/copy for a general plan when personal input is absent.

Category counts and report strengths/gaps are derived from these records in Python. The app does not accept independent AI-generated counts or a separate report summary that could contradict the skill rows.

### Where information goes and what happens after navigation

1. The user enters details in the browser form.
2. On submission, Flask validates the required job description and sends the three text fields to Groq over HTTPS. The app does not log them.
3. Groq returns the model response; Flask validates it fully. The valid result is rendered back into the current page.
4. JavaScript reveals hidden result sections already present in that page; it does not store data in browser local storage or make another AI request.
5. A download click posts the current result payload to Flask. Flask checks it again and returns a Markdown attachment directly. It does not store the report.
6. Refreshing, closing the tab, stopping Flask, or navigating away may lose the result. There is no history to reopen.

User inputs and results are not saved by ProofPath AI to a database or persistent application history. This does not mean no external service processes the text: the job description, skills, and project details are sent to Groq for the requested analysis. The pre-submit disclosure must say this and advise users not to include names or confidential information. Groq's current data documentation says inference data is not retained by default but may be kept temporarily for service reliability or abuse monitoring, up to 30 days; recheck the policy before the demo and do not promise that Groq retains nothing.

## File Structure

The `5-build` stage should create this small, organized tree. Existing `devpost/` planning files remain in place.

```text
ProofPathAI/
├── app.py                    # Flask routes: home, analysis, download, sample report
├── models.py                 # Pydantic request/result models and consistency checks
├── ai_service.py             # Groq request, prompt, error mapping, response parsing
├── report.py                 # Markdown report from validated result; in-memory response
├── sample_data.py            # Editable sample form values and separate static sample report
├── templates/
│   ├── base.html             # Shared page shell, metadata, accessible navigation/footer
│   ├── index.html            # Home page and guided input form
│   ├── results.html          # Assessment, hidden plan, final report, download form
│   └── sample_report.html    # Clearly labeled, prewritten sample report
├── static/
│   ├── styles.css            # Responsive navy/teal visual system and focus states
│   └── app.js                # Reveal plan/report; no AI or key handling
├── devpost/                  # Approved scope, PRD, this spec, learner profile
├── .env.example              # Placeholder only; never a real key
├── .env                      # Local secret; ignored by Git and never committed
├── .gitignore                # Ignore .env, .venv/, Python cache, and local secrets
├── requirements.txt          # Minimal pinned runtime dependencies
└── README.md                 # Windows setup, run, verification, troubleshooting, privacy
```

The `.venv/` folder is generated locally by Python and ignored by Git. It is not hand-written source. The existing root `.gitignore` already excludes `.env` and `.env.*` while allowing `.env.example`; the build must add `.venv/` and ensure the real `.env` remains excluded.

## External Services and Dependencies

### GroqCloud inference API

- **Purpose:** interpret varied job descriptions and generate the complete skill assessment and seven-day plan in one request.
- **Model:** `openai/gpt-oss-20b`, subject to availability and free-tier eligibility at build/demo time.
- **Endpoint:** `POST https://api.groq.com/openai/v1/chat/completions` through the official Python SDK.
- **Authentication:** `GROQ_API_KEY` from the server process environment, loaded from local `.env` for development. Never send it to the browser or include it in logs, screenshots, or the public repository.
- **Request:** one system instruction plus one user message containing the job description, optional self-reported skills, optional project/work examples, the evidence rules, and one JSON Schema response format with `strict: true`. Current Groq documentation lists this model as supporting strict JSON Schema mode. No tools, web search, streaming, or secondary AI call. Set a finite 60-second timeout and configure the SDK client with `max_retries=0`; Groq's Python SDK otherwise retries some errors automatically by default, which would conflict with the approved manual-retry-only behavior.
- **Response:** one JSON object matching the analysis schema below. Parse with JSON/Pydantic; reject refusal, missing content, malformed output, and any cross-field rule violation.
- **Free use:** Groq currently publishes free-tier rate limits for this model. At the time checked, the documentation listed 30 requests/minute, 1,000 requests/day, 8,000 tokens/minute, and 200,000 tokens/day. This confirms that a free tier is publicly documented, but cannot confirm that an individual account is eligible or has quota remaining. Check the learner's account console before the first live request and again before the demo. Limits and eligibility can change. Keep all use within the free tier; do not add a payment method, upgrade to a paid plan, or make background/retry calls. If free access is unavailable or a limit is reached, show an error and offer the separately labeled sample.
- **Cost:** no paid subscription is required for the demo when usage remains within available free-tier limits. Free availability is conditional; the app must still work as a static sample-report demonstration if free access is unavailable. Do not silently switch to paid usage.
- **Privacy:** tell users before submission that all three text fields are sent to Groq. Encourage them not to enter names or confidential details. Groq's data handling terms and any temporary retention are separate from ProofPath AI's no-database design. Review the current terms before recording or sharing the demo.
- **Eligibility:** Groq's services agreement currently requires the developer account holder to be at least 18.

API references:

- [Groq Quickstart](https://console.groq.com/docs/quickstart)
- [Groq Chat Completions API](https://console.groq.com/docs/api-reference)
- [Model page: `openai/gpt-oss-20b`](https://console.groq.com/docs/model/openai/gpt-oss-20b)
- [Structured Outputs and supported models](https://console.groq.com/docs/structured-outputs)
- [Current rate limits](https://console.groq.com/docs/rate-limits)
- [Groq data handling](https://console.groq.com/docs/your-data)
- [Groq Services Agreement](https://console.groq.com/docs/legal/services-agreement)

### Structured result contract

The request should use a strict JSON Schema response format supported by the selected model. The JSON object is an implementation contract, not evidence of truth. Pydantic then validates the returned data independently.

Required top-level fields:

| Field | Required content |
|---|---|
| `role_title` | Role title from the supplied job description; no guessed employer or facts. |
| `overview` | Concise summary grounded in identified requirements and supplied examples. |
| `skill_assessments` | One entry for every skill explicitly stated or reasonably inferred. This is the authoritative list; the overview is derived from it. |
| `plan_days` | Exactly seven records numbered in order 1–7. |
| `assumptions_and_limitations` | Missing context, uncertain readings, and the fact that skill ability is not independently verified. |

Each `skill_assessments` entry requires `skill_name`, `requirement_type` (`explicit` or `inferred`), `job_description_basis`, `uncertain`, `uncertainty_note`, `why_it_matters`, `evidence_category` (one of the three exact approved categories), `skill_claimed_by_user`, `supporting_example_quote`, `what_is_missing`, `suggested_next_step`, and `priority`.

Each `plan_days` entry requires `day_number`, `task`, `deliverable`, `targeted_gap`, `why_it_matters`, and `completion_criterion`. All seven day numbers must be present once and ordered 1 through 7. Prioritize two or three gaps when personal information is available; otherwise disclose the beginner-friendly default assumptions.

Pydantic validation rules:

1. All required fields are present and non-empty where a useful explanation is required; unexpected category labels are rejected.
2. Every skill is a requirement identified in the returned authoritative skill list; no parallel skill list may omit an assessment.
3. `supporting_example_quote` must be blank or an exact excerpt found in the submitted project/work field after case and whitespace normalization. A skill claim from the separate skills field cannot be used as the supporting excerpt.
4. `Evidence provided` requires a supporting project/work excerpt. Without one, a claimed skill must be rendered as **“Skill claimed — evidence not provided”** and categorized **Evidence not provided**. Partial evidence likewise requires an actual described example, not just missing details.
5. An `inferred` requirement must be labeled as an inference; any uncertain interpretation must have an explanation. Explicit requirements must have a basis in the job-description text. The prompt requests a short basis for every requirement.
6. Each skill contains `why_it_matters`, an example or explicit absence, `what_is_missing`, and a concrete `suggested_next_step`.
7. The plan has exactly seven sequential days and every day contains its task, deliverable, gap, relevance, and completion criterion.
8. Never render an invalid, incomplete, or refused response as a valid personalized report. Show a friendly error, preserve the form fields, and offer manual retry and the separate sample report.

These checks validate structure and selected relationships. They do not verify the model's interpretation, prove that a quoted example demonstrates ability, or guarantee that the plan will work for every person. The UI and report must say that categories assess the information provided, not the user's actual competence.

## Important Failure Modes

- **Blank or too-short job description** → server-side validation explains that the full internship description is needed, keeps entered text, and makes no AI request.
- **Missing API key** → display a setup message directing the developer to `.env`; do not call Groq and do not reveal the key.
- **Rate limit, timeout, network issue, service outage, or unavailable model** → show a concise issue-specific message when known, preserve inputs, offer **Try Again** (new call only after click), and separately offer **Demo example — not based on your inputs**.
- **Malformed, incomplete, refused, or Pydantic-invalid AI response** → do not show personalized results or download; say the analysis could not be validated, preserve inputs, and offer manual retry/sample.
- **Sample report used** → mark the sample clearly at the top and in its download. Never insert it into the custom-analysis result or label it personalized.
- **Refresh/navigation** → results can be lost because the app deliberately has no persistent storage; tell the user they can download the report before leaving.

Do not log request bodies, responses, names, project details, API keys, or exception representations that could contain them. Map known API errors to safe user-facing messages and log only a minimal technical category and request outcome if logging is needed.

## Working-Demo Acceptance Checks

These are the manual checks the build should complete before the demo is considered working; they do not add test libraries or expand the product:

1. The home actions open the same form; the sample action fills realistic editable data. Empty/too-short job-description input shows inline guidance, preserves all fields, and makes no Groq call. Blank optional fields still allow analysis and are described accurately.
2. The pre-submit Groq disclosure is visible. The request is made only from Flask. The API key is absent from rendered HTML, browser JavaScript, logs, screenshots, `.env.example`, and Git-tracked files.
3. With a valid free-tier key, one submission returns a complete response that passes Pydantic checks before any personalized result appears. Explicit and inferred requirements are distinguishable; uncertain interpretations include explanations; every returned skill has all required fields; claim-only cases use the exact label and are not treated as demonstrated evidence.
4. The initial results view shows the assessment summary and skill-by-skill rows. Clicking the plan action reveals exactly seven ordered days and the final report below them on the same page, without another AI request. The plan prioritizes up to three gaps when personal details are supplied, and uses a labeled general starting plan when they are not.
5. Missing key, rate limit, timeout, service/network error, refusal, and invalid response each result in a helpful error, preserved inputs, and a manual retry action. There are no background or automatic retries. The separate report is clearly labeled “Demo example — not based on your inputs.”
6. With a valid result, **Download Report** downloads an openable Markdown file that contains the role and requirements, categories and examples/absence, prioritized next steps, all seven days and deliverables, and uncertainty/limitations. The file uses the current validated analysis and requires no second AI call or persistent server file. With no valid result, the personalized download is unavailable and the page explains the next action.
7. Refreshing or closing the results can lose them; no user history reappears after restarting the app. A download happens only after the user's click.

The model's ability to identify every relevant skill in arbitrary job text remains a judgment task. These checks verify the promised response shape and evidence rules but do not establish factual correctness or independent skill verification.

## What Was Simplified and Why

- **Local Flask app** instead of a hosted product — meets the local demo/video need without deployment setup. A public deployment can be considered later after the local demo works and is reviewed.
- **One AI call for assessment and all seven days** instead of separate calls — reduces latency, free-tier use, and state-handling complexity. The response is longer, so use one finite timeout and a clear loading message.
- **Markdown download** instead of PDF — preserves the required content and structure without a PDF rendering library or layout debugging. The user can print it to PDF from a Markdown viewer/browser if needed.
- **No database or accounts** — one user can complete the workflow without sign-up; closing/refreshing may lose the result and the user controls the downloaded file.
- **Only one sample report as fallback** — provides a dependable local demo if AI service access fails while preserving a clear boundary between demo content and the user's own analysis.
- **No automatic retries or extra model** — avoids unexpected free-tier usage and extra failure paths; the user initiates any retry.
- **One focused internship type** — keeps the prompt, sample, plan, and build small enough to demonstrate the approved data analyst internship workflow.

## Decisions and Open Issues

### Decisions the learner approved

- Use GroqCloud with `openai/gpt-oss-20b`, subject to current eligibility and free-tier availability; do not require a paid subscription.
- Keep the demo local first; deployment is optional only after the local app is complete and tested.
- Use Flask/Python with HTML/CSS and a little JavaScript. Keep the API key on the Python server.
- Use the official Groq Python library and Pydantic. Request structured JSON where supported, then validate it in Python; never treat schema compliance as proof of factual correctness.
- Keep user inputs and results out of a database, saved history, persistent files, and logs. Explain Groq data processing in the pre-submit disclosure.
- On service failure, show an error and offer a separate prewritten sample labeled **“Demo example — not based on your inputs.”** Preserve the user's form values and allow manual retry; never retry automatically.
- Generate the assessment and plan in one request. Initially show the assessment; reveal the already-generated plan and report on the same page without another call.
- Generate a readable Markdown report in memory only after the user clicks **Download Report**; use the current validated result, not the sample unless the user explicitly selects it.
- Use a local `.venv`, minimal `requirements.txt`, `.env`, placeholder `.env.example`, and `.gitignore` exclusions for `.env` and `.venv/`.

### Implementation details derived from those choices

- Python 3.11+; Flask 3.1.3; Groq SDK 1.7.0; Pydantic 2.14.1; python-dotenv 1.2.4. All pinned packages are available and their Python version metadata is compatible with Python 3.11. Resolve the set together in `.venv` before implementation and recheck compatibility if any pin changes.
- Flask routes: `GET /` for home/form; `POST /analyze` for server validation and one Groq call; `POST /download` for an in-memory Markdown attachment; and a separate `GET /sample-report` for the static labeled example. Sample form values can be prefilled using a query parameter on `/`.
- The full analysis is validated before rendering any personalized result. Summary counts and final report sections are derived from the validated assessment, not separately generated.
- JavaScript reveals the hidden plan and final report already returned by Flask. It never handles the API key, calls Groq, or stores content in local storage.
- Download request carries the current result JSON and its per-process HMAC signature from the page. Flask checks the signature before parsing, then validates with Pydantic again. Tampered, malformed, or invalid payloads receive an error response and no attachment. No Groq key, database, persistent report file, or browser local storage is involved. The HMAC signing key stays in Python memory and changes when the local process restarts.
- Use a finite 60-second SDK timeout and set the Groq SDK's `max_retries=0` to disable its built-in retries. A manual retry is an explicit new form submission.
- Keep Flask debug mode off in the documented demo run and keep the built-in server bound to localhost.

### Small build stages and checkpoints

The `5-build` work should proceed in these small stages. Each checkpoint is a manual demonstration of the stage before moving on; it does not require a new testing framework.

1. **Core form and sample data:** Build the home page, shared guided form, editable sample prefill, and basic required/optional field validation. Check both entry actions reach the same form and failed validation preserves input.
2. **Groq integration and validation:** Add local key loading, one request using `openai/gpt-oss-20b` structured JSON, Pydantic models, and evidence/quote/day consistency rules. Check valid and intentionally invalid model-shaped data before displaying results. Confirm no key or submitted text is logged or placed in browser code.
3. **Results and plan reveal:** Render assessment summary and skill cards from validated data, with the seven-day plan and final report below and initially hidden. Check the reveal works on the same page without another Groq request.
4. **Markdown download:** Add the result JSON and HMAC signature to the download form; verify the signature and Pydantic data again in Flask; stream Markdown from memory. Check a valid download contains all required sections, while changed JSON/signature returns an error and no file.
5. **Error handling and accessibility checks:** Consolidate friendly messages for missing keys, API errors, rate limits, timeouts, validation failures, and manual retry. Check form preservation and the separate labeled sample fallback. Review keyboard use, focus visibility, heading order, labels, contrast, evidence text labels, and plan reveal announcements.

Implement basic accessible labels and safe error handling as each page is built; stage 5 is the final end-to-end review and correction pass. No features outside the approved PRD are added in these stages.

### One useful unknown clarified

The learner asked how to keep AI-generated analysis dependable. We clarified the difference between **structured output** and **correct analysis**: JSON Schema/Pydantic can check shape, allowed values, and selected relationships, but cannot prove that an interpretation is true. The implementation uses a supporting-example excerpt checked against the project text, labels uncertain job-description inferences, and avoids any claim of ability verification. This approach should be reviewed during the build against the chosen model's current strict-schema support.

### Remaining review notes

- The precise minimum length for a usable job description is an implementation threshold; choose a conservative guardrail during the build and confirm it accepts the sample while rejecting blank or plainly unusable input.
- Groq's official Structured Outputs documentation currently lists `openai/gpt-oss-20b` as supporting strict JSON Schema mode, which matches the planned request format. Its free-tier eligibility, model availability, quota values, cost terms, retention policy, and account rules can change. Check the model page, structured-output support, and the account console again before implementation and before the demo. The current documented rate-limit table lists 30 RPM, 1,000 RPD, 8,000 TPM, and 200,000 TPD for this model; confirm the account's actual free quota. If free access is unavailable or exhausted, show the clear error and separate sample report. Do not add a payment method, upgrade, or silently switch to paid usage or another model/service.
- The approved PRD's `Download format` open question is resolved as Markdown: it is simpler and dependable within the hackathon while meeting the required end-to-end download criterion.

