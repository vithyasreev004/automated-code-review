import redis

# Connect to Redis server
r = redis.Redis(host='localhost', port=6379, db=0)

# Test connection
print(r.ping())  # should print True

# Example: store and retrieve a session summary
r.set("latest_session", "repo=automated-code-review, confidence=0.87")
print(r.get("latest_session"))  # should print b'repo=automated-code-review, confidence=0.87'
