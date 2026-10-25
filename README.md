# ProofPath AI

**Turn internship requirements into evidence-backed portfolio actions.**

ProofPath AI helps students and recent graduates prepare for entry-level data analyst internships by comparing job requirements with their existing skills, projects, and practical examples. It highlights evidence gaps and creates a personalized seven-day portfolio-building plan.

## Why ProofPath AI?

Early-career applicants may know some relevant skills but struggle to demonstrate them with concrete project evidence. ProofPath AI helps them understand what an internship asks for, what their current examples support, and what they can work on next.

## Features

- **Job requirement analysis:** Extracts relevant skills and expectations from a job description.
- **Evidence-based assessment:** Compares requirements with the user's supplied skills and project or work examples.
- **Clear evidence labels:** Distinguishes between `Evidence provided`, `Partial evidence`, and `Evidence not provided`.
- **Honest skill assessment:** A skill name alone is not treated as proof of practical ability.
- **Personalized seven-day plan:** Suggests practical portfolio-building activities based on identified gaps.
- **Sample internship workflow:** Lets users try an editable example instead of starting from a blank form.
- **Separate demo example:** Provides a clearly labeled demo when a personalized analysis cannot be produced.
- **Validated AI responses:** Checks the structure and selected relationships in the AI response before displaying personalized results.
- **No account required:** The prototype does not require users to create an account or maintain a persistent history.

## How It Works

1. Enter or edit a data analyst internship job description.
2. Provide your current skills and relevant project or work examples.
3. Submit the form for analysis.
4. Review the identified requirements and how your supplied evidence relates to them.
5. Use the seven-day portfolio plan to work on evidence gaps and strengthen your project portfolio.

## Technology Stack

- **Python** — application logic
- **Flask** — web application
- **Groq API** — AI-powered analysis
- **Pydantic** — response validation
- **HTML, CSS, JavaScript** — user interface
- **pytest** — automated testing

## Run Locally on Windows

### 1. Prerequisites

Install Python 3.11 or newer. Python 3.12 is suitable.

You also need a Groq API key for personalized AI analysis. Keep the key private.

### 2. Open the project folder

Open Command Prompt and run:

```bat
cd /d "%USERPROFILE%\Desktop\ProofPathAI"
```

### 3. Create and activate a virtual environment

Run these commands one at a time:

```bat
python -m venv .venv
```

```bat
.venv\Scripts\activate
```

### 4. Install dependencies

```bat
python -m pip install -r requirements.txt
```

### 5. Configure your API key

Create your local environment file by copying the example:

```bat
copy .env.example .env
```

Open it:

```bat
notepad .env
```

Add your key to the `GROQ_API_KEY` setting, replacing the placeholder value. Save the file and close Notepad.

**Security:** Never commit `.env`, publish your API key, or include it in screenshots, issues, or public messages. The `.env` file should remain local.

If `.env.example` is not included in the repository, create `.env` locally and add the required `GROQ_API_KEY` setting. Follow the configuration expected by the application.

### 6. Start the application

```bat
python app.py
```

Open [http://127.0.0.1:5000](http://127.0.0.1:5000) in your browser.

Keep Command Prompt open while using the application. Press `Ctrl+C` in that window to stop the server.

## Run the Tests

With the virtual environment activated, run:

```bat
python -m pytest -q
```

The test suite covers application behavior, AI-service handling, and portfolio-plan generation.

## Privacy and Responsible AI

- The job description, skills, and project or work examples submitted for personalized analysis are sent to Groq for processing.
- Do not submit names, private contact details, confidential work information, or other sensitive data.
- The prototype does not store submissions in a database or persistent history.
- Groq processes submitted text under its own service terms and data practices.
- AI output can be incomplete or incorrect. Structural validation does not prove that every extracted requirement or assessment is factually correct.
- Evidence labels describe the information supplied to the application, not a definitive judgment of a person's ability.
- A demo example is separate from personalized analysis and must not be interpreted as an assessment of the user's inputs.

## Troubleshooting

**Python is not recognized**

Install Python 3.11 or newer, enable the option to add Python to PATH if available, and open a new Command Prompt. You can use `py` instead of `python` if the Python launcher is installed.

**A module is missing**

Activate `.venv` and run:

```bat
python -m pip install -r requirements.txt
```

**The API key is missing**

Check that your local `.env` file contains the expected `GROQ_API_KEY` setting. Save the file and restart the application. Do not print or share the key.

**Groq returns a rate-limit or service error**

Wait until the service is available, then retry manually if appropriate or view the separate demo example. The application does not automatically retry requests or switch to a paid plan.

**Port 5000 is already in use**

Stop the other local application using that port, then start ProofPath AI again.

## Project Status

ProofPath AI is a working prototype with a personalized assessment workflow and a seven-day portfolio plan. Its purpose is to help early-career applicants turn job requirements into concrete next steps—not to guarantee employment, internship selection, or technical proficiency.

## Created By

**Sunnaina Tanveer**

Built as an AI-assisted project focused on practical, evidence-aware career preparation for aspiring data analysts.
