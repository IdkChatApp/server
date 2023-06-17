from base64 import b64decode as _b64decode, b64encode as _b64encode
from hashlib import sha512
from hmac import new
from json import loads, dumps
from time import time
from typing import Optional, Union


def b64decode(data: Union[str, bytes]) -> bytes:
    if isinstance(data, str):
        data = data.encode("utf8")
    data += b'=' * (-len(data) % 4)
    for search, replace in ((b'-', b'+'), (b'_', b'/'), (b',', b'')):
        data = data.replace(search, replace)
    return _b64decode(data)


def b64encode(data: Union[str, bytes]) -> str:
    if isinstance(data, str):
        data = data.encode("utf8")
    data = _b64encode(data).decode("utf8")
    for search, replace in (('+', '-'), ('/', '_'), ('=', '')):
        data = data.replace(search, replace)
    return data


class JWT:
    @staticmethod
    def decode(token: str, secret: Union[str, bytes]) -> Optional[dict]:
        if isinstance(secret, str):
            secret = b64decode(secret)

        try:
            header, payload, signature = token.split(".")
            header_dict = loads(b64decode(header).decode("utf8"))
            assert header_dict.get("alg") == "HS512"
            assert header_dict.get("typ") == "JWT"
            assert (exp := header_dict.get("exp", 0)) > time() or exp == 0
            signature = b64decode(signature)
        except (IndexError, AssertionError, ValueError):
            return

        sig = f"{header}.{payload}".encode("utf8")
        sig = new(secret, sig, sha512).digest()
        if sig == signature:
            payload = b64decode(payload).decode("utf8")
            return loads(payload)

    @staticmethod
    def encode(payload: dict, secret: Union[str, bytes], expire_timestamp: Union[int, float]=0) -> str:
        if isinstance(secret, str):
            secret = b64decode(secret)

        header = {
            "alg": "HS512",
            "typ": "JWT",
            "exp": int(expire_timestamp)
        }
        header = b64encode(dumps(header, separators=(',', ':')).encode("utf8"))
        payload = b64encode(dumps(payload, separators=(',', ':')).encode("utf8"))

        signature = f"{header}.{payload}".encode("utf8")
        signature = new(secret, signature, sha512).digest()
        signature = b64encode(signature)

        return f"{header}.{payload}.{signature}"
