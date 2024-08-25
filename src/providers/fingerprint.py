from hashlib import md5


class InvalidFingerprint(Exception):
    ...


class FingerprintExists(Exception):
    ...


def hash_fingerprint(fingerprint: str) -> str:
    """Hashes the device fingerprint using SHA-256."""
    return md5(fingerprint.encode('utf-8')).hexdigest()