"""Redis owns atomic admission and the persistent parking records."""
import json


class ParkingStore:
    # Redis executes a script without interleaving other commands. The duplicate
    # check precedes capacity so a repeated camera message has a stable response.
    ADMIT = """
    if redis.call('HEXISTS', KEYS[1], ARGV[1]) == 1 then return 'duplicate' end
    if redis.call('HLEN', KEYS[1]) >= tonumber(ARGV[3]) then return 'full' end
    redis.call('HSET', KEYS[1], ARGV[1], ARGV[2])
    redis.call('LPUSH', KEYS[2], ARGV[2])
    redis.call('LTRIM', KEYS[2], 0, 19)
    return 'created'
    """

    def __init__(self, client, prefix='parking'):
        self.client = client
        self.active = prefix + ':active'
        self.history = prefix + ':history'
        self.admission = client.register_script(self.ADMIT)

    def ping(self):
        return self.client.ping()

    def admit(self, plate, entered_at, capacity):
        record = json.dumps(dict(plate=plate, entered_at=entered_at))
        return self.admission(keys=[self.active, self.history], args=[plate, record, capacity])

    def release(self, plate):
        return bool(self.client.hdel(self.active, plate))

    def snapshot(self):
        # A transaction gives the dashboard a consistent view of both collections.
        with self.client.pipeline(transaction=True) as pipeline:
            pipeline.hvals(self.active)
            pipeline.lrange(self.history, 0, 19)
            active, history = pipeline.execute()
        vehicles = sorted((json.loads(item) for item in active),
                          key=lambda item: item['entered_at'], reverse=True)
        return dict(vehicles=vehicles, recent_entries=[json.loads(item) for item in history])
