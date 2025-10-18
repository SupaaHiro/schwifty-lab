import os
import redis

host = os.getenv("REDIS_HOST", "redis")
port = int(os.getenv("REDIS_PORT", "6379"))
timeout = int(os.getenv("REDIS_TIMEOUT", "10"))

try:
    client = redis.Redis(
        host=host,
        port=port,
        socket_connect_timeout=timeout,
        socket_timeout=timeout
    )
    client.ping()
    print(f"✅ Connected to Redis at {host}:{port} (timeout={timeout}s)")
except Exception as e:
    print(f"❌ Failed to connect to Redis: {e}")
