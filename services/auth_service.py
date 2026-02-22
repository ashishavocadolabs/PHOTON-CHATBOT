import os
import requests
import base64
import json
from dotenv import load_dotenv

load_dotenv()

BASE_URL = "https://api.shipphoton.com"

USERNAME = os.getenv("EMAIL_ID")
PASSWORD = os.getenv("password")

token_cache = {
    "token": None,
    "user_id": None,
    "name": None
}


def decode_jwt(token):
    """
    Decode JWT safely (without verifying signature)
    """
    try:
        payload_part = token.split(".")[1]
        padded = payload_part + "=" * (-len(payload_part) % 4)
        decoded_bytes = base64.urlsafe_b64decode(padded)
        return json.loads(decoded_bytes)
    except Exception:
        return {}


def login():
    url = f"{BASE_URL}/api/Auth/GetToken"

    payload = {
        "userId": USERNAME,
        "password": PASSWORD,
        "deviceType": 0,
        "deviceId": "chatbot",
        "os": "windows"
    }

    response = requests.post(url, json=payload)
    response.raise_for_status()

    data = response.json()
    token = data["data"]["token"]

    token_cache["token"] = token

    # 🔥 Decode token to extract userId
    decoded = decode_jwt(token)

    token_cache["name"] = (
        decoded.get("name")
        or decoded.get("unique_name")
        or decoded.get("fullName")
        or decoded.get("Name")
    )

    user_id = (
        decoded.get("userId")
        or decoded.get("userid")
        or decoded.get("sub")
        or decoded.get("nameid")
        or decoded.get("UserId")
    )

    # Convert safely to int if possible
    try:
        token_cache["user_id"] = int(user_id)
    except Exception:
        token_cache["user_id"] = None

    print("EXTRACTED USER ID:", token_cache["user_id"])

    return token


def get_headers():
    if not token_cache["token"]:
        login()

    return {
        "Authorization": f"Bearer {token_cache['token']}",
        "Content-Type": "application/json"
    }


def get_logged_user_id():
    if token_cache["user_id"] is None:
        login()
    return token_cache["user_id"]

def get_logged_user_name():
    if not token_cache["token"]:
        login()
    return token_cache.get("name") or "User"