# chat-app-message-service
Part of chat-application microservices
- enables one-to-one messaging using websockets protcols
- load balanced using nginx
- uses 3 node-redis cluster for caching
- uses Cassandra as database for storing messages
- produces events into kafka streams whenever a new message is send by the user to create notifications using firebase
- connects with other microservices such as user-service, user-presence-service, notification-service

tech-stack: Cassandra, Python, Flask, Redis, NGINX, Kafka, Firebase, Websockets
