import os
import unittest
import uuid
from concurrent.futures import ThreadPoolExecutor

import redis
from storage import ParkingStore


class StorageTests(unittest.TestCase):
    def setUp(self):
        self.db = redis.Redis(host=os.getenv('REDIS_HOST', 'redis'), decode_responses=True)
        self.prefix = 'test:' + uuid.uuid4().hex
        self.store = ParkingStore(self.db, self.prefix)

    def tearDown(self):
        self.db.delete(self.prefix + ':active', self.prefix + ':history')

    def test_entry_duplicate_capacity_and_release(self):
        self.assertEqual(self.store.snapshot(), dict(vehicles=[], recent_entries=[]))
        self.assertEqual(self.store.admit('ABC', '2026-01-01T00:00:00+00:00', 1), 'created')
        self.assertEqual(self.store.admit('ABC', '2026-01-01T00:00:00+00:00', 1), 'duplicate')
        self.assertEqual(self.store.admit('DEF', '2026-01-01T00:00:00+00:00', 1), 'full')
        self.assertTrue(self.store.release('ABC'))
        self.assertFalse(self.store.release('ABC'))
        self.assertEqual(len(self.store.snapshot()['recent_entries']), 1)
        self.assertEqual(self.store.snapshot()['vehicles'], [])

    def test_concurrent_last_space(self):
        with ThreadPoolExecutor(max_workers=2) as pool:
            results = list(pool.map(lambda plate: self.store.admit(plate, '2026-01-01', 1), ['ABC', 'DEF']))
        self.assertCountEqual(results, ['created', 'full'])
        snapshot = self.store.snapshot()
        self.assertEqual(len(snapshot['vehicles']), 1)
        self.assertEqual(len(snapshot['recent_entries']), 1)

    def test_order_and_history_bound(self):
        for number in range(25):
            self.store.admit(str(number), f'2026-01-01T00:00:{number:02d}+00:00', 30)
        snapshot = self.store.snapshot()
        self.assertEqual(snapshot['vehicles'][0]['plate'], '24')
        self.assertEqual(len(snapshot['recent_entries']), 20)
        self.assertEqual(snapshot['recent_entries'][0]['plate'], '24')


if __name__ == '__main__':
    unittest.main()
