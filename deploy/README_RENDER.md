Render deployment notes for DopeInTheMornings

1) Build & start commands
- Build command (Render):
  pip install --upgrade pip setuptools wheel && pip install numpy==2.1.0 && pip install -r requirements.txt && python manage.py collectstatic --noinput && python manage.py migrate
- Start command (Render / Procfile):
  gunicorn Podcastdope.wsgi:application --bind 0.0.0.0:$PORT --workers 3

2) Required environment variables (set in Render dashboard or attach a managed database):
- DJANGO_SECRET_KEY: a strong, unshared secret. Required in production.
- DJANGO_SETTINGS_MODULE: set to Podcastdope.prod
- DATABASE_URL: when you attach a managed Postgres, Render will populate this automatically.
- EXTRA_ALLOWED_HOSTS (optional): comma-separated additional hosts for ALLOWED_HOSTS.

3) Why pandas failed to build
- The error "metadata-generation-failed" when installing pandas typically means pip tried to build pandas from source and the isolated build environment either lacked a pre-installed compatible NumPy wheel or the build toolchain. To avoid building from source on Render we:
  - upgrade pip/setuptools/wheel so pip can install pre-built binary wheels when available
  - pre-install numpy (the required version) before installing the rest of the requirements so pandas' build-time dependency is satisfied

4) Notes
- If the build still fails, check the Python runtime version used by Render: use Python 3.10+ (3.11 recommended) so pre-built wheels for numpy/pandas are available. You can set the "runtime" or "Python version" in Render service settings.
- Alternatively you can pin to older pandas/numpy wheels that are compatible with the selected Python runtime, or install pandas from conda in a different environment.

5) Next steps
- Update Render service to use the new build command above, or keep the render.yaml in the repo and let Render pick it up.
- Ensure the Render runtime is Python 3.10 or 3.11. Attach a managed Postgres and set DJANGO_SECRET_KEY.

