"""Reconnaissance vocale : SpeechRecognition + sounddevice, via Google Speech (en ligne).

sounddevice est utilisé à la place de PyAudio : il s'installe en simple wheel sous Windows.
"""
from __future__ import annotations

import math
from array import array

from ..models import SPEECH_CODES

SAMPLE_RATE = 16000
BLOCK = 1600            # 0,1 s
MAX_SECONDS = 6.0       # durée max d'écoute
SILENCE_AFTER = 0.9     # arrêt après ce silence suivant la parole
START_TIMEOUT = 5.0     # abandon si personne ne parle


class SpeechError(Exception):
    """Erreur affichable telle quelle à l'utilisateur."""


def _rms(raw: bytes) -> float:
    samples = array("h", raw)
    if not samples:
        return 0.0
    return math.sqrt(sum(s * s for s in samples) / len(samples))


def _record() -> bytes:
    try:
        import sounddevice as sd
    except Exception as exc:
        raise SpeechError("Module « sounddevice » introuvable (pip install sounddevice).") from exc
    try:
        if not sd.query_devices(kind="input"):
            raise SpeechError("Aucun microphone détecté.")
    except SpeechError:
        raise
    except Exception as exc:
        raise SpeechError("Aucun microphone détecté.") from exc

    chunks: list[bytes] = []
    threshold = None
    spoke = False
    silent_blocks = 0
    try:
        with sd.RawInputStream(samplerate=SAMPLE_RATE, channels=1, dtype="int16", blocksize=BLOCK) as stream:
            max_blocks = int(MAX_SECONDS * SAMPLE_RATE / BLOCK)
            for i in range(max_blocks):
                data, _ = stream.read(BLOCK)
                raw = bytes(data)
                chunks.append(raw)
                level = _rms(raw)
                if i < 3:   # calibrage sur le bruit ambiant (0,3 s)
                    threshold = max(level * 2.5, 400) if threshold is None else max(threshold, level * 2.5, 400)
                    continue
                if level > threshold:
                    spoke, silent_blocks = True, 0
                else:
                    silent_blocks += 1
                    if spoke and silent_blocks * BLOCK / SAMPLE_RATE >= SILENCE_AFTER:
                        break
                    if not spoke and i * BLOCK / SAMPLE_RATE >= START_TIMEOUT:
                        break
    except Exception as exc:
        raise SpeechError(f"Erreur d'accès au microphone : {exc}") from exc
    if not spoke:
        raise SpeechError("Je n'ai rien entendu. Réessayez.")
    return b"".join(chunks)


def listen_and_recognize(lang: str) -> str:
    """Écoute le micro puis renvoie le texte reconnu (langue = `lang`: fr/en/de)."""
    try:
        import speech_recognition as sr
    except Exception as exc:
        raise SpeechError("Module « SpeechRecognition » introuvable (pip install SpeechRecognition).") from exc

    audio = sr.AudioData(_record(), SAMPLE_RATE, 2)
    try:
        return sr.Recognizer().recognize_google(audio, language=SPEECH_CODES.get(lang, "en-US"))
    except sr.UnknownValueError as exc:
        raise SpeechError("Parole non comprise. Réessayez.") from exc
    except sr.RequestError as exc:
        raise SpeechError("Service de reconnaissance injoignable : vérifiez votre connexion Internet.") from exc
    except Exception as exc:
        raise SpeechError(f"Erreur de reconnaissance : {exc}") from exc
