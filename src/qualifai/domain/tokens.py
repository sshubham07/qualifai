"""Magic-link tokens: the link carries the token, the database only ever holds its hash."""

import hashlib
import hmac


def hash_token(token: str) -> str:
    return hashlib.sha256(token.encode()).hexdigest()


def token_matches(token: str | None, stored_hash: str) -> bool:
    return bool(token) and hmac.compare_digest(hash_token(token or ""), stored_hash)
