# Report-It

Report-It is a small Flask and vanilla JavaScript app for preparing Open311-style street issue reports from an uploaded image, location, short description, and phone number.

## Stack

- Frontend: plain JavaScript, HTML, and CSS
- Backend: Python Flask
- Database: SQLite
- AI report generation: OpenAI Responses API with image input
- 311 submission sample: San Francisco Open311-compatible payload format

## Local Setup

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
```

Set these values in `.env`, then run:

```bash
OPENAI_API_KEY=sk-your-key-here
OPENAI_MODEL=gpt-5.6
OPEN311_BASE_URL=https://san-francisco2-dev.spotmobile.net/open311/v2
OPEN311_PROVIDER_NAME=San Francisco 311
PUBLIC_BASE_URL=https://your-cloudflare-hostname.example.com
```

`PUBLIC_BASE_URL` is optional. If it is set, the generated Open311 sample includes the uploaded image as a public `media_url`.

Then start the app:

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

## Open311 Integration

The app is configured around San Francisco's Open311-compatible SpotMobile payload format by default. It does not POST to Open311 or check whether a city created an official request. After preparing the payload, the UI waits 5 seconds and marks the local flow successful.

```text
https://san-francisco2-dev.spotmobile.net/open311/v2
```

The sample shows the fields that would be sent to `POST /requests.json`: `service_code`, `address_string`, `description`, `phone`, optional `media_url`, and any required `attribute[...]` values for the selected service.
