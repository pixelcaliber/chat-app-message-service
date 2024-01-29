import codecs
import io
import logging
import uuid


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


class GetUserMessages:
    def __init__(self, paging_state, messages):
        self.paging_state = paging_state
        self.messages = messages


class MessagesService(object):
    """Provides methods that implement functionality of the message Service."""

    def __init__(self, session):
        self.session = session
        self.user_message_startingPointPrepared = session.prepare(
            "SELECT * FROM messages WHERE chat_id = ? AND (timestamp) <= (?) ALLOW FILTERING"
        )
        self.user_message_noStartingPointPrepared = session.prepare(
            "SELECT * FROM messages WHERE chat_id = ? ALLOW FILTERING"
        )

    def get_user_messages(self, chat_id, page_size, starting_timestamp, paging_state):
        if page_size <= 0:
            raise ValueError(
                "Page size should be strictly positive for get user comments"
            )

        results = list()
        next_page_state = ""

        bound_statement = None

        if starting_timestamp:
            bound_statement = self.user_message_startingPointPrepared.bind(
                [uuid.UUID(chat_id), starting_timestamp]
            )
        else:
            bound_statement = self.user_message_noStartingPointPrepared.bind(
                [uuid.UUID(chat_id)]
            )

        logging.info("Current query is: " + str(bound_statement))

        bound_statement.fetch_size = page_size
        result_set = None

        if paging_state:
            result_set = self.session.execute(
                bound_statement, paging_state=codecs.decode(paging_state, "hex")
            )
        else:
            result_set = self.session.execute(bound_statement)

        logging.info(result_set)
        current_rows = result_set.current_rows

        remaining = len(current_rows)

        for message_row in current_rows:
            # logging.info(f'next user comment is: {message_row}')
            message = {
                "message_id": str(message_row.message_id),
                "content": message_row.content,
                "sender_id": str(message_row.sender_id),
                "timestamp": message_row.timestamp,
            }
            results.append(message)

            remaining -= 1
            if remaining == 0:
                break

        if len(results) == page_size:
            next_page_state = codecs.encode(result_set.paging_state, "hex")
        return GetUserMessages(paging_state=next_page_state, messages=results)
