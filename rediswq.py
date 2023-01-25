# Based on http://peter-hoffmann.com/2012/python-simple-queue-redis-queue.html
# and the suggestion in the redis documentation for RPOPLPUSH, at
# http://redis.io/commands/rpoplpush, which suggests how to implement a work-queue.

import hashlib
import uuid
from typing import Union

import redis


class RedisWQ:

    def __init__(self, name: str, **redis_kwargs):
        """The work queue is identified by "name". The library may create other
        keys with "name" as a prefix.
        """
        self.client = redis.StrictRedis(**redis_kwargs)
        # The session ID will uniquely identify this "worker".
        self.session = uuid.uuid4().hex
        # Work queue is implemented as two queues: main, and processing.
        # Work is initially in main, and moved to processing when a client picks it up.
        self.main_q_key = name
        self.processing_q_key = name + ":processing"
        self.lease_key_prefix = name + ":leased_by_session:"

    def size(self):
        """Return the size of the main queue."""
        return self.client.llen(self.main_q_key)

    def processing_size(self):
        """Return the size of the main queue."""
        return self.client.llen(self.processing_q_key)

    def empty(self):
        """Return True if the queue is empty, including work being done, False otherwise.

        False does not necessarily mean that there is work available to work on right now,
        """
        return self.size() == 0 and self.processing_size() == 0

    def item_key(self, item: bytes):
        """Returns a string that uniquely identifies an item (bytes)."""
        return hashlib.sha224(item).hexdigest()

    def push(self, item: Union[str, bytes]):
        """Push a new item onto the main queue."""
        self.client.lpush(self.main_q_key, item)

    def lease(self, lease_secs: int = 60, block: bool = True, timeout: int = None):
        """Begin working on an item the work queue. 

        Lease the item for lease_secs. After that time, other
        workers may consider this client to have crashed or stalled
        and pick up the item instead.

        If optional args block is true and timeout is None (the default), block until an item is available."""
        if block:
            item = self.client.brpoplpush(self.main_q_key, self.processing_q_key, timeout=timeout)
        else:
            item = self.client.rpoplpush(self.main_q_key, self.processing_q_key)
        if item:
            # Record that we (this session id) are working on a key. Expire that
            # note after the lease timeout.
            # Note: if we crash at this line of the program, then GC will see no lease
            # for this item a later return it to the main queue.
            key = self.item_key(item)
            self.client.setex(self.lease_key_prefix + key, lease_secs, self.session)
        return item

    def lease_exists(self, item: bytes) -> bool:
        """True if a lease on 'item' exists."""
        return self.client.exists(self.lease_key_prefix + self.item_key(item)) > 0

    def check_expired_leases(self):
        """Check for expired leases and return them to the main queue."""
        # Processing list should not be _too_ long since it is approximately as long
        # as the number of active and recently active workers.
        processing = self.client.lrange(self.processing_q_key, 0, -1)
        for item in processing:
            # If the lease key is not present for an item (it expired or was
            # never created because the client crashed before creating it)
            # then move the item back to the main queue so others can work on it.
            if not self.lease_exists(item):
                # Atomically move the item to the main queue.
                with self.client.pipeline() as pipe:
                    try:
                        pipe.watch(self.processing_q_key)
                        pipe.multi()
                        pipe.lpush(self.main_q_key, item)
                        pipe.lrem(self.processing_q_key, 0, item)
                        pipe.execute()
                    except redis.WatchError:
                        # Another worker must have processed the item first.
                        pass

    def complete(self, value: bytes):
        """Complete working on the item with 'value'.

        If the lease expired, the item may not have completed, and some
        other worker may have picked it up. There is no indication
        of what happened.
        """
        self.client.lrem(self.processing_q_key, 0, value)
        # If we crash here, then the GC code will try to move the value, but it will
        # not be here, which is fine. So this does not need to be a transaction.
        key = self.item_key(value)
        self.client.delete(self.lease_key_prefix + key)

    def __str__(self):
        return "RedisWQ(name={},session={})".format(self.main_q_key, self.session)
