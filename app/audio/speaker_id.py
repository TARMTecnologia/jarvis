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
                self.mentor_voiceprint = np.load(str(VOICEPRINT_FILE_PATH))
                logger.info(f"Impressao vocal do mentor carregada com sucesso ({len(self.mentor_voiceprint)} dims).")
        except Exception as e:
            logger.error(f"Erro ao carregar mentor_voiceprint: {e}")
            self.mentor_voiceprint = None

    def _extract_acoustic_features(self, audio: np.ndarray, sr: int = 16000) -> Optional[np.ndarray]:
        """Extrai vetor numerico de caracteristicas acusticas (energia, espectro, ZCR e sub-bandas)."""
        if audio is None or len(audio) < 1600:  # Minimo 100ms de audio
            return None

        # Garante float32 e normalizacao
        sig = audio.astype(np.float32)
        max_val = np.max(np.abs(sig))
        if max_val > 0:
            sig = sig / max_val

        frame_size = int(sr * 0.03)  # 30ms
        hop_size = int(sr * 0.015)   # 15ms
        
        num_frames = max(1, (len(sig) - frame_size) // hop_size)
        if num_frames < 3:
            return None

        features = []

        # 1. Zero Crossing Rate
        zcr = np.mean(np.abs(np.diff(np.sign(sig))))
        features.append(zcr)

        # 2. RMS Energy
        rms = np.sqrt(np.mean(sig ** 2))
        features.append(rms)

        # 3. FFT e sub-bandas de frequencia
        fft_vals = np.abs(np.fft.rfft(sig[:sr]))
        freqs = np.fft.rfftfreq(min(len(sig), sr), 1.0 / sr)
        
        # Centroide espectral
        if np.sum(fft_vals) > 0:
            spectral_centroid = np.sum(freqs * fft_vals) / np.sum(fft_vals)
        else:
            spectral_centroid = 0.0
        features.append(spectral_centroid / (sr / 2.0))

        # 4. Energias em 16 sub-bandas de frequencia (Mel scale approximation)
        num_bands = 16
        band_size = len(fft_vals) // num_bands
        if band_size > 0:
            for i in range(num_bands):
                start = i * band_size
                end = (i + 1) * band_size
                band_energy = np.mean(fft_vals[start:end] ** 2) if end > start else 0.0
                features.append(np.log1p(band_energy))
        else:
            features.extend([0.0] * num_bands)

        vec = np.array(features, dtype=np.float32)
        norm = np.linalg.norm(vec)
        if norm > 0:
            vec = vec / norm
        return vec

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
                # Media movel exponencial para adaptar a variacoes sutis da voz do mentor
                self.mentor_voiceprint = 0.7 * self.mentor_voiceprint + 0.3 * feat
                norm = np.linalg.norm(self.mentor_voiceprint)
                if norm > 0:
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

        if self.mentor_voiceprint is None:
            self.enroll_mentor_voice(audio, sr)
            return True, 1.0

        feat = self._extract_acoustic_features(audio, sr)
        if feat is None:
            return True, 0.5

        similarity = float(np.dot(feat, self.mentor_voiceprint))
        threshold = getattr(app_config.audio, "mentor_voice_similarity_threshold", 0.55)

        is_mentor = similarity >= threshold
        if is_mentor:
            logger.info(f"Voz do mentor reconhecida (Similaridade: {similarity:.2f} >= {threshold:.2f}).")
            self.mentor_voiceprint = 0.95 * self.mentor_voiceprint + 0.05 * feat
        else:
            logger.warning(f"Voz rejeitada (Similaridade: {similarity:.2f} < {threshold:.2f} — possivel terceiro ou ruido).")

        return is_mentor, similarity

    def reset_profile(self) -> None:
        """Limpa a calibracao da voz do mentor."""
        self.mentor_voiceprint = None
        if VOICEPRINT_FILE_PATH.exists():
            try:
                VOICEPRINT_FILE_PATH.unlink()
                logger.info("Perfil de voz do mentor removido.")
            except Exception as e:
                logger.error(f"Erro ao remover mentor_voiceprint: {e}")


speaker_identifier = SpeakerIdentifier()
