#!/usr/bin/env bash
set -e

python manage.py migrate
python manage.py seed_initial_data
gunicorn project.wsgi:application --bind 0.0.0.0:$PORT
