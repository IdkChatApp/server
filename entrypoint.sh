#!/bin/sh

cd idkchat || exit
python3 manage.py migrate
daphne -b 0.0.0.0 -p 8000 idkchat.asgi:application