import os
from typing import Any, Optional
import requests
import json


def getenv(name: str, default: Optional[Any] = None, raise_error_if_null: bool = True):
    value = os.getenv(name)
    if value is not None:
        return value
    if raise_error_if_null:
        raise ValueError(f"No {name} set for Flask application")
    else:
        return default


AUTOMATE_SECRET_KEY = getenv("AUTOMATE_SECRET_KEY")
AUTOMATE_EMAIL_ID = getenv("AUTOMATE_EMAIL_ID")


def send_notification(message: str):
    requests.post(
        "https://llamalab.com/automate/cloud/message",
        json={
            "secret": AUTOMATE_SECRET_KEY,
            "to": AUTOMATE_EMAIL_ID,
            "device": None,
            "priority": "normal",
            "payload": json.dumps(
                {"title": "Minecraft AWS Server", "message": message}
            ),
        },
    )
