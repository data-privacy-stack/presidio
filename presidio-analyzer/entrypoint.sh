#!/bin/sh
exec gunicorn -w "$WORKERS" -b "0.0.0.0:$PORT" "app:create_app()"
