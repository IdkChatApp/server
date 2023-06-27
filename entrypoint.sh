#!/bin/sh

cd idkchat || exit

if [ -d "/idkstatic" ]; then
  python3 manage.py collectstatic
fi

python3 manage.py migrate
daphne -b 0.0.0.0 -p 8000 idkchat.asgi:application