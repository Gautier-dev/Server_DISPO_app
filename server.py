from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask import jsonify
from flask_cors import CORS
import json 
import click

HOSTNAME = "127.0.0.1"
DATABASE_URI = 'sqlite:///machines.db'

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI']= DATABASE_URI
app.config['FLASK_APP']='server'
db = SQLAlchemy(app)
db.create_all()
cors=CORS(app)

class Machine(db.Model):
    id=db.Column(db.Integer, primary_key=True)
    state=db.Column(db.Integer)
    laund_id=db.Column(db.Integer, db.ForeignKey('laund.id'), nullable=False)

class Laund(db.Model):
    id=db.Column(db.Integer, primary_key=True)
    name=db.Column(db.String, nullable=False)
    address=db.Column(db.String, nullable=False)
    machines = db.relationship('Machine', backref='machines')

def newLaund(name, address):
    laund = Laund(name=name, address=address)
    db.session.add(laund)
    db.session.commit()

def findLaundId(name, address):
    laund = Laund.query.filter_by(name=name).filter_by(address=address).first()
    return laund.id

def newMachine(state, laund_id):
    machine = Machine(state=state, laund_id=laund_id)
    db.session.add(machine)
    db.session.commit()

def changeState(id, newState):
    machine = Machine.query.filter_by(id=id).first()
    machine.state=newState
    db.session.commit()

def initDb():
    clearDb()
    newLaund('laverie du port','123 rue du port')
    newMachine('0',findLaundId('laverie du port','123 rue du port'))
    changeState(1,'1')
    newMachine('0', findLaundId('laverie du port', '123 rue du port'))
    db.session.commit()

def clearDb():
    machines = Machine.query.all()
    for machine in machines:
        db.session.delete(machine)
        
    launds = Laund.query.all()
    for laund in launds:
        db.session.delete(laund)

    db.session.commit()

@app.cli.command('init-db')
def initDbCommand():
    """Clear the existing data and create new tables."""
    clearDb()
    initDb()
    click.echo('Initialized the database.')

@app.route('/')
def home():
    file = open('example.json')
    return json.loads(file.read()) 

if __name__ == "__main__":
    app.run(host=HOSTNAME,debug=True)
