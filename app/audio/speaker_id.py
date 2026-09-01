"""
Modulo de Identificacao de Voz e Verificacao do Mentor (Speaker ID) para o JARVIS.
Permite reconhecer e filtrar apenas a voz do dono/mentor atraves de impressao vocal acustica (Voiceprint).
"""

import os
from pathlib import Path
from typing import Tuple, Optional
import numpy as np
from app.core.config import app_config
from app.core.logging_config import get_logger

logger = get_logger("audio.speaker_id")

VOICEPRINT_FILE_PATH = Path("data") / "mentor_voiceprint.npy"


class SpeakerIdentifier:
    """Extrator de caracteristicas acusticas e comparador de impressao vocal do mentor."""

    def __init__(self):
        self.mentor_voiceprint: Optional[np.ndarray] = None
        self._load_voiceprint()

    def _load_voiceprint(self) -> None:
        """Carrega a impressao vocal do mentor salva em disco."""
        try:
            if VOICEPRINT_FILE_PATH.exists():
                vp = np.load(str(VOICEPRINT_FILE_PATH))
                if vp is not None and len(vp) > 0 and not np.isnan(vp).any():
                    norm = float(np.linalg.norm(vp))
                    if norm > 1e-6:
                        self.mentor_voiceprint = vp / norm
                        logger.info(f"Impressao vocal do mentor carregada ({len(self.mentor_voiceprint)} dims).")
                        return
            self.mentor_voiceprint = None
        except Exception as e:
            logger.error(f"Erro ao carregar mentor_voiceprint: {e}")
            self.mentor_voiceprint = None

    def _extract_acoustic_features(self, audio: np.ndarray, sr: int = 16000) -> Optional[np.ndarray]:
        """Extrai vetor numerico estavel de caracteristicas acusticas (energia, espectro, ZCR e sub-bandas)."""
        if audio is None or len(audio) < 1600:
            return None

        sig = np.nan_to_num(audio.astype(np.float32), nan=0.0, posinf=0.0, neginf=0.0)
        max_val = float(np.max(np.abs(sig)))
        if max_val > 1e-5:
            sig = sig / max_val
        else:
            return None

        frame_size = int(sr * 0.03)
        hop_size = int(sr * 0.015)
        
        num_frames = max(1, (len(sig) - frame_size) // hop_size)
        if num_frames < 2:
            return None

        features = []

        # 1. Zero Crossing Rate
        zcr = float(np.mean(np.abs(np.diff(np.sign(sig)))))
        features.append(0.0 if np.isnan(zcr) else zcr)

        # 2. RMS Energy
        rms = float(np.sqrt(np.mean(sig ** 2)))
        features.append(0.0 if np.isnan(rms) else rms)

        # 3. FFT e sub-bandas de frequencia
        fft_vals = np.abs(np.fft.rfft(sig[:sr]))
        freqs = np.fft.rfftfreq(min(len(sig), sr), 1.0 / sr)
        
        sum_fft = float(np.sum(fft_vals))
        if sum_fft > 1e-6:
            spectral_centroid = float(np.sum(freqs * fft_vals) / sum_fft)
        else:
            spectral_centroid = 0.0
        features.append(spectral_centroid / (sr / 2.0))

        # 4. Energias em 16 sub-bandas
        num_bands = 16
        band_size = len(fft_vals) // num_bands
        if band_size > 0:
            for i in range(num_bands):
                start = i * band_size
                end = (i + 1) * band_size
                band_energy = float(np.mean(fft_vals[start:end] ** 2)) if end > start else 0.0
                features.append(float(np.log1p(max(0.0, band_energy))))
        else:
            features.extend([0.0] * num_bands)

        vec = np.nan_to_num(np.array(features, dtype=np.float32), nan=0.0, posinf=0.0, neginf=0.0)
        norm = float(np.linalg.norm(vec))
        if norm > 1e-6:
            return vec / norm
        return None

    def enroll_mentor_voice(self, audio: np.ndarray, sr: int = 16000) -> bool:
        """Calibra ou atualiza a impressao vocal do mentor com a fala recebida."""
        feat = self._extract_acoustic_features(audio, sr)
        if feat is None:
            logger.warning("Audio insuficiente para calibrar impressao vocal do mentor.")
            return False

        try:
            if self.mentor_voiceprint is None:
                self.mentor_voiceprint = feat
            else:
                self.mentor_voiceprint = 0.6 * self.mentor_voiceprint + 0.4 * feat
                norm = float(np.linalg.norm(self.mentor_voiceprint))
                if norm > 1e-6:
                    self.mentor_voiceprint = self.mentor_voiceprint / norm

            VOICEPRINT_FILE_PATH.parent.mkdir(parents=True, exist_ok=True)
            np.save(str(VOICEPRINT_FILE_PATH), self.mentor_voiceprint)
            logger.info("Impressao vocal do mentor calibrada e salva com sucesso!")
            return True
        except Exception as e:
            logger.error(f"Erro ao salvar impressao vocal do mentor: {e}")
            return False

    def is_mentor_voice(self, audio: np.ndarray, sr: int = 16000) -> Tuple[bool, float]:
        """
        Compara o audio atual com a impressao vocal do mentor.
        Retorna (autorizado: bool, similaridade: float).
        """
        if not getattr(app_config.audio, "mentor_voice_filter_enabled", False):
            return True, 1.0

        if self.mentor_voiceprint is None or len(self.mentor_voiceprint) == 0:
            self.enroll_mentor_voice(audio, sr)
            return True, 1.0

        feat = self._extract_acoustic_features(audio, sr)
        if feat is None:
            return True, 0.5

        similarity = float(np.dot(self.mentor_voiceprint, feat))
        if np.isnan(similarity):
            similarity = 0.5

        threshold = 0.38
        is_match = similarity >= threshold
        logger.info(f"Verificacao Speaker ID: Similaridade={similarity:.2f} (Threshold={threshold}) -> Match: {is_match}")
        return is_match, similarity

    def reset_profile(self) -> None:
        """Reseta o perfil de voz do mentor."""
        self.mentor_voiceprint = None
        if VOICEPRINT_FILE_PATH.exists():
            try:
                VOICEPRINT_FILE_PATH.unlink()
            except Exception:
                pass


speaker_identifier = SpeakerIdentifier()
