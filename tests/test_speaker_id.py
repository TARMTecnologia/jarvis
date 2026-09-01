"""
Testes Unitarios para o Módulo de Identificacao de Voz do Mentor (Speaker ID).
"""

import pytest
import numpy as np
from app.audio.speaker_id import speaker_identifier
from app.core.config import app_config


def test_mentor_voice_enrollment_and_verification():
    # Cria sinal senoidal simulando voz
    sr = 16000
    t = np.linspace(0, 1.0, sr)
    mentor_voice = np.sin(2 * np.pi * 220 * t) + 0.5 * np.sin(2 * np.pi * 440 * t)
    impostor_voice = np.sin(2 * np.pi * 1200 * t) + np.random.normal(0, 0.2, sr)

    # 1. Calibra voz do mentor
    success = speaker_identifier.enroll_mentor_voice(mentor_voice, sr=sr)
    assert success is True
    assert speaker_identifier.mentor_voiceprint is not None

    # 2. Testa verificacao com filtro ativado
    app_config.audio.mentor_voice_filter_enabled = True

    is_mentor, sim_mentor = speaker_identifier.is_mentor_voice(mentor_voice, sr=sr)
    assert is_mentor is True
    assert sim_mentor > 0.80

    is_impostor, sim_impostor = speaker_identifier.is_mentor_voice(impostor_voice, sr=sr)
    assert sim_mentor > sim_impostor

    # Desativa filtro
    app_config.audio.mentor_voice_filter_enabled = False
