from cassandra.auth import PlainTextAuthProvider

cassandra_config = {
    "contact_points": ["127.0.0.1"],
    "auth_provider": PlainTextAuthProvider(username="abhinav", password="12345"),
    "keyspace": "chat_app",
}

# curl -X POST "${ES_URL}/_bulk?pretty" \
#   -H "Authorization: ApiKey "${API_KEY}"" \
#   -H "Content-Type: application/json" \
#   -d'
# { "index" : { "_index" : "index_name" } }
# {"name": "Snow Crash", "author": "Neal Stephenson", "release_date": "1992-06-01", "page_count": 470}
# { "index" : { "_index" : "index_name" } }
# {"name": "Revelation Space", "author": "Alastair Reynolds", "release_date": "2000-03-15", "page_count": 585}
# { "index" : { "_index" : "index_name" } }
# {"name": "1984", "author": "George Orwell", "release_date": "1985-06-01", "page_count": 328}
# { "index" : { "_index" : "index_name" } }
# {"name": "Fahrenheit 451", "author": "Ray Bradbury", "release_date": "1953-10-15", "page_count": 227}
# { "index" : { "_index" : "index_name" } }
# {"name": "Brave New World", "author": "Aldous Huxley", "release_date": "1932-06-01", "page_count": 268}
# { "index" : { "_index" : "index_name" } }
# {"name": "The Handmaid'"'"'s Tale", "author": "Margaret Atwood", "release_date": "1985-06-01", "page_count": 311}
# '

# curl -X PUT  "http://localhost:9200/chat_app" -H "Content-Type: application/json" -d '{  "settings" : { "keyspace" : "chat_app" } },  "mappings":{      "messages":{         "properties":{            "username":{               "type":"string",             "index":"not_analyzed"          },          "chat_id":{               "type":"keyword",             "index":"not_analyzed"          },          "type":{               "type":"string",             "index":"not_analyzed"          },          "content":{               "type":"string",             "index":"not_analyzed"          },          "timestamp":{               "type":"date",             "index":"not_analyzed"          },          "sender_id":{               "type":"keyword",             "index":"not_analyzed"          },          "seen_at":{               "type":"date",             "index":"not_analyzed"          }       }    } }}'


# curl -X PUT -H "Content-Type: application/json" "http://localhost:9200/chat_app/_mapping/messages" -d '{
#     "messages" : {
#         "discover" : "[a-zA-Z].*",
#         "properties" : {
#             "content" : {
#                 "type" : "string",
#                 "index" : "analyzed"
#             }
#         }
#     }
# }'

# curl -X PUT "http://localhost:9200/twitter" -H "Content-Type: application/json" -d '{
#    "settings" : { "keyspace" : "twitter" } },
#    "mappings":{
#      "user":{
#         "properties":{
#            "username":{
#               "type":"string",
#               "index":"not_analyzed"
#            },
#            "mail":{
#               "type":"string",
#               "index":"not_analyzed"
#            }
#         }
#      }
#   }
# }'

# curl -X PUT "http://localhost:9200/twitter/_mapping/user"  -H "Content-Type: application/json" -d '{
#     "user" : {
#         "discover" : "[a-zA-Z].*",
#         "properties" : {
#             "name" : {
#                 "type" : "string",
#                 "index" : "analyzed"
#             }
#         }
#     }
# }'
