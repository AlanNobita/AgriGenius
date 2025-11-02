#!/usr/bin/env python3
"""Generate a secure Flask SECRET_KEY and print it to stdout."""
import secrets
import sys

# Generate 48 bytes worth of url-safe text
key = secrets.token_urlsafe(48)
print(key)
# also exit with key on stdout
sys.exit(0)
