import io
import uuid
from datetime import datetime

import redis
from gevent import monkey

monkey.patch_all()

import codecs
import logging
from datetime import datetime

from cassandra.auth import PlainTextAuthProvider
from cassandra.cluster import Cluster
from cassandra.query import SimpleStatement
from flask import Flask, jsonify, render_template, request, send_file
from flask_cors import CORS
from flask_migrate import Migrate
from flask_socketio import SocketIO, emit, join_room

redis_client = redis.StrictRedis(host='localhost', port=6379, decode_responses=True)

app = Flask(__name__)
app.config[
    "SECRET_KEY"
] = "asda!@%^213adaw#3as@!@#!#nksndak12313asd1@@nm2%^&*#nasmadk231m132m"

cassandra_config = {
    "contact_points": ["127.0.0.1"],  # the IP address of your Cassandra node
    "auth_provider": PlainTextAuthProvider(username="abhinav", password="12345"),
    "keyspace": "chat_app",
}


cluster = Cluster(
    contact_points=cassandra_config["contact_points"],
    auth_provider=cassandra_config["auth_provider"],
)
session = cluster.connect()

session.set_keyspace(cassandra_config["keyspace"])

socketio = SocketIO(app, cors_allowed_origins="*")


CORS(app)


class Message:
    def __init__(
        self, message_id, chat_id, content, seen_at, sender_id, timestamp, type
    ):  # messages (message_id, chat_id, content, sender_id, timestamp, type)
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

# create_message_table_query = """
# CREATE TABLE IF NOT EXISTS messages (
#     message_id UUID PRIMARY KEY,
#     chat_id UUID,
#     sender_id UUID,
#     type TEXT,
#     timestamp TIMESTAMP,
#     content TEXT,
#     seen_at TIMESTAMP
# );

# """

create_message_table_query = """
CREATE TABLE IF NOT EXISTS messages (
        message_id UUID,
        chat_id UUID,
        sender_id UUID,
        type TEXT,
        timestamp TIMESTAMP,
        content TEXT,
        seen_at TIMESTAMP,
        PRIMARY KEY ((chat_id, sender_id), timestamp, message_id)
    )
    WITH CLUSTERING ORDER BY(timestamp DESC);
"""


# CREATE TABLE IF NOT EXISTS chat_by_day(
#   day TEXT,
#   id UUID,
#   time timestamp,
#   idSender UUID,
#   message TEXT,
#   PRIMARY KEY ((day),time,id))
# WITH CLUSTERING ORDER BY(time DESC,id ASC);

create_index_on_sender_id = """
CREATE INDEX IF NOT EXISTS idx_sender_id ON messages (sender_id, timestamp);
"""
create_index_on_chat_id = """
CREATE INDEX IF NOT EXISTS idx_chat_id ON messages (chat_id, timestamp);
"""


create_user_chat_table_query = """
    CREATE TABLE IF NOT EXISTS user_chat (
    user_chat_id UUID,
    user_id UUID,
    chat_id UUID,
    timestamp TIMESTAMP,
    PRIMARY KEY (user_id, chat_id)
);
"""

session.execute(create_message_table_query)
session.execute(create_index_on_sender_id)
session.execute(create_index_on_chat_id)


@socketio.on("connect", namespace="/chat")
def handle_connect():
    user_id = (
        request.sid
    )  # Unique identifier for the user (replace this with your authentication logic)
    print(f"User connected: {user_id}")


@socketio.on("disconnect", namespace="/chat")
def handle_disconnect():
    user_id = (
        request.sid
    )  # Unique identifier for the user (replace this with your authentication logic)
    print(f"User disconnected: {user_id}")


@socketio.on("start_private_chat", namespace="/chat")
def start_private_chat(data):
    sender_id = data["sender_id"]
    receiver_id = data["receiver_id"]
    chat_id = uuid.uuid4()

    print(f"initial chat_id: {chat_id}")

    select_query = """
        SELECT chat_id
        FROM user_chat
        WHERE user_id = %s ALLOW FILTERING;
    """

    result_user1 = set(
        row.chat_id for row in session.execute(select_query, (uuid.UUID(sender_id),))
    )
    result_user2 = set(
        row.chat_id for row in session.execute(select_query, (uuid.UUID(receiver_id),))
    )

    common_chat_ids = result_user1.intersection(result_user2)
    common_chat_id = common_chat_ids.pop() if common_chat_ids else None

    if common_chat_id:
        print(f"common chat found: {common_chat_id}")
        chat_id = common_chat_id
    else:
        user_chat_id1 = uuid.uuid4()
        user_chat_id2 = uuid.uuid4()

        sender_id_uuid = uuid.UUID(sender_id)
        receiver_id_uuid = uuid.UUID(receiver_id)

        insert_query_user = """
            INSERT INTO user_chat (user_chat_id, user_id, chat_id, timestamp)
            VALUES (%s, %s, %s, %s)
        """
        session.execute(
            insert_query_user, (user_chat_id1, sender_id_uuid, chat_id, datetime.now())
        )
        session.execute(
            insert_query_user,
            (user_chat_id2, receiver_id_uuid, chat_id, datetime.now()),
        )

    room_name = str(chat_id)
    join_room(room_name)

    print(f"Private chat room created: {room_name}")


