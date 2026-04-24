from hashlib import sha256
from pathlib import Path


def sha256_text(text: str) -> str:
    return sha256(text.encode("utf-8")).hexdigest()


def short_hash_text(text: str, length: int = 12) -> str:
    if length <= 0:
        raise ValueError("length must be positive")
    return sha256_text(text)[:length]


def sha256_file(path: Path) -> str:
    digest = sha256()
    with path.open("rb") as handle:
        while True:
            chunk = handle.read(1024 * 1024)
            if not chunk:
                break
            digest.update(chunk)
    return digest.hexdigest()
