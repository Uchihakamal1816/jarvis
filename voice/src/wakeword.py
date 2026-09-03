"""
JARVIS Voice Layer — Wake Word Engine Wrapper
Wraps openwakeword to detect specific wake words before activating STT.
"""

from __future__ import annotations
import numpy as np

try:
    import openwakeword
    from openwakeword.model import Model
except ImportError as exc:
    raise ImportError(
        "openwakeword is not installed. Run: pip install openwakeword"
    ) from exc

from . import config
from .logger import get_logger

log = get_logger(__name__)


class WakeWordEngine:
    def __init__(self) -> None:
        if not config.WAKE_WORD_ENABLED:
            log.info("Wake Word Engine is DISABLED.")
            return

        log.info(
            "Loading Wake Word Model (model=%s, threshold=%.2f)",
            config.WAKE_WORD_MODEL,
            config.WAKE_WORD_THRESHOLD,
        )
        # Automatically download the required pre-trained model if missing
        openwakeword.utils.download_models(model_names=[config.WAKE_WORD_MODEL])
        
        self._model = Model(
            wakeword_models=[config.WAKE_WORD_MODEL],
            inference_framework="onnx"
        )
        log.info("Wake Word Engine ready.")

    def process_chunk(self, raw_bytes: bytes) -> bool:
        """
        Feed one audio chunk (16kHz, mono, int16 PCM) to the wake word model.
        Returns True if the wake word is detected.
        """
        if not config.WAKE_WORD_ENABLED:
            return False

        # openwakeword expects a 1D numpy array of int16
        audio_array = np.frombuffer(raw_bytes, dtype=np.int16)
        
        prediction = self._model.predict(audio_array)
        
        for model_key, score in prediction.items():
            if score >= config.WAKE_WORD_THRESHOLD:
                log.info("Wake word detected! (model=%s, score=%.2f)", model_key, score)
                self.reset()
                return True
                
        return False
        
    def reset(self) -> None:
        """Reset the internal state of the wake word model."""
        if config.WAKE_WORD_ENABLED:
            self._model.reset()
