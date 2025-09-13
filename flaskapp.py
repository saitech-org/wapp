import os

from flask import Flask
from env import db, ENV, WAPP_AUTO_MIGRATE, DATABASE_URL
from demo.wapp import DemoWapp
from nested.things.wapp import ThingsWapp
from core import Wapp
import subprocess

class MainWapp(Wapp):
    class Wapps:
        demo = DemoWapp
        things = ThingsWapp

def is_main():
    return os.environ.get("WERKZEUG_RUN_MAIN") == "true"

if ENV == 'development' and WAPP_AUTO_MIGRATE and is_main():
    # Run migration script automatically in development using the CLI entry point
    print('[flaskapp.py] Running migrations (development mode)...')
    subprocess.run(['wapp-migrate'], check=True)


def create_app():
    flask_app = Flask(__name__)
    flask_app.config['SQLALCHEMY_DATABASE_URI'] = DATABASE_URL
    db.init_app(flask_app)

    # Bind db to the main Wapp
    MainWapp.register_wapp(flask_app, db)

    # Register blueprints from your Wapps
    with flask_app.app_context():
        # db.create_all()  # Create tables for all models (handled by Alembic now)
        pass

    return flask_app

if __name__ == '__main__':
    app = create_app()
    app.run(debug=True)
