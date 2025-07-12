# models.py
from flask_sqlalchemy import SQLAlchemy

db = SQLAlchemy()

class User(db.Model):
    __tablename__ = 'user'
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    password = db.Column(db.String(120), nullable=False)
    role = db.Column(db.String(20), nullable=False, default='employe')

class Checklist(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(100), nullable=False)
    date = db.Column(db.Date, nullable=False)
    status = db.Column(db.String(20), nullable=False)
    created_by = db.Column(db.String(80), nullable=False)
    items = db.relationship('ChecklistItem', backref='checklist', lazy=True)

class ChecklistItem(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    checklist_id = db.Column(db.Integer, db.ForeignKey('checklist.id'), nullable=False)
    item_text = db.Column(db.Text, nullable=False)
    answer = db.Column(db.String(10), nullable=False)
    comment = db.Column(db.Text)

class ChecklistTemplate(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(255), nullable=False)
    items = db.Column(db.Text, nullable=False)
    created_by = db.Column(db.String(100))
    created_at = db.Column(db.DateTime, server_default=db.func.now())
