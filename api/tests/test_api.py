import unittest
from unittest.mock import Mock, patch

from redis.exceptions import ConnectionError
from app import create_app


class ApiTests(unittest.TestCase):
    def test_explicit_bounded_redis_retry(self):
        with patch('app.redis.Redis') as factory:
            create_app()
        retry = factory.call_args.kwargs.get('retry')
        self.assertIsNotNone(retry, 'Default Redis retries can exceed the proxy timeout')
        self.assertEqual(retry.get_retries(), 0)

    def setUp(self):
        self.store = Mock()
        self.store.admit.return_value = "created"
        self.store.snapshot.return_value = {"vehicles": [], "recent_entries": []}
        self.client = create_app(self.store, 5).test_client()

    def test_empty_snapshot(self):
        self.assertEqual(self.client.get('/api/parking').json,
                         dict(vehicles=[], recent_entries=[], count=0, capacity=5, full=False))

    def test_normalized_entry(self):
        response = self.client.post('/api/entries', json={'plate': ' abc-123 '})
        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.json['plate'], 'ABC-123')
        self.assertTrue(response.json['entered_at'].endswith('+00:00'))
        self.assertEqual(self.store.admit.call_args.args[0], 'ABC-123')

    def test_invalid_inputs_do_not_touch_storage(self):
        for body in [None, [], 'ABC', 123, {}, {'plate': 123}, {'plate': ''},
                     {'plate': 'ab'}, {'plate': 'A' * 13}, {'plate': '<script>'}, {'plate': 'אבג'},
                     {'plate': 'ß12'}, {'plate': 'ı12'}]:
            with self.subTest(body=body):
                response = self.client.post('/api/entries', json=body)
                self.assertEqual(response.status_code, 400)
                self.assertIn('error', response.json)
        self.store.admit.assert_not_called()

    def test_malformed_json(self):
        self.assertEqual(self.client.post('/api/entries', data='{', content_type='application/json').status_code, 400)

    def test_duplicate_and_full(self):
        for result in ['duplicate', 'full']:
            self.store.admit.return_value = result
            response = self.client.post('/api/entries', json={'plate': 'ABC-123'})
            self.assertEqual(response.status_code, 409)
            self.assertEqual(response.json['code'], result)

    def test_release_and_missing(self):
        self.store.release.return_value = True
        self.assertEqual(self.client.delete('/api/vehicles/abc-123').status_code, 204)
        self.store.release.assert_called_with('ABC-123')
        self.store.release.return_value = False
        self.assertEqual(self.client.delete('/api/vehicles/ABC-123').status_code, 404)

    def test_redis_outage_returns_json(self):
        for route, method, operation in [('/api/health', 'get', 'ping'),
                                         ('/api/parking', 'get', 'snapshot'),
                                         ('/api/entries', 'post', 'admit'),
                                         ('/api/vehicles/ABC', 'delete', 'release')]:
            getattr(self.store, operation).side_effect = ConnectionError('offline')
            response = getattr(self.client, method)(route, json={'plate': 'ABC'})
            self.assertEqual(response.status_code, 503)
            self.assertIn('error', response.json)


if __name__ == '__main__':
    unittest.main()
