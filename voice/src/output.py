"""
JARVIS Voice Layer — Output Handler

Publishes transcription events to configured destinations.

Supported modes:
  - stdout   : Prints JSON events to stdout (default, good for piping)
  - webhook  : POSTs JSON events to WEBHOOK_URL
  - core     : Routes to IntentRouter & Hermes Orchestrator with thinking quotes
"""

from __future__ import annotations

import json
import time
import threading
from typing import Any

from . import config
from .logger import get_logger

log = get_logger(__name__)


class OutputHandler:
    """
    Routes transcript events to the configured output destination.
    """

    def __init__(self) -> None:
        self._mode = config.OUTPUT_MODE
        if self._mode == "webhook":
            self._init_webhook()
        elif self._mode == "core":
            self._init_core()
        log.info("Output handler: mode=%s", self._mode)

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def emit_speech_start(self) -> None:
        self._emit({"event": "speech_start", "timestamp": time.time()})

    def emit_speech_end(self) -> None:
        self._emit({"event": "speech_end", "timestamp": time.time()})

    def emit_partial(self, text: str) -> None:
        self._emit({
            "event": "partial",
            "text": text,
            "is_final": False,
            "timestamp": time.time(),
        })

    def emit_transcript(
        self,
        text: str,
        words: list,
        duration_ms: int,
    ) -> None:
        confidence = self._avg_confidence(words)
        self._emit({
            "event": "transcript",
            "text": text,
            "is_final": True,
            "confidence": confidence,
            "words": words,
            "timestamp": time.time(),
            "duration_ms": duration_ms,
        })

    # ------------------------------------------------------------------
    # Internal
    # ------------------------------------------------------------------

    def _emit(self, payload: dict[str, Any]) -> None:
        if self._mode == "stdout":
            print(json.dumps(payload), flush=True)
        elif self._mode == "webhook":
            self._post_webhook(payload)
        elif self._mode == "core":
            if payload["event"] == "transcript" and payload.get("text"):
                print(f"\n[VOICE INPUT] {payload['text']}")
                
                # Speak a natural thinking pre-phrase + quote while Hermes processes
                from .tts import tts_engine
                try:
                    from core.src.quotes import get_thinking_phrase
                    thinking_msg = get_thinking_phrase()
                    print(f"[THINKING QUOTE] {thinking_msg}")
                    threading.Thread(target=tts_engine.speak, args=(thinking_msg,), daemon=True).start()
                except Exception as exc:
                    log.warning("Could not load quote: %s", exc)

                response = self._router.route_intent(payload["text"], self._session)
                print(f"\n[SUPERVISOR] {response}\n")
                
                # Speak final response
                threading.Thread(target=tts_engine.speak, args=(response,), daemon=True).start()
        else:
            log.warning("Unknown output mode '%s'; falling back to stdout", self._mode)
            print(json.dumps(payload), flush=True)

    def _init_core(self) -> None:
        try:
            from core.src.intent import IntentRouter
            from core.src.session import session_manager
            self._router = IntentRouter()
            self._session = session_manager.get_or_create_session()
            log.info("Core integration initialized successfully.")
        except ImportError as exc:
            log.error("Failed to load core components: %s", exc)
            self._mode = "stdout" # Fallback

    def _init_webhook(self) -> None:
        if not config.WEBHOOK_URL:
            raise ValueError(
                "OUTPUT_MODE=webhook requires WEBHOOK_URL to be set."
            )
        try:
            import requests  # optional dep for webhook mode
            self._session = requests.Session()
        except ImportError:
            raise ImportError(
                "requests is required for webhook output mode. "
                "Run: pip install requests"
            )
        log.info("Webhook target: %s", config.WEBHOOK_URL)

    def _post_webhook(self, payload: dict) -> None:
        try:
            resp = self._session.post(
                config.WEBHOOK_URL,
                json=payload,
                timeout=config.WEBHOOK_TIMEOUT_S,
            )
            resp.raise_for_status()
        except Exception as exc:
            log.error("Webhook delivery failed: %s", exc)

    @staticmethod
    def _avg_confidence(words: list) -> float | None:
        if not words:
            return None
        confs = [w.get("conf", 0) for w in words if "conf" in w]
        return round(sum(confs) / len(confs), 3) if confs else None
