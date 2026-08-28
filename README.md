# Report-It

Report-It is a small Flask and vanilla JavaScript app for drafting DC 311-style street issue reports from an uploaded image, location, short description, and phone number.

## Stack

- Frontend: plain JavaScript, HTML, and CSS
- Backend: Python Flask
- Database: SQLite
- AI report generation: OpenAI Responses API with image input

## Local Setup

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
```

Set `OPENAI_API_KEY` in `.env`, then run:

```bash
python run.py
```

Open `http://127.0.0.1:5000`.

## Tests

```bash
python -m pytest --cov=app --cov-fail-under=80
```

## Security Notes

- `.env` is ignored and must not be committed.
- SQLite data and uploaded images are written under `instance/`, which is ignored.
- Uploads are limited to JPG, PNG, and WEBP images up to 5MB.
- API writes use parameterized SQLite queries.

## DC 311 Integration

The app currently generates a draft report. A backend TODO is included in the OpenAI prompt path to add a future integration that submits the validated report data to the DC 311 website after user confirmation.
