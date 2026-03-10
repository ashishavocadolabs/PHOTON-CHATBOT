import os
from dotenv import load_dotenv

load_dotenv()

ELEVEN_KEY = os.getenv("ELEVENSLAB_API")
# default voice ID – choose a male voice by default.  You can override
# this with ELEVEN_VOICE_ID in your .env file (get IDs from the
# ElevenLabs dashboard). The original female voice was 21m00Tcm4TlvDq8ikWAM;
# here we picked a male example ID but any valid voice works.
VOICE_ID = os.getenv("ELEVEN_VOICE_ID", "EXAVITQu4vr4xnSDxMaL")


async def text_to_speech(text: str) -> bytes | None:
    """Return audio bytes for given text using ElevenLabs.

    If the ELEVENSLAB_API key is missing the function returns ``None``.
    """

    if not ELEVEN_KEY:
        return None

    url = f"https://api.elevenlabs.io/v1/text-to-speech/{VOICE_ID}"
    headers = {
        "xi-api-key": ELEVEN_KEY,
        "Content-Type": "application/json",
        "Accept": "audio/mpeg",
    }
    payload = {"text": text}

    import httpx

    try:
        async with httpx.AsyncClient(timeout=30) as client:
            resp = await client.post(url, json=payload, headers=headers)
        if resp.status_code == 200:
            return resp.content
    except Exception as e:
        print("tts_service.error", e)

    return None
