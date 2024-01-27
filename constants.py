
create_keyspace_query = """
    CREATE KEYSPACE IF NOT EXISTS chat_application_user_service
    WITH replication = {'class': 'SimpleStrategy', 'replication_factor': 1};
"""

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

