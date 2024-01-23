from flask import Flask, render_template
from flask_cors import CORS  # Import CORS from flask_cors
from flask_migrate import Migrate
from flask_socketio import SocketIO, emit
from flask_sqlalchemy import SQLAlchemy

app = Flask(__name__)
app.config['SECRET_KEY'] = 'asda!@%^213adaw#3as@!@#!#nksndak12313asd1@@nm2%^&*#nasmadk231m132m'
app.config['SQLALCHEMY_DATABASE_URI'] = 'postgresql://postgres:12345@localhost/chat-application-user-service'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)
socketio = SocketIO(app, cors_allowed_origins="*")
migrate = Migrate(app, db)

CORS(app) 

class Message(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    sender_id = db.Column(db.String(50), nullable=False)
    receiver_id = db.Column(db.String(50), nullable=False)
    content = db.Column(db.Text, nullable=False)
    timestamp = db.Column(db.TIMESTAMP, server_default=db.func.current_timestamp())

@socketio.on('connect', namespace='/chat')
def handle_connect():
    print('Client connected')

@socketio.on('disconnect', namespace='/chat')
def handle_disconnect():
    print('Client disconnected')

@socketio.on('send_message', namespace='/chat')
def handle_send_message(data):
    sender_id = data['sender_id']
    receiver_id = data['receiver_id']
    content = data['content']

    # Save message to the database
    message = Message(sender_id=sender_id, receiver_id=receiver_id, content=content)
    
    db.session.add(message)
    db.session.commit()

    # Emit the message to the receiver
    emit('receive_message', data, room=receiver_id, namespace='/chat')


# Flask routes
@app.route('/')
def index():
    return render_template('index.html')

if __name__ == '__main__':
    db.create_all()
    socketio.run(app, debug=True)
