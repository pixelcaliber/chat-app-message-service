# chat-app-message-service
Part of chat-application microservices
- enables one-to-one messaging using websockets protcols
- load balanced using nginx
- uses 3 node-redis cluster for caching
- uses Cassandra as database for storing messages
- produces events into kafka streams whenever a new message is send by the user to create notifications using firebase
- connects with other microservices such as user-service, user-presence-service, notification-service

tech-stack: Cassandra, Python, Flask, Redis, NGINX, Kafka, Firebase, Websockets

### Additionally, whenever a user sends a message, we generate notification with message details using Firebase Cloud Messaging and Kafka for scalability, based on the FCM token of users' device, refer: notification service repo for more details
- so, this service is a producer of kafka notification events, we are pushing those events into a topic for worker to consume and generate notifications on user devices upon new messages

### Cassandra

For storing messages, we'll consider using a NoSQL database, such as Cassandra.  Since it is a distributed database, Cassandra can (and usually does) have multiple nodes. A node represents a single instance of Cassandra. These nodes communicate with one another through a protocol called gossip, which is a process of computer peer-to-peer communication. Cassandra also has a masterless architecture – any node in the database can provide the exact same functionality as any other node – contributing to Cassandra’s robustness and resilience. Multiple nodes can be organized logically into a cluster, or "ring".

Through multiple nodes we can easily scale out or horizontally scale the database.

In Cassandra, the data itself is automatically distributed using partitions. Each node owns a particular set of tokens, and Cassandra distributes data based on the ranges of these tokens across the cluster. The partition key is responsible for distributing data among nodes and is important for determining data locality. When data is inserted into the cluster, the first step is to apply a hash function to the partition key. The output is used to determine what node (based on the token range) will get the data.

```
CREATE TABLE IF NOT EXISTS messages (
        message_id UUID,
        chat_id UUID,
        sender_id UUID,
        type TEXT,
        timestamp TIMESTAMP,
        content TEXT,
        seen_at TIMESTAMP,
        PRIMARY KEY ((chat_id), timestamp, message_id)
    )
    WITH CLUSTERING ORDER BY(timestamp DESC);
```
* 'chat_id' will be the partition key and timestamp, message_id the clustering key. 
* We specified timestamp DESC inside of CLUSTERING ORDER BY. It's important to note that 'message_id' will serve for uniqueness purposes in this design.


### Message Service:

1. It's be a python flask application that handles the one-to-one messaging feature.
2. To handle high loads, we've deployed multiple instances of the message service and utilized load balancers to distribute incoming traffic evenly across these instances, ensuring optimal performance and scalability.
3. For storing messages, we've considered using a NoSQL database, such as "Cassandra". 
4. Since it is a distributed database, Cassandra can (and usually does) have multiple nodes. See “Cassandra Component“ section for more details.
5. To enable real-time messaging, we've integrated WebSocket connections, allowing for bi-directional communication between clients and servers. 
6. Retrieving chat history involves querying the database for messages associated with the relevant users. We've implemented pagination to display messages in batches, along with a "load more messages" button feature to fetch additional messages as needed.
7. The messages should also be stored hashed and not be visible it should be encrypted.
8. To enhance performance, we've implemented caching to store the most recent chats in redis. This cached data will be quickly accessible upon user login, providing a seamless and responsive user experience.


### API Contracts:

```
GET: /users/chat?user_id={user_id}

- returns the chat_ids of all the chats user is part of 

GET: /users/chat/{chat_id}

- returns the messages of a chat with particular chat_id 
- sort the messages based on timestamp from newest to oldest
```

### Pagination in cassandra:

We wanted to achieve pagination that is not showing all the messages to the user at once but splitting it into the pages. So, we wanted to fetch from our cassandra server only few messages of some size “chunks”, to speed up the process of fetching messages and loading chat history. Idea was to further store them in cache so, that they can get loaded pretty quickly when user visits the chat history.

Let's first understand how smartly SELECT * query is implemented in Cassandra. Suppose, you have a table with ~1B rows and you run -

SELECT * FROM my_cassandra_table;

Loading all the 1B rows into the memory is very tedious. Cassandra does it in a very smart way with fetching data in pages. so you don't have to worry about the memory. It just fetches a chunk from the database (~ 5000 rows) and returns a cursor for results on which you can iterate, to see the rows. 

Once our iteration reaches close to 5000, it again fetches the next chunk of 5000 rows internally and adds it to the result cursor. It does it so brilliantly that we don’t even feel this magic happening behind the scene.

When I deep-dived into Cassandra configurations I found that whenever Cassandra returns a result cursor, it brings a page state with it. Page state is nothing but a page number to help Cassandra remember which chunk to fetch next.

```
from cassandra.query import SimpleStatement

query = "SELECT * FROM my_cassandra_table;"

statement = SimpleStatement(query, fetch_size=100)
results = session.execute(statement)

# save page state
page_state = results.paging_state

for data in results:
    process_data_here(data)
```

* Based on our use case, we set the fetch size (it is the size of the chunk, manually given by us to Cassandra). And when we got the result cursor, we saved the page state in a variable.
* We put a check on the counter. If it exceeds the manual chunk size, it breaks and again fetches a fresh new chunk with the page state already saved.
* We saved the page_state in the redis, whenever the user press the load more button we get the latest page_state from the redis and use it to move forward the page_state cursor.


