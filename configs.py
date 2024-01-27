from cassandra.auth import PlainTextAuthProvider

cassandra_config = {
    "contact_points": ["127.0.0.1"],
    "auth_provider": PlainTextAuthProvider(username="abhinav", password="12345"),
    "keyspace": "chat_app",
}