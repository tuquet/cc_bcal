# Trong main.py hoặc app_core.py
import redis

# Kết nối đến Redis server
redis_client = redis.Redis(host='localhost', port=6379, db=0)
pubsub = redis_client.pubsub()

# Thay thế SSE_QUEUE bằng Redis
# Khi cần gửi cập nhật:
# SSE_QUEUE.put(...)  ->  redis_client.publish('job_updates', json.dumps(update))

# Trong event_stream():
# update = SSE_QUEUE.get() ->
# for message in pubsub.listen():
#     if message['type'] == 'message':
#         update = json.loads(message['data'])
#         # ... yield update
