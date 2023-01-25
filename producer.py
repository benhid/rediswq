import json
import os
import sys
import uuid

import rediswq

QUEUE_NAME = os.getenv("QUEUE_NAME", "job")
REDIS_HOST = os.getenv("REDIS_HOST", "localhost")
REDIS_PORT = os.getenv("REDIS_PORT", "6378")

if len(sys.argv) != 2:
    print("Usage: python producer.py <n>")
    sys.exit(1)

n_jobs = int(sys.argv[1])

q = rediswq.RedisWQ(name=QUEUE_NAME, host=REDIS_HOST, port=REDIS_PORT)
print("Connected to Redis at: " + REDIS_HOST + ":" + REDIS_PORT)


def get_item() -> dict:
    return {
        # This UUID simulates the user/service that submitted the item.
        "requestId": uuid.uuid4().hex,
        # Unique ID for this item.
        "itemId": uuid.uuid4().hex,
        # Image to run.
        "image": "hello-world",
    }


for _ in range(n_jobs):
    item = get_item()
    print("Pushing item: " + item["itemId"])

    q.push(json.dumps(item))
