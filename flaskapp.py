from flask import Flask
from flask_db import db
from demo.wapp import DemoWapp
from nested.things.wapp import ThingsWapp
from wapp.core import Wapp
import os
from dotenv import load_dotenv
import subprocess

class MainWapp(Wapp):
    class Wapps:
        demo = DemoWapp
        things = ThingsWapp


# Load environment variables from .env
load_dotenv()

ENV = os.getenv('ENV', 'production')
DATABASE_URL = os.getenv('DATABASE_URL', 'sqlite:///app.db')

if ENV == 'development':
    # Run migration script automatically in development
    print('[flaskapp.py] Running migrations (development mode)...')
    subprocess.run(['python', 'migrate.py'], check=True)


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
