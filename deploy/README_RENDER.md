Render deployment notes for DopeInTheMornings

1) Build & start commands
- Build command (Render):
  pip install -r requirements.txt && python manage.py collectstatic --noinput && python manage.py migrate
- Start command (Render / Procfile):
  gunicorn Podcastdope.wsgi:application --bind 0.0.0.0:$PORT --workers 3

2) Required environment variables (set in Render dashboard or attach a managed database):
- DJANGO_SECRET_KEY: a strong, unshared secret. Required in production.
- DJANGO_SETTINGS_MODULE: set to Podcastdope.prod
- DATABASE_URL: when you attach a managed Postgres, Render will populate this automatically.
- EXTRA_ALLOWED_HOSTS (optional): comma-separated additional hosts for ALLOWED_HOSTS.

3) Notes
- The project already includes Podcastdope/prod.py which expects DJANGO_SECRET_KEY and DATABASE_URL.
- If your repo previously had a file named `requirements` without .txt, this repo already contains `requirements.txt` so the default Render behaviour will work.
- WhiteNoise is configured in prod.py; static files are collected into `staticfiles/`.

4) Next steps
- In the Render dashboard: create a new Web Service, connect the repo and branch, set the Build & Start commands above, attach a Managed Postgres, and set DJANGO_SECRET_KEY in the Environment secrets.
- After first deploy, confirm migrations ran and static files are served. Check logs if errors appear.
