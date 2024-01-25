import uuid
from datetime import datetime

from gevent import monkey

monkey.patch_all()

from cassandra.auth import PlainTextAuthProvider
from cassandra.cluster import Cluster
from flask import Flask, jsonify, render_template, request
from flask_cors import CORS
from flask_migrate import Migrate
from flask_socketio import SocketIO, emit, join_room

app = Flask(__name__)
app.config['SECRET_KEY'] = 'asda!@%^213adaw#3as@!@#!#nksndak12313asd1@@nm2%^&*#nasmadk231m132m'

cassandra_config = {
    'contact_points': ['127.0.0.1'],  # the IP address of your Cassandra node
    'auth_provider': PlainTextAuthProvider(username='abhinav', password='12345'),
    'keyspace': 'chat_app'
}


cluster = Cluster(contact_points=cassandra_config['contact_points'], auth_provider=cassandra_config['auth_provider'])
session = cluster.connect()

session.set_keyspace(cassandra_config['keyspace'])

socketio = SocketIO(app, cors_allowed_origins="*")


CORS(app)

class Message:
    def __init__(self, message_id, chat_id, content, seen_at, sender_id, timestamp, type): # messages (message_id, chat_id, content, sender_id, timestamp, type)
        self.sender_id = sender_id
        self.message_id = message_id
        self.chat_id = chat_id
        self.type = type
        self.content = content
        self.timestamp = timestamp
        self.seen_at = seen_at

create_keyspace_query = """
    CREATE KEYSPACE IF NOT EXISTS chat_application_user_service
    WITH replication = {'class': 'SimpleStrategy', 'replication_factor': 1};
"""

create_message_table_query = """
CREATE TABLE IF NOT EXISTS messages (
    message_id UUID PRIMARY KEY,
    chat_id UUID,
    sender_id UUID,
    type TEXT,
    timestamp TIMESTAMP,
    content TEXT,
    seen_at TIMESTAMP
);

"""

# create_user_chat_table_query = """
#     CREATE TABLE IF NOT EXISTS user_chat (
#     user_chat_id UUID PRIMARY KEY,
#     user_id UUID,
#     chat_id UUID,
#     timestamp TIMESTAMP
# );
# """


create_user_chat_table_query = """
    CREATE TABLE IF NOT EXISTS user_chat (
    user_chat_id UUID,
    user_id UUID,
    chat_id UUID,
    timestamp TIMESTAMP,
    PRIMARY KEY (user_id, chat_id)
);
"""

@socketio.on('connect', namespace='/chat')
def handle_connect():
    user_id = request.sid  # Unique identifier for the user (replace this with your authentication logic)
    print(f'User connected: {user_id}')

@socketio.on('disconnect', namespace='/chat')
def handle_disconnect():
    user_id = request.sid  # Unique identifier for the user (replace this with your authentication logic)
    print(f'User disconnected: {user_id}')

@socketio.on('start_private_chat', namespace='/chat')
def start_private_chat(data):
    user1_id = data['user1_id']
    user2_id = data['user2_id']
    chat_id = uuid.uuid4()

    print(f"initial chat_id: {chat_id}")

    select_query = """
        SELECT chat_id
        FROM user_chat
        WHERE user_id = %s ALLOW FILTERING;
    """

    result_user1 = set(row.chat_id for row in session.execute(select_query, (uuid.UUID(user1_id),)))
    result_user2 = set(row.chat_id for row in session.execute(select_query, (uuid.UUID(user2_id),)))
    
    common_chat_ids = result_user1.intersection(result_user2)
    common_chat_id = common_chat_ids.pop() if common_chat_ids else None

    if common_chat_id:
        print(f"common chat found: {common_chat_id}")
        chat_id = common_chat_id
    else:
        user_chat_id1 = uuid.uuid4()
        user_chat_id2 = uuid.uuid4()

        user1_id_uuid = uuid.UUID(user1_id)
        user2_id_uuid = uuid.UUID(user2_id)
        
        insert_query_user = """
            INSERT INTO user_chat (user_chat_id, user_id, chat_id, timestamp)
            VALUES (%s, %s, %s, %s)
        """
        session.execute(insert_query_user, (user_chat_id1, user1_id_uuid, chat_id, datetime.now()))
        session.execute(insert_query_user, (user_chat_id2, user2_id_uuid, chat_id, datetime.now()))

    room_name = str(chat_id)
    join_room(room_name)

    print(f'Private chat room created: {room_name}')


