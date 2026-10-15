import os
import dotenv

_ = dotenv.load_dotenv(os.path.join(os.getcwd(), ".env"))

def get_and_assert_env(name: str) -> str:
    value = os.getenv(name)
    assert value, f"{name} is not set"

    return value
