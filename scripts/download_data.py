"""Restore precisely the public archive recorded in data/source.json."""
from pathlib import Path
import hashlib
import json
import urllib.request

ROOT = Path(__file__).resolve().parents[1]


def main():
    source = json.loads((ROOT / 'data/source.json').read_text())
    payload = urllib.request.urlopen(source['url'], timeout=120).read()
    if hashlib.sha256(payload).hexdigest() != source['sha256']:
        raise ValueError('Downloaded bytes do not match the pinned SHA-256; no file written.')
    target = ROOT / 'data/raw' / source['filename']
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_bytes(payload)
    print(f'Verified {target.name}: {len(payload):,} bytes')


if __name__ == '__main__':
    main()