@socketio.on('send_message', namespace='/chat')
def handle_send_message(data):
    try:
        user1_id = data['user1_id']
        chat_id = data['chat_id']
        sender_id = uuid.UUID(user1_id)
        content = data['message']
        message_id = uuid.uuid4()
        timestamp = datetime.now()
        type = data['type']

        print(f"MessId: {message_id}")
        print(f"chat_id: {chat_id}")
        print(f"sender_id: {sender_id}")
        print(f"content: {content}")
        print(f"timestamp: {timestamp}")

        insert_query = """
            INSERT INTO messages (message_id, chat_id, content, seen_at, sender_id, timestamp, type)
            VALUES (%s, %s, %s, %s, %s, %s, %s)
        """

        session.execute(insert_query, (message_id, uuid.UUID(chat_id), content, timestamp, sender_id, timestamp, type))

        room_name = chat_id
        emit('receive_message', data['message'], room=room_name, namespace='/chat')
        return jsonify({'message': 'User chat table created', 'status': 200})
    
    except AssertionError as e:
        print(f"AssertionError: {e}")


@socketio.on('receive_message', namespace='/chat')
def handle_receive_message(data):
    try:
        print(f"message is: {data}")
        user1_id = data['user1_id']
        user2_id = data['user2_id']
        room_name = f'private_chat_{user1_id}_{user2_id}'

        emit('message_received', {'message': 'Message received successfully'}, room=room_name, namespace='/chat')
    except AssertionError as e:
        print(f"AssertionError: {e}")



@app.route('/')
def index():
    return render_template('index.html')

# @app.route('/users/chat/<user1_id>&<user2_id>', methods=['GET'])
# def get_chat_id(user1_id, user2_id):
#     try:

#         select_query = """
#             SELECT chat_id
#             FROM user_chat
#             WHERE user_id = %s ALLOW FILTERING;
#         """

#         print(user1_id)
#         print(user2_id)

#         # Fetch chat_id for user1
#         result_user1 = set(row.chat_id for row in session.execute(select_query, (uuid.UUID(user1_id),)))

#         # Fetch chat_id for user2
#         result_user2 = set(row.chat_id for row in session.execute(select_query, (uuid.UUID(user2_id),)))

#         print(result_user1)
#         print(result_user2)
        
#         common_chat_ids = result_user1.intersection(result_user2)

#         if common_chat_ids:
#             print(common_chat_ids)
#             return jsonify({'message': 'User chat table already exists', 'status': 200})

#         user_chat_id1 = uuid.uuid4()
#         user_chat_id2 = uuid.uuid4()

#         user1_id_uuid = uuid.UUID(user1_id)
#         user2_id_uuid = uuid.UUID(user2_id)
        
#         chat_id = uuid.uuid4()
        
#         insert_query_user = """
#             INSERT INTO user_chat (user_chat_id, user_id, chat_id, timestamp)
#             VALUES (%s, %s, %s, %s)
#         """
#         session.execute(insert_query_user, (user_chat_id1, user1_id_uuid, chat_id, datetime.now()))
#         session.execute(insert_query_user, (user_chat_id2, user2_id_uuid, chat_id, datetime.now()))

#         return jsonify({'message': 'User chat table created', 'status': 200})

        
#     except Exception as e:
#         return jsonify({'error': str(e), 'status': 500}), 500


if __name__ == '__main__':
    socketio.run(app, debug=True)
