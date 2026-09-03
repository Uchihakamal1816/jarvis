"""
JARVIS Voice Layer — Text-to-Speech Engine
Wraps edge-tts for natural, fast TTS generation and uses pygame for playback.
"""

import asyncio
import os
import re
import tempfile
import logging
from typing import Optional

try:
    import edge_tts
    import pygame
except ImportError as exc:
    raise ImportError(
        "edge-tts or pygame is not installed. Run: pip install edge-tts pygame"
    ) from exc

from . import config

log = logging.getLogger(__name__)


def clean_text_for_speech(text: str) -> str:
    """
    Cleans raw markdown text into speech-friendly plain text.
    Strips asterisks, backticks, header symbols, subagent handoff boilerplate, etc.
    """
    # 1. Remove subagent handoff boilerplate messages & bracket tags
    text = re.sub(r"\[[A-Z0-9_]+\]\s*", "", text)
    text = re.sub(r"I have gathered [^.\n]+\.\s*", "", text, flags=re.IGNORECASE)
    text = re.sub(r"sent the report to the parent agent\.?\s*", "", text, flags=re.IGNORECASE)

    # 2. Convert markdown headers, bold, italics, code formatting
    text = re.sub(r"#+\s*", "", text)                   # Headers (#, ##)
    text = re.sub(r"\*\*([^*]+)\*\*", r"\1", text)       # Bold **text**
    text = re.sub(r"\*([^*]+)\*", r"\1", text)           # Italic *text*
    text = re.sub(r"__([^_]+)__", r"\1", text)           # Bold __text__
    text = re.sub(r"_([^_]+)_", r"\1", text)             # Italic _text_
    text = re.sub(r"`([^`]+)`", r"\1", text)             # Code `text`
    text = re.sub(r"```[\s\S]*?```", "", text)           # Code blocks ```

    # 3. Clean up bullet points & lists
    text = re.sub(r"^\s*[-*+]\s+", "", text, flags=re.MULTILINE)
    text = re.sub(r"^\s*\d+\.\s+", "", text, flags=re.MULTILINE)

    # 4. Clean up markdown links [text](url) -> text
    text = re.sub(r"\[([^\]]+)\]\([^\)]+\)", r"\1", text)

    # 5. Normalize extra line breaks and whitespace
    text = re.sub(r"\n+", ". ", text)
    text = re.sub(r"\s+", " ", text).strip()

    return text


class TTSEngine:
    def __init__(self):
        self.enabled = config.TTS_ENABLED
        self.voice = config.TTS_VOICE
        self.rate = config.TTS_RATE
        self.is_playing = False
        
        if self.enabled:
            # Initialize pygame mixer for audio playback
            try:
                pygame.mixer.init()
                log.info("TTS Engine initialized with voice: %s", self.voice)
            except Exception as e:
                log.error("Failed to initialize pygame mixer: %s", e)
                self.enabled = False
        else:
            log.info("TTS Engine is DISABLED.")

    async def _generate_and_play(self, text: str) -> None:
        """Asynchronously generate audio using edge-tts and play it."""
        self.is_playing = True
        try:
            # Create a temporary file to hold the MP3 data
            fd, temp_path = tempfile.mkstemp(suffix=".mp3")
            os.close(fd)
            
            # Generate speech
            communicate = edge_tts.Communicate(text, self.voice, rate=self.rate)
            await communicate.save(temp_path)
            
            # Play speech
            pygame.mixer.music.load(temp_path)
            pygame.mixer.music.play()
            
            # Block until audio finishes playing
            while pygame.mixer.music.get_busy():
                await asyncio.sleep(0.1)

            # Brief 300ms echo dissipation buffer so mic doesn't re-hear TTS tail
            await asyncio.sleep(0.3)
                
            # Cleanup
            pygame.mixer.music.unload()
            try:
                os.remove(temp_path)
            except OSError:
                pass
                
        except Exception as e:
            log.error("Edge-TTS generation/playback failed (%s). Attempting offline pyttsx3 fallback...", e)
            try:
                import pyttsx3
                engine = pyttsx3.init()
                engine.say(text)
                engine.runAndWait()
            except Exception as fallback_err:
                log.error("Offline TTS fallback failed: %s", fallback_err)
        finally:
            self.is_playing = False

    def speak(self, text: str) -> None:
        """Synchronously speak the provided text after sanitizing markdown formatting."""
        if not self.enabled or not text.strip():
            return
            
        speech_ready_text = clean_text_for_speech(text)
        if not speech_ready_text:
            return

        log.info("Speaking: '%s'", speech_ready_text)
        self.is_playing = True # Set immediately to prevent race conditions
        
        # Run the async generation and playback in a new event loop
        try:
            loop = asyncio.get_event_loop()
        except RuntimeError:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            
        if loop.is_running():
            loop.create_task(self._generate_and_play(speech_ready_text))
        else:
            try:
                loop.run_until_complete(self._generate_and_play(speech_ready_text))
            finally:
                self.is_playing = False

# Global TTS engine instance
tts_engine = TTSEngine()
