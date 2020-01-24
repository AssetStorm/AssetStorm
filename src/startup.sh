#!/bin/bash
export PYTHONPATH=$PYTHONPATH:/usr/local/lib/python3.8/site-packages
python manage.py migrate
python manage.py loaddata AssetStorm/assets/fixtures/*
gunicorn --workers=3 AssetStorm.wsgi -b 0.0.0.0:8080