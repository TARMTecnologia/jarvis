"""
Ferramenta de Diagnostico e Auto-Teste do Sistema JARVIS (CLI).
Executa verificacoes de hardware, dependencias, banco de dados, chaves e modelos.
Uso: python -m app.doctor
"""

import sys
import os
import socket
import sqlite3
from pathlib import Path


def check_mark(status: bool) -> str:
    return "OK" if status else "FALHA"


def run_doctor() -> bool:
    print("\n=======================================================")
    print("              JARVIS DIAGNOSTIC & SELF-TEST             ")
    print("=======================================================\n")

    all_passed = True

    # 1. Versao do Python
    py_ver = f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}"
    py_ok = sys.version_info >= (3, 12)
    print(f"Python ({py_ver}) ...................... [{check_mark(py_ok)}]")
    if not py_ok:
        all_passed = False

    # 2. Banco de Dados SQLite
    try:
        from app.memory.database import db
        conn = db.get_connection()
        cursor = conn.execute("SELECT name FROM sqlite_master WHERE type='table';")
        tables = [r[0] for r in cursor.fetchall()]
        db_ok = "memories" in tables and "conversations" in tables
        print(f"Database (SQLite) ...................... [{check_mark(db_ok)}] ({len(tables)} tabelas)")
    except Exception as e:
        print(f"Database (SQLite) ...................... [FALHA] ({e})")
        all_passed = False

    # 3. Microfone e Dispositivos de Audio
    try:
        from app.audio.microphone import microphone
        mics = microphone.list_input_devices()
        mic_ok = len(mics) > 0
        print(f"Microfone .............................. [{check_mark(mic_ok)}] ({len(mics)} detectados)")
    except Exception as e:
        print(f"Microfone .............................. [FALHA] ({e})")

    # 4. Alto-falantes
    try:
        from app.audio.speaker import speaker
        speakers = speaker.list_output_devices()
        spk_ok = len(speakers) > 0
        print(f"Alto-falante ........................... [{check_mark(spk_ok)}] ({len(speakers)} detectados)")
    except Exception as e:
        print(f"Alto-falante ........................... [FALHA] ({e})")

    # 5. Webcam / Camera
    try:
        from app.vision.camera import camera_capture
        cams = camera_capture.list_cameras(max_tested=2)
        cam_ok = len(cams) > 0
        print(f"Camera (OpenCV DirectShow) ............. [{check_mark(cam_ok)}] ({len(cams)} detectada(s))")
    except Exception as e:
        print(f"Camera ................................. [FALHA] ({e})")

    # 6. Windows Keyring (Credential Manager)
    try:
        from app.security.secrets import secrets_manager
        secrets_manager.set_api_key("doctor_test", "test_secret_123")
        val = secrets_manager.get_api_key("doctor_test")
        secrets_manager.delete_api_key("doctor_test")
        keyring_ok = val == "test_secret_123"
        print(f"Keyring (Windows Credential Locker) .... [{check_mark(keyring_ok)}]")
    except Exception as e:
        print(f"Keyring (Windows Credential Locker) .... [FALHA] ({e})")

    # 7. Conectividade com a Internet
    try:
        socket.create_connection(("8.8.8.8", 53), timeout=3)
        net_ok = True
        print(f"Conexao Internet ....................... [OK]")
    except OSError:
        net_ok = False
        print(f"Conexao Internet ....................... [OFFLINE]")

    # 8. Motor de Sintese de Voz (TTS SAPI5)
    try:
        from app.audio.tts import local_tts
        voices = local_tts.list_voices()
        tts_ok = len(voices) > 0
        print(f"Motor Local TTS (SAPI5) ................ [{check_mark(tts_ok)}] ({len(voices)} vozes)")
    except Exception as e:
        print(f"Motor Local TTS ........................ [FALHA] ({e})")

    # 9. Motor de Embeddings Semanticos
    try:
        from app.memory.embeddings import embedding_engine
        vec = embedding_engine.generate_embedding("teste de diagnostico jarvis")
        emb_ok = len(vec) > 0
        print(f"Embeddings Semanticos Locais ........... [{check_mark(emb_ok)}] (dimensao {len(vec)})")
    except Exception as e:
        print(f"Embeddings Semanticos Locais ........... [FALHA] ({e})")

    # 10. Provedor de IA Ativo
    try:
        from app.core.config import app_config
        from app.security.secrets import secrets_manager
        prov = app_config.ai.provider
        has_key = secrets_manager.has_api_key(prov)
        key_status = "Chave Configurada" if has_key else "Sem Chave Cadastrada"
        print(f"Provedor IA ({prov.upper()}) .............. [{check_mark(has_key)}] ({key_status})")
    except Exception as e:
        print(f"Provedor IA ............................ [FALHA] ({e})")

    print("\n-------------------------------------------------------")
    if all_passed:
        print("                     SYSTEM READY                      ")
    else:
        print("                 ATTENTION REQUIRED                    ")
    print("=======================================================\n")
    return all_passed


def main() -> None:
    success = run_doctor()
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