@socketio.on("send_message", namespace="/chat")
def handle_send_message(data):
    try:
        chat_id = data["chat_id"]
        sender_id = uuid.UUID(data["sender_id"])
        content = data["message"]
        message_id = uuid.uuid4()
        timestamp = datetime.now()
        type = data["type"]

        print(f"MessId: {message_id}")
        print(f"chat_id: {chat_id}")
        print(f"sender_id: {sender_id}")
        print(f"content: {content}")
        print(f"timestamp: {timestamp}")

        insert_query = """
            INSERT INTO messages (message_id, chat_id, content, seen_at, sender_id, timestamp, type)
            VALUES (%s, %s, %s, %s, %s, %s, %s)
        """

        session.execute(
            insert_query,
            (
                message_id,
                uuid.UUID(chat_id),
                content,
                timestamp,
                sender_id,
                timestamp,
                type,
            ),
        )

        room_name = chat_id
        emit("receive_message", data["message"], room=room_name, namespace="/chat")
        return jsonify({"message": "User chat table created", "status": 200})

    except AssertionError as e:
        print(f"AssertionError: {e}")


@socketio.on("receive_message", namespace="/chat")
def handle_receive_message(data):
    try:
        print(f"message is: {data}")
        sender_id = data["sender_id"]
        receiver_id = data["receiver_id"]
        room_name = f"private_chat_{sender_id}_{receiver_id}"

        emit(
            "message_received",
            {"message": "Message received successfully"},
            room=room_name,
            namespace="/chat",
        )
    except AssertionError as e:
        print(f"AssertionError: {e}")


@app.route("/")
def index():
    return render_template("index.html")


@app.route("/users/chat/", methods=["GET"])
def get_user_chats():
    try:
        user_id = request.args.get("user_id")

        if not user_id:
            return jsonify({"error": "User ID is required.", "status": 400}), 400

        select_query = """
            SELECT chat_id
            FROM user_chat
            WHERE user_id = %s ALLOW FILTERING;
        """

        result = session.execute(select_query, (uuid.UUID(user_id),))
        chat_ids = [row.chat_id for row in result]
        return jsonify({"chat_ids": chat_ids, "status": 200})

    except Exception as e:
        return jsonify({"error": str(e), "status": 500}), 500


class GetUserMessages():
   def __init__(self, paging_state, messages):
       self.paging_state = paging_state
       self.messages = messages

class MessagesService(object):
    """Provides methods that implement functionality of the message Service."""

    def __init__(self, session):

        self.session = session
        self.user_message_startingPointPrepared = session.prepare('SELECT * FROM messages WHERE chat_id = ? AND (timestamp) <= (?) ALLOW FILTERING')
        self.user_message_noStartingPointPrepared = session.prepare('SELECT * FROM messages WHERE chat_id = ? ALLOW FILTERING')


    def get_user_messages(self, chat_id, page_size, starting_timestamp, paging_state):
        if page_size <= 0:
            raise ValueError('Page size should be strictly positive for get user comments')

        results = list()
        next_page_state = ''

        bound_statement = None

        if starting_timestamp:
            bound_statement = self.user_message_startingPointPrepared.bind([uuid.UUID(chat_id), starting_timestamp])
        else:
            bound_statement = self.user_message_noStartingPointPrepared.bind([uuid.UUID(chat_id)])

        # print('Current query is: ' + str(bound_statement))

        bound_statement.fetch_size = page_size
        result_set = None
        
        if paging_state:
            result_set = self.session.execute(bound_statement, paging_state=codecs.decode(paging_state, 'hex'))
        else:
            result_set = self.session.execute(bound_statement)

        # print(result_set)
        current_rows = result_set.current_rows

        remaining = len(current_rows)

        for message_row in current_rows:
            # print(f'next user comment is: {message_row}')
            message = {
                "message_id": str(message_row.message_id),
                "content": message_row.content,
                "sender_id": str(message_row.sender_id),
                "timestamp": message_row.timestamp,
            }
            results.append(message)

            remaining -= 1
            if (remaining == 0):
                break

        if len(results) == page_size:
            next_page_state = codecs.encode(result_set.paging_state, 'hex')
        return GetUserMessages(paging_state=next_page_state, messages=results)
        

