flask db init
flask db migrate
flask db upgrade
gunicorn --log-level=info service:app