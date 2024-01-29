import logging
import uuid
from datetime import datetime
from functools import lru_cache

import redis
from gevent import monkey

monkey.patch_all()

from datetime import datetime

from cassandra.cluster import Cluster
from confluent_kafka import Producer
from flask import Flask, json, jsonify, render_template, request
from flask_cors import CORS
from flask_socketio import SocketIO, emit, join_room

from configs import cassandra_config
from constants import (
    create_index_on_chat_id,
    create_index_on_timestamp,
    create_keyspace_query,
    create_message_table_query,
    create_user_chat_table_query,
)
from Models import GetUserMessages, Message, MessagesService
from utills import FLASK_SECRET_KEY

redis_client = redis.StrictRedis(host="localhost", port=6379, decode_responses=True)

app = Flask(__name__)
app.config["SECRET_KEY"] = FLASK_SECRET_KEY

logging.basicConfig(level=logging.INFO)

cluster = Cluster(
    contact_points=cassandra_config["contact_points"],
    auth_provider=cassandra_config["auth_provider"],
)


session = cluster.connect()
session.set_keyspace(cassandra_config["keyspace"])

socketio = SocketIO(app, cors_allowed_origins="*")


producer_config = {"bootstrap.servers": "localhost:9092"}
producer = Producer(producer_config)

CORS(app)


# session.execute(create_message_table_query)
# session.execute(create_index_on_sender_id)
# session.execute(create_index_on_chat_id)
# session.execute(create_index_on_timestamp)


@socketio.on("connect", namespace="/chat")
def handle_connect():
    user_id = request.sid
    logging.info(f"User connected: {user_id}")


@socketio.on("disconnect", namespace="/chat")
def handle_disconnect():
    user_id = request.sid
    logging.info(f"User disconnected: {user_id}")


@socketio.on("start_private_chat", namespace="/chat")
def start_private_chat(data):
    sender_id = data["sender_id"]
    receiver_id = data["receiver_id"]
    chat_id = uuid.uuid4()

    logging.info(f"initial chat_id: {chat_id}")

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
        logging.info(f"common chat found: {common_chat_id}")
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

    # save chat_id to the session

    logging.info(f"Private chat room created: {room_name}")

    emit("private_chat_room_created", room_name, namespace="/chat")


@socketio.on("send_message", namespace="/chat")
def handle_send_message(data):
    try:
        chat_id = data["chat_id"]
        sender_id = uuid.UUID(data["sender_id"])
        content = data["message"]
        message_id = uuid.uuid4()
        timestamp = datetime.now()
        type = data["type"]

        logging.info(f"MessId: {message_id}")
        logging.info(f"chat_id: {chat_id}")
        logging.info(f"sender_id: {sender_id}")
        logging.info(f"content: {content}")
        logging.info(f"timestamp: {timestamp}")

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

        kafka_message = {"header": f"New message from: {sender_id}", "body": content}
        producer.produce("received_messages", value=json.dumps(kafka_message))
        producer.flush()
        return jsonify({"message": "User chat table created", "status": 200})

    except AssertionError as e:
        logging.info(f"AssertionError: {e}")


@socketio.on("receive_message", namespace="/chat")
def handle_receive_message(data):
    try:
        logging.info(f"message is: {data}")
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
        logging.info(f"AssertionError: {e}")


@app.route("/")
def index():
    return render_template("index.html")


@app.route("/users/chat/", methods=["GET"])
def get_user_chats():
    try:
        user_id = request.args.get("user_id")

        if not user_id:
            return jsonify({"error": "User ID is required.", "status": 400}), 400

        chat_ids = get_user_chats_cached(user_id)
        return jsonify({"chat_ids": chat_ids, "status": 200})

    except Exception as e:
        return jsonify({"error": str(e), "status": 500}), 500


@lru_cache(maxsize=128)
def get_user_chats_cached(user_id):
    select_query = """
        SELECT chat_id
        FROM user_chat
        WHERE user_id = %s ALLOW FILTERING;
    """

    result = session.execute(select_query, (uuid.UUID(user_id),))
    return [row.chat_id for row in result]


# @app.route("/user/update_read_receipts", methods=["GET"])
# def get_user_chats():
#     try:
#         user_id = request.args.get("user_id")

#         if not user_id:
#             return jsonify({"error": "User ID is required.", "status": 400}), 400

#         select_query = """
#             SELECT chat_id
#             FROM user_chat
#             WHERE user_id = %s ALLOW FILTERING;
#         """

#         result = session.execute(select_query, (uuid.UUID(user_id),))
#         chat_ids = [row.chat_id for row in result]
#         return jsonify({"chat_ids": chat_ids, "status": 200})

#     except Exception as e:
#         return jsonify({"error": str(e), "status": 500}), 500


@app.route("/users/chat/<chat_id>", methods=["POST"])
def get_chat_messages(chat_id):
    try:
        data = request.get_json()
        paging_state_id = data.get("paging_state_id", None)
        starting_timestamp_str = data.get("starting_timestamp_str")

        fs = data.get("fetch_size", 5)
        fetch_size = int(fs)

        logging.info(f"data: {data}")

        logging.info(f"paging_id from the client: {paging_state_id}")
        paging_state = None

        if paging_state_id:
            paging_state = redis_client.get(paging_state_id)

        logging.info(f"paging state from cache: {paging_state}")

        timestamp_format = "%Y-%m-%d %H:%M:%S.%f"

        starting_timestamp = None
        if starting_timestamp_str:
            # timestamp_str = "Sat, 27 Jan 2024 15:26:40 GMT"
            # # Parse the provided timestamp string into a datetime object
            # timestamp_obj = datetime.strptime(
            #     starting_timestamp_str, "%a, %d %b %Y %H:%M:%S %Z"
            # )

            # # Format the datetime object into the desired format
            # formatted_timestamp = timestamp_obj.strftime("%Y-%m-%d %H:%M:%S")

            starting_timestamp = datetime.strptime(
                starting_timestamp_str, timestamp_format
            )

        message_service = MessagesService(session)
        user_messages = message_service.get_user_messages(
            chat_id, fetch_size, starting_timestamp, paging_state
        )

        # logging.info(f"user_messages: {user_messages.messages}")
        logging.info(f"paging state: {user_messages.paging_state}")

        messages = user_messages.messages
        next_paging_state = user_messages.paging_state

        if next_paging_state == "":
            return jsonify({"user_messages": messages}), 200

        next_paging_state_id = str(uuid.uuid4())
        redis_client.set(next_paging_state_id, next_paging_state)

        logging.info(messages)

        for message in messages:
            message["timestamp"] = message["timestamp"].strftime(
                "%Y-%m-%d %H:%M:%S.%f%z"
            )

        return (
            jsonify(
                {
                    "user_messages": messages,
                    "next_paging_state_id": next_paging_state_id,
                }
            ),
            200,
        )

    except Exception as e:
        logging.info(f"exception: {e}")
        return jsonify({"error": str(e), "status": 500}), 500


if __name__ == "__main__":
    socketio.run(app, debug=True)
