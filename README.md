# ProofPath AI

ProofPath AI helps students and recent graduates turn internship requirements into portfolio evidence. The local prototype currently includes the homepage, editable sample form, server-side validation, one Groq request per analysis attempt, and Pydantic response validation. The personalized results page and seven-day plan display are a later build stage.

## Run locally on Windows

Open **Command Prompt** in the project folder and run:

```bat
python -m venv .venv
.venv\Scripts\activate
python -m pip install -r requirements.txt
copy .env.example .env
notepad .env
```

In Notepad, replace the placeholder value with your Groq API key. Save and close the file. Do not paste the key into a command, issue, screenshot, or public repository. The `.env` file is excluded from Git. Restart the app after changing it.

Then start the app:

```bat
python app.py
```

Open <http://127.0.0.1:5000>. Keep the Command Prompt window open while using the app. Press `Ctrl+C` to stop it. The app makes one request only when you submit the form; it does not automatically retry.

If `python` is not recognized, install Python 3.11 or newer and select the option to add Python to PATH, then open a new Command Prompt. The Python launcher `py` may be used in place of `python` if it is installed.

## Try Stage 2

- Choose **Try Sample Data Analyst Internship** to fill the same editable form.
- Submit a usable job description with your local Free-plan key configured. A response that passes structural and consistency checks shows a confirmation; this stage does not display personalized results yet.
- Remove or blank the local key, restart the app, and submit again to see the missing-key error. Never print the key to check it.
- If a Free-plan rate limit or service issue occurs, the app shows an error and a separate **Demo example — not based on your inputs** link. The fixed sample is never presented as analysis of your submission.

Submitted job description, skills, and project/work text are sent to Groq for analysis. Do not enter names or confidential information. ProofPath AI does not save submissions in a database or persistent history; Groq processes the text under its own data practices. The response checks validate structure and selected relationships, not factual correctness or a person's actual ability.

## Troubleshooting

- **`No module named ...`:** Confirm `(.venv)` appears at the start of the prompt, then run `python -m pip install -r requirements.txt` again.
- **Missing API-key message:** Confirm the local `.env` contains a `GROQ_API_KEY` assignment, save it, and restart the app. Never share the value.
- **Free-plan rate-limit message:** Wait for the available limit to reset, then click **Try Again** once or view the separate demo example. The app does not upgrade, switch models, or retry automatically.
- **Port 5000 is already in use:** Stop the other local Flask app or close its terminal window, then restart this app.
- **Python version:** Run `python --version`; use Python 3.11 or newer.
