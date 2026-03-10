# transcription helper stub – previously used OpenAI Whisper.
# after removing server‑side transcription we simply return None which
# tells callers that no transcription occurred.

def transcribe_audio(file_path: str) -> str | None:
    """Placeholder function.

    Always returns ``None`` to indicate that transcription is not
    configured.  The front-end still posts audio to /voice, but the
    endpoint no longer tries to decode it.
    """
    return None
