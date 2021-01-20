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

#mqtt = Mqtt()
cors=CORS(app)

def create_app():
    mqtt.init_app(app)




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
    gps_lat=db.Column(db.Float, nullable=False)
    gps_lng=db.Column(db.Float, nullable=False)
    machines = db.relationship('Machine', backref='machines')

class Client(db.Model):
    id=db.Column(db.Integer, primary_key=True)
    name=db.Column(db.String, nullable=False)
    laund_list=db.Column(db.String)

class DatapointLaund(db.Model):
    id=db.Column(db.Integer, primary_key=True)
    dispo=db.Column(db.Integer, nullable=False)
    timestamp=db.Column(db.DateTime,nullable=False)
    laund_id=db.Column(db.Integer, db.ForeignKey('laund.id'), nullable=False)

class DatapointMachine(db.Model):
    id=db.Column(db.Integer, primary_key=True)
    state=db.Column(db.Integer, nullable=False)
    timestamp=db.Column(db.DateTime,nullable=False)
    machine_id=db.Column(db.Integer, db.ForeignKey('machine.id'), nullable=False)


db.create_all()

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

def newLaund(name, address,gps_lat,gps_lng):
    laund = Laund(name=name, address=address,gps_lat=gps_lat, gps_lng=gps_lng)
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
    machine = Machine.query.filter_by(laund_id=laund_id, frequency=freq).first()
    machine.state=newState
    db.session.commit()

def initDb():
    clearDb()
    newClient('Robin')
    newLaund('laverie du port','123 rue du port',gps_lat=45.77010440000001,gps_lng=4.8826282)
    newLaund('laverie de la terre','456 chemin',gps_lat=45.7578137,gps_lng=4.8320114)
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
            'id': launds[i].id,
            'name': launds[i].name,
            'adresse': launds[i].address,
            'dispo': getAvailable(machines[i]),
            'geo_lat':launds[i].gps_lat,
            'geo_lng':launds[i].gps_lng,
            'max' : len(machines[i])
        })
    return data

def DatapointsToDict(laund_id,number):
    data=[]

    datapoints = DatapointLaund.query.filter_by(laund_id=laund_id).order_by(DatapointLaund.timestamp.desc()).all()
    for i in range(number):
        data.append({
            'dispo': datapoints[i].dispo,
            'timestamp' : datapoints[i].timestamp
        })

    
    return data
    
    
def getAvailable(machines):
    num =0
    for machine in machines:
        if machine.state==0:
            num= num+1
    return num

def record_loop(timestep):
    # Register datapoints every timestep seconds 
    while True:
        clients=Client.query.filter_by().all()
        for client in clients:
            launds=getLaundList(client)
            for laund_id in launds:
                laund = Laund.query.filter_by(id=laund_id).first()
                machines = getMachines(laund.name,laund.address)
                datapoint_laund = DatapointLaund(dispo=getAvailable(machines), laund_id=laund_id,timestamp=datetime.now())
                db.session.add(datapoint_laund)
                db.session.commit()
                for machine in machines:
                    datapoint_machine = DatapointMachine(state=machine.state, machine_id=machine.id,timestamp=datetime.now())
                    db.session.add(datapoint_machine)
                    db.session.commit()
        time.sleep(timestep)
        print("new datapoint from process : ",os.getpid())

@app.cli.command('init-db')
def initDbCommand():
    """Clear the existing data and create new tables."""
    clearDb()
    initDb()
    click.echo('Initialized the database.')

"""
@mqtt.on_connect()
def handle_connect(client, userdata, flags, rc):
    mqtt.subscribe('laverie/#')

@mqtt.on_message()
def handle_mqtt_message(client, userdata, message):
    
    topic=message.topic
    payload=message.payload.decode('utf-8')
    print("{},{}".format(topic,payload))
    id_lav = int(message.topic.split("/")[1])
    changeState(id_lav, float(payload.split(",")[0]), int(payload.split(",")[1]))
    machine = db.session.query(Machine).filter(Machine.id==1).first()
    print(machine.state)
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

@app.route('/data/<laund_id>')
def data_laund(laund_id):
    try :
        client = findClient(int(request.args.get('id')))
        nombre = int(request.args.get('nombre'))

    except KeyError:
        print("error key")
    if client is not None:
        data = []
        data = DatapointsToDict(laund_id=laund_id,number=nombre)
        return jsonify(client="Laveries de "+client.name, datapoints=data)
    return jsonify(client="Tu n'es pas connecté")
"""
@app.route('/data/<id_laund>/<id_machine>/<number>')
def data_laund(type, id_laund, id_machine, number):
    try :
        client = findClient(int(request.args.get('id')))
    except KeyError:
        print("error key")
    if client is not None:
        data
        return jsonify(client="Laveries de "+client.name, stations=data)

    return jsonify(client="Tu n'es pas connecté")
"""
if __name__ == "__main__":
    initDb()
    #create_app()
    p = Process(target=record_loop, args=(60,))
    p.start()
    app.run(host=HOSTNAME, debug=True, use_reloader=False)
    p.join()