@app.route("/users/chat/<chat_id>", methods=["POST"])
def get_chat_messages(chat_id):
    try:
        data = request.get_json()
        paging_state_id = data.get("paging_state_id", None)
        starting_timestamp_str = data.get("starting_timestamp_str", None)
        fs = data.get("fetch_size", 5)
        fetch_size=int(fs)

        print(f"paging_id from the client: {paging_state_id}")
        paging_state = redis_client.get(paging_state_id)
        print(f"paging state from cache: {paging_state}")

        timestamp_format = "%Y-%m-%d %H:%M:%S.%f%z"

        starting_timestamp = None
        if starting_timestamp_str:
            starting_timestamp = datetime.strptime(starting_timestamp_str, timestamp_format)

        message_service = MessagesService(session)
        user_messages = message_service.get_user_messages(chat_id, fetch_size, starting_timestamp, paging_state)

        # print(f"user_messages: {user_messages.messages}")
        print(f"paging state: {user_messages.paging_state}")

        messages = user_messages.messages
        next_paging_state = user_messages.paging_state

        if next_paging_state == "":
            return jsonify({"user_messages": messages}), 200
        
        next_paging_state_id = str(uuid.uuid4())
        redis_client.set(next_paging_state_id, next_paging_state)

        return jsonify({"user_messages": messages, "next_paging_state_id": next_paging_state_id}), 200

    except Exception as e:
        return jsonify({"error": str(e), "status": 500}), 500

# def fetch_a_fresh_chunk(chat_id, sender_id, fetch_size, paging_state=None):
#     query = "SELECT * FROM messages;"
#     statement = SimpleStatement(query, fetch_size=fetch_size)
    # results = session.execute(statement, paging_state=paging_state)
    # result_messages = session.execute(
    #     statement, paging_state=paging_state
    # )

    # Check if there are more pages available
    # next_page_available = True if result_messages.paging_state else False

    # return result_messages, result_messages.paging_state
    # try:
    # page_size = request.args.get('page_size', default=30, type=int)
    # page_number = request.args.get('page_number', default=1, type=int)
    # sender_id = request.args.get('sender_id')

    # offset = (page_number - 1) * page_size

    # select_messages_query = """
    #     SELECT message_id, content, chat_id, sender_id, timestamp
    #     FROM messages
    #     WHERE chat_id = %s AND sender_id = %s
    #     AND token(sender_id, timestamp) > token(%s, (SELECT max(timestamp) FROM messages WHERE chat_id = %s AND sender_id = %s))
    #     ORDER BY timestamp DESC
    #     LIMIT %s;
    # """

    result_messages = session.execute(
        select_messages_query,
        (
            uuid.UUID(chat_id),
            uuid.UUID(sender_id),
            uuid.UUID(chat_id),
            uuid.UUID(chat_id),
            uuid.UUID(sender_id),
            page_size,
        ),
    )

    # select_messages_query = """
    #     SELECT message_id, content, chat_id, sender_id, timestamp
    #     FROM messages
    #     WHERE chat_id = %s AND sender_id = %s
    #     ORDER BY timestamp DESC
    #     LIMIT %s ALLOW FILTERING;
    # """

    # result_messages = session.execute(select_messages_query, (uuid.UUID(chat_id), uuid.UUID(sender_id), page_size))

    # select_messages_query = """
    #     SELECT message_id, content, chat_id, sender_id, timestamp
    #     FROM messages
    #     WHERE chat_id = %s
    #     ALLOW FILTERING;
    # """

    # result_messages = session.execute(select_messages_query, (uuid.UUID(chat_id),))

    #     messages = [
    #         {
    #             "message_id": str(row.message_id),
    #             "content": row.content,
    #             "sender_id": str(row.sender_id),
    #             "timestamp": row.timestamp,
    #         }
    #         for row in result_messages
    #     ]

    #     return jsonify({"messages": messages, "status": 200})

    # except Exception as e:
    #     return jsonify({"error": str(e), "status": 500}), 500


if __name__ == "__main__":
    socketio.run(app, debug=True)
