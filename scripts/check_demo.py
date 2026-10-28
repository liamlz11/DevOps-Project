"""HTTP smoke tests and a non-destructive persistence demonstration.

Run from the project root with Python 3.12+; no third-party packages required.
"""
import argparse
import json
from pathlib import Path
from urllib.error import HTTPError
from urllib.request import Request, urlopen
import uuid


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--base-url', default='http://localhost:8080')
    parser.add_argument('--state', default='.demo-state.json')
    group = parser.add_mutually_exclusive_group()
    group.add_argument('--seed', action='store_true')
    group.add_argument('--verify', action='store_true')
    group.add_argument('--cleanup', action='store_true')
    args = parser.parse_args()

    def call(path, method='GET', body=None, expected=200):
        payload = json.dumps(body).encode() if body is not None else None
        req = Request(args.base_url.rstrip('/') + path, data=payload, method=method,
                      headers={'Content-Type': 'application/json'})
        try:
            response = urlopen(req, timeout=10)
        except HTTPError as error:
            response = error
        with response:
            content = response.read()
            if response.status != expected:
                raise AssertionError(f'{method} {path}: expected {expected}, got {response.status}: {content!r}')
            return json.loads(content) if content and path.startswith('/api/') else content

    state_path = Path(args.state)
    if args.seed:
        if state_path.exists():
            raise SystemExit('State file already exists. Verify/clean up that record first.')
        record = call('/api/entries', 'POST', {'plate': 'P-' + uuid.uuid4().hex[:8]}, 201)
        state_path.write_text(json.dumps(record), encoding='utf-8')
        print(f'Seeded {record["plate"]}; state saved to {state_path}.')
    elif args.verify or args.cleanup:
        record = json.loads(state_path.read_text(encoding='utf-8'))
        snapshot = call('/api/parking')
        assert record in snapshot['vehicles'], 'Seeded active vehicle did not survive.'
        assert record in snapshot['recent_entries'], 'Seeded arrival history did not survive.'
        print(f'PASS: {record["plate"]} and its arrival timestamp survived container recreation.')
        if args.cleanup:
            call('/api/vehicles/' + record['plate'], 'DELETE', expected=204)
            state_path.unlink()
            print('Released only the seeded vehicle; arrival history retained.')
    else:
        assert b'Gatehouse' in call('/')
        assert call('/api/health')['status'] == 'ok'
        plate = 'T-' + uuid.uuid4().hex[:8]
        record = call('/api/entries', 'POST', {'plate': plate}, 201)
        try:
            snapshot = call('/api/parking')
            assert record in snapshot['vehicles'] and record in snapshot['recent_entries']
            call('/api/entries', 'POST', {'plate': plate}, 409)
            call('/api/entries', 'POST', {'plate': '<script>'}, 400)
        finally:
            call('/api/vehicles/' + plate, 'DELETE', expected=204)
        call('/api/vehicles/' + plate, 'DELETE', expected=404)
        print('PASS: dashboard, health, POST, GET, duplicate, validation, release, and missing vehicle.')


if __name__ == '__main__':
    main()
