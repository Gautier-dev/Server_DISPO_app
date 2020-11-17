from flask import Flask
from flask_sqlalchemy import SQLAlchemy

HOSTNAME = "127.0.0.1"
DATABASE_URI = 'sqlite:///machines.db'

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI']= DATABASE_URI
db = SQLAlchemy(app)

class Machine(db.Model):
    id=db.Column(db.Integer, primary_key=True)
    state=db.Column(db.Integer)
    laund_id=db.Column(db.Integer, db.ForeignKey('laund.id'), nullable=False)

class Laund(db.Model):
    id=db.Column(db.Integer, primary_key=True)
    name=db.Column(db.String, nullable=False)
    address=db.Column(db.String, nullable=False)
    machines = db.relationship('Machine', backref='machines')

if __name__ == "__main__":
    app.run(host=HOSTNAME,debug=True)