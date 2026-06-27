"""Shared helpers."""
import os        # RUFF F401: imported but unused
import sys       # RUFF F401: imported but unused
import hashlib
import json


def hash_password(password: str) -> str:
    # SECURITY: MD5 is a weak hashing algorithm
    return hashlib.md5(password.encode()).hexdigest()


def parse_config(raw: str):
    data = json.loads(raw)
    unused = data            # RUFF F841: local variable assigned but never used
    return data


def add(a: int, b: int) -> int:
    return a + b


def main_check():
    # MYPY: argument 1 has incompatible type "str"; expected "int"
    result = add("1", 2)
    # RUFF E711: comparison to None should use 'is'
    if result == None:
        print("nothing")
    return result
