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

## GitHub Pages Deployment

The GitHub Pages deployment publishes the `static/` directory and runs fully in the browser. GitHub Pages cannot run Flask, SQLite, Python, `.env` files, or server-side OpenAI calls, so the Pages version prepares a local Open311 request sample and shows a successful submission after 5 seconds.

1. Commit and push the Pages workflow:

```bash
git add .
git commit -m "chore: deploy static app to github pages"
git push
```

2. In GitHub, open the repo:

```text
https://github.com/skinreich11/Report-It-Cloud5
```

3. Go to Settings -> Pages.

4. Under Build and deployment, set Source to:

```text
GitHub Actions
```

5. Go to Actions -> Deploy GitHub Pages and run the workflow, or push to `main`.

6. After it finishes, the site should be available at:

```text
https://skinreich11.github.io/Report-It-Cloud5/
```

For the full Flask/OpenAI/SQLite version, run the app locally or deploy it to a backend-capable host such as Vercel, Render, Fly.io, Railway, or another Python hosting service.

## Vercel Deployment

This repo is deployable on Vercel as a Python/Flask app. The deployment entrypoint is `main.py`, and `vercel.json` routes traffic to that Flask app.

1. Commit these deployment files:

```bash
git add pyproject.toml main.py vercel.json .vercelignore README.md
git add app static tests requirements.txt run.py .env.example
git commit -m "chore: configure vercel deployment"
git push
```

2. In Vercel, import the GitHub repo.

3. In the Vercel project settings, add this Environment Variable:

```text
OPENAI_API_KEY=your-real-openai-api-key
```

Optional environment variables:

```text
OPENAI_MODEL=gpt-5.6
OPEN311_BASE_URL=https://san-francisco2-dev.spotmobile.net/open311/v2
OPEN311_PROVIDER_NAME=San Francisco 311
PUBLIC_BASE_URL=https://your-vercel-domain.vercel.app
```

4. Deploy with Vercel's default Python settings. Do not set a custom build command unless Vercel asks for one.

The previous Vercel error:

```text
No `project` table found in: /vercel/path0/pyproject.toml
```

is fixed by the `[project]` section in `pyproject.toml`.

Important deployment note: Vercel serverless functions do not provide a persistent SQLite database or permanent upload storage. This app uses `/tmp` on Vercel so it can run, but reports and uploaded images may disappear between cold starts or deployments. For production persistence, replace SQLite/uploads with hosted storage such as Vercel Postgres plus Vercel Blob, Supabase, Neon, or another managed database/storage provider.

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
