
from flask_db import db
from wapp.core import Wapp

class Thing(db.Model):
    __tablename__ = 'thing'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    description = db.Column(db.Text, nullable=True)

    class WappModel:
        slug = "thing"
        name = "Thing"
        description = "A model representing a Thing entity"


class ThingsWapp(Wapp):
    class Models:
        thing = Thing

