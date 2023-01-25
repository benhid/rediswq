import json
import os
import time

import docker

import rediswq

QUEUE_NAME = os.getenv("QUEUE_NAME", "job")
REDIS_HOST = os.getenv("REDIS_HOST", "localhost")
REDIS_PORT = os.getenv("REDIS_PORT", "6378")

print("Waiting for 'DOCKER_HOST' to be ready")

# Sometimes the Docker daemon takes a while to start up.
# Wait for it to be ready a fixed amount of time before continuing.
# TODO - Find a better way to do this.
time.sleep(30)

client = docker.from_env()

q = rediswq.RedisWQ(name=QUEUE_NAME, host=REDIS_HOST, port=REDIS_PORT)
print("Connected to Redis at: " + REDIS_HOST + ":" + REDIS_PORT)
print(q)

while True:
    item = q.lease(lease_secs=120, block=True, timeout=2)
    if item:
        try:
            item_dic = json.loads(item.decode("utf-8"))
            print("Processing request from " + item_dic["requestId"])

            container = client.containers.run(item_dic["image"], detach=True)
            print("Running container: " + container.id)

            container.wait()
            logs = container.logs()
            print("Container logs: " + logs.decode("utf-8"))

            container.remove()
        except Exception as e:
            print("Error processing item: " + str(e))
        finally:
            q.complete(item)
    else:
        q.check_expired_leases()
        print("Waiting for work")
    time.sleep(1.0)
