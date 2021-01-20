from flask import Flask, request
from flask_sqlalchemy import SQLAlchemy
from flask import jsonify
from flask_cors import CORS
from flask_mqtt import Mqtt
import json 
import click
from datetime import datetime
from multiprocessing import Process
import time
import os



HOSTNAME = "127.0.0.1"
DATABASE_URI = 'sqlite:///machines.db'

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI']= DATABASE_URI
app.config['MQTT_BROKER_URL'] = HOSTNAME
app.config['MQTT_BROKER_PORT'] = 1883
app.config['MQTT_USERNAME'] = 'slip'
app.config['MQTT_PASSWORD'] = 'slip'
app.config['MQTT_REFRESH_TIME'] = 1.0  # refresh time in seconds
db = SQLAlchemy(app)
#mqtt = Mqtt(app)
db.create_all()
cors=CORS(app)

class Machine(db.Model):
    id=db.Column(db.Integer, primary_key=True)
    state=db.Column(db.Integer)
    frequency=db.Column(db.Float)
    type=db.Column(db.String)
    laund_id=db.Column(db.Integer, db.ForeignKey('laund.id'), nullable=False)

class Laund(db.Model):
    id=db.Column(db.Integer, primary_key=True)
    name=db.Column(db.String, nullable=False)
    address=db.Column(db.String, nullable=False)
    machines = db.relationship('Machine', backref='machines')

class Datapoint(db.Model):
    id=db.Column(db.Integer, primary_key=True)
    time=db.Column(db.Date, default=datetime.now())
    dispo=db.Column(db.Integer, nullable=False)
    laund_id=db.Column(db.Integer, db.ForeignKey('laund.id'), nullable=False)

class Client(db.Model):
    id=db.Column(db.Integer, primary_key=True)
    name=db.Column(db.String, nullable=False)
    laund_list=db.Column(db.String)

def newClient(name):
    client = Client(name=name, laund_list="[]")
    db.session.add(client)
    db.session.commit()

def findClient(id):
    client = Client.query.filter_by(id=id).first()
    return client

def getLaundList(client):
    laund_str = client.laund_list
    laund_str=laund_str.replace("[",'').replace("]",'')
    if laund_str=="":
        laund_list=[]
    else:
        laund_list = laund_str.split(',')
    return laund_list

def setLaundList(client, laund_list):
    laund_str="["+','.join([str(elem) for elem in laund_list])+"]"
    client.laund_list=laund_str
    db.session.commit()
        
def addLaund(client_id, laund_id):
    client= Client.query.filter_by(id=client_id).first()
    laund_list = getLaundList(client)
    if laund_id not in laund_list:
        laund_list.append(laund_id)

    setLaundList(client, laund_list)

def new_data_point(laund, address):
    machines = getMachines(laund, address)
    dispo = getAvailable(machines)
    laund_id=findLaundId(laund,address)
    datapoint = Datapoint(dispo=dispo, laund_id=laund_id)
    db.session.add(datapoint)
    db.session.commit()
    print("commited datapoint")

def metrics_loop(timestep_sec):

    with app.app_context():
        """
        clients = Client.query.filter_by().all()
        
        clients_id =[1]
        clients = [findClient(1)]
        print("CLIEEEEEEEEEEEEEEEEEENTS",clients)
        if clients is not None:
            for client in clients:
                launds = getLaunds(client)
                if launds is not None:
                    for laund in launds:
                        new_data_point(laund.name, laund.address)
        """
        print("click ! ",os.getpid())


def newLaund(name, address):
    laund = Laund(name=name, address=address)
    db.session.add(laund)
    db.session.commit()

def findLaundId(name, address):
    laund = Laund.query.filter_by(name=name).filter_by(address=address).first()
    return laund.id

def newMachine(state, laund_id, freq, type_machine):
    machine = Machine(state=state, laund_id=laund_id, frequency=freq, type=type_machine)
    db.session.add(machine)
    db.session.commit()

def changeState(laund_id, freq, newState):
    print("changing state")
    machine = Machine.query.filter_by(laund_id=laund_id, frequency=freq).first()
    machine.state=newState
    db.session.commit()
    new_data_point(laund.name, laund.address)
    
def initDb():
    clearDb()
    newClient('Robin')
    newLaund('laverie du port','123 rue du port')
    newLaund('laverie de la terre','456 chemin')
    addLaund(1,1)
    addLaund(1,2)
    newMachine('0',findLaundId('laverie du port','123 rue du port'), 102.5,"machine")
    newMachine('0',findLaundId('laverie du port','123 rue du port'), 105.0,"machine")
    newMachine('0',findLaundId('laverie du port','123 rue du port'), 107.5,"seche-linge")
    changeState(1,102.5,'1')
    newMachine('1', findLaundId('laverie de la terre','456 chemin'), 102.5, "machine")
    newMachine('1', findLaundId('laverie de la terre','456 chemin'), 105.0, "machine")
    newMachine('1', findLaundId('laverie de la terre','456 chemin'), 107.5, "seche-linge")
    newMachine('1', findLaundId('laverie de la terre','456 chemin'), 109.0, "seche-linge")

    
    db.session.commit()


def clearDb():
    clients = Client.query.all()
    for client in clients:
        db.session.delete(client)

    machines = Machine.query.all()
    for machine in machines:
        db.session.delete(machine)
        
    launds = Laund.query.all()
    for laund in launds:
        db.session.delete(laund)

    datapoints = Datapoint.query.all()
    for datapoint in datapoints:
        db.session.delete(datapoint)

    db.session.commit()

def getLaunds(client):
    launds=[]
    laund_list= getLaundList(client)
    for id in laund_list:
        laund = Laund.query.filter_by(id=id).first()
        launds.append(laund)
    return launds

def getMachines(laund, address):
    laundId= findLaundId(laund,address)
    return Machine.query.filter_by(laund_id=laundId).all()

def createData(launds, machines):
    data=[]
    for i in range(len(launds)):
        data.append({
            'name': launds[i].name,
            'adresse': launds[i].address,
            'dispo': getAvailable(machines[i]),
            'max' : len(machines[i])
        })
    return data

def getAvailable(machines):
    num =0
    for machine in machines:
        if machine.state==0:
            num= num+1
    return num

@app.cli.command('init-db')
def initDbCommand():
    """Clear the existing data and create new tables."""
    clearDb()
    initDb()
    click.echo('Initialized the database.')


"""
@mqtt.on_connect()
def handle_connect(client, userdata, flags, rc):
    mqtt.subscribe('laveries/#')


@mqtt.on_message()
def handle_mqtt_message(client, userdata, message):
    data = dict(
        topic=message.topic,
        payload=message.payload.decode()
    )

    id_lav = int(message.topic.split("/")[1])
    changeState(id_lav, int(payload[0]), int(payload[1]))
"""

@app.route('/')
def home():
    try :
        client = findClient(int(request.args.get('id')))
    except KeyError:
        print("error key")
    if client is not None:
        machines = []
        launds = getLaunds(client)
        for laund in launds:
            machines.append(getMachines(laund.name,laund.address))
        data = createData(launds,machines)
        return jsonify(client="Laveries de "+client.name, stations=data)

    return jsonify(client="Tu n'es pas connecté")
    
    # file = open('example.json')
    # return json.loads(file.read()) 

if __name__ == "__main__":
    app.run(host=HOSTNAME,debug=True)

    
    
