import os
import requests
from dotenv import load_dotenv

load_dotenv()

BASE_URL = "https://api.shipphoton.com"

USERNAME = os.getenv("EMAIL_ID")
PASSWORD = os.getenv("password")

token_cache = {"token": None}


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
    data = response.json()

    token = data["data"]["token"]
    token_cache["token"] = token
    return token


def get_headers():
    if not token_cache["token"]:
        login()

    return {
        "Authorization": f"Bearer {token_cache['token']}",
        "Content-Type": "application/json"
    }