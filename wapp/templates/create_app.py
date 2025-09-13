# app_factory.py
from flask import Flask
from flasgger import Swagger
from app_env import db, DATABASE_URL
from example import Example

def create_app(*, bind: bool = True):
    app = Flask(__name__)
    app.config['SQLALCHEMY_DATABASE_URI'] = DATABASE_URL

    # make sure instance dir exists for sqlite
    import os
    os.makedirs("instance", exist_ok=True)

    db.init_app(app)

    if bind:
        # only register endpoints when running the web app
        Example.bind(app, db)
        Swagger(app)

    return app
