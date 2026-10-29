"""Build a deterministic signed release manifest (CI only).

Private seed must be passed as GitHub Actions secret NOMIKO_SIGNING_KEY_B64.
Never log it or commit it. No release is published without this secret.
"""
from __future__ import annotations

import argparse
import base64
import hashlib
import json
import os
from pathlib import Path
import re
import sys

from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
from cryptography.hazmat.primitives import serialization


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--version', required=True)
    parser.add_argument('--channel', choices=['alpha','stable'], required=True)
    parser.add_argument('--installer', required=True)
    parser.add_argument('--out', default='release')
    parser.add_argument('--notes', default='NOMIKO browser improvements and signed updates.')
    args = parser.parse_args()
    if not re.fullmatch(r'\d+\.\d+\.\d+', args.version):
        raise SystemExit('Invalid version')
    path = Path(args.installer)
    expected_name = f'NOMIKO-Setup-{args.version}' + ('-alpha' if args.channel == 'alpha' else '') + '.exe'
    if path.name != expected_name or not path.is_file():
        raise SystemExit(f'Expected installer {expected_name}')
    seed_b64 = os.environ.get('NOMIKO_SIGNING_KEY_B64', '')
    if not seed_b64:
        raise SystemExit('NOMIKO_SIGNING_KEY_B64 missing; refusing unsigned release')
    try:
        seed = base64.b64decode(seed_b64, validate=True)
        if len(seed) != 32:
            raise ValueError('Invalid key length')
        signing = Ed25519PrivateKey.from_private_bytes(seed)
    except (ValueError, TypeError) as exc:
        raise SystemExit('Signing secret is invalid') from exc
    # Refuse to sign with a private key that does not match the browser's trust anchor.
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
    from src.update_trust import PUBLIC_ED25519_KEY_B64
    pub = signing.public_key().public_bytes(serialization.Encoding.Raw, serialization.PublicFormat.Raw)
    if base64.b64encode(pub).decode('ascii') != PUBLIC_ED25519_KEY_B64:
        raise SystemExit('Signing key does not match NOMIKO pinned public key')
    digest = hashlib.sha256()
    with path.open('rb') as file:
        for part in iter(lambda: file.read(1024 * 1024), b''):
            digest.update(part)
    manifest = {
        'schema': 1,
        'version': args.version,
        'tag': 'v' + args.version + ('-alpha' if args.channel == 'alpha' else ''),
        'channel': args.channel,
        'asset': path.name,
        'size': path.stat().st_size,
        'sha256': digest.hexdigest(),
        'notes': args.notes[:4000],
    }
    output = Path(args.out)
    output.mkdir(parents=True, exist_ok=True)
    raw = json.dumps(manifest, sort_keys=True, ensure_ascii=False, separators=(',', ':')).encode('utf-8')
    (output/'update.json').write_bytes(raw)
    (output/'update.sig').write_text(base64.b64encode(signing.sign(raw)).decode('ascii') + '\n', encoding='utf-8')
    print(f'Signed manifest created for {args.version}; SHA-256: {manifest["sha256"]}')


if __name__ == '__main__':
    main()
