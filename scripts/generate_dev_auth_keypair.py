#!/usr/bin/env python
"""Generate an RSA keypair for the dev-only token minting path
(``glue/dev_auth.py``, ``POST /v1/dev/token``) and print the ``.env``
snippet to enable it locally.

Usage::

    python scripts/generate_dev_auth_keypair.py

The private key never leaves your machine unless you paste it into your
own ``.env`` -- this script only prints it once, to stdout.

**Never set DEV_AUTH_ENABLED in a real deployment.** This exists purely so
``web/`` has something legitimate to authenticate with against a local
API instance. See ``glue/dev_auth.py``'s module docstring.
"""
from __future__ import annotations

import json

from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import rsa

KID = "dev-key-1"


def main() -> None:
    private_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    private_pem = private_key.private_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PrivateFormat.PKCS8,
        encryption_algorithm=serialization.NoEncryption(),
    ).decode()
    public_pem = private_key.public_key().public_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PublicFormat.SubjectPublicKeyInfo,
    ).decode()

    print("Add these to your .env (see .env.example):\n")
    print("DEV_AUTH_ENABLED=true")
    print(f"DEV_AUTH_KID={KID}")
    print(f'DEV_AUTH_PRIVATE_KEY_PEM="{private_pem}"'.replace("\n", "\\n"))
    print(f'AUTH_STATIC_KEYS_JSON=\'{json.dumps({KID: public_pem})}\'')
    print(
        "\nAUTH_STATIC_KEYS_JSON must already be your chosen auth verification "
        "source (AUTH_JWKS_URL is the other option) -- if you already have "
        "real signing keys configured there for a JWKS-based deployment, "
        "merge this dev key in as an additional entry rather than replacing it."
    )
    print("\nAlso set CORS_ALLOWED_ORIGINS to your Vite dev server origin, e.g.:")
    print("CORS_ALLOWED_ORIGINS=http://localhost:5173")


if __name__ == "__main__":
    main()
