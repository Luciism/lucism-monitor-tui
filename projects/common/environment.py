import os

def get_and_assert_env(name: str) -> str:
    value = os.getenv(name)
    assert value, f"{name} is not set"

    return value
