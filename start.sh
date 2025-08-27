#!/bin/bash
# Start CaseForge Django server with correct environment

cd "$(dirname "$0")"
source venv/bin/activate
echo "Using Python: $(which python)"
python manage.py runserver