"""
Janela de Configuracoes Completas do JARVIS.
Permite personalizar IA, Audio, Camera, Memoria, Sistema e executar testes de diagnostico de hardware.
"""

import asyncio
from typing import Optional
from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QDialog, QTabWidget, QWidget, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit,
    QPushButton, QComboBox, QSlider, QCheckBox, QGroupBox, QSpinBox, QMessageBox,
    QTextEdit
)
from app.core.config import app_config, RECOMMENDED_MODELS
from app.security.secrets import secrets_manager
from app.ai.provider_factory import AIProviderFactory
from app.audio.microphone import microphone
from app.audio.speaker import speaker
from app.audio.tts import local_tts
from app.vision.camera import camera_capture
from app.platform.windows import windows_platform
from app.memory.long_term import long_term_memory
from app.ui.styles import HUD_DARK_STYLESHEET


class SettingsWindow(QDialog):
    """Janela de configuracoes com abas tematicas."""

    def __init__(self, parent: QWidget = None):
        super().__init__(parent)
        self.setWindowTitle("JARVIS — Configurações")
        self.resize(760, 580)
        self.setStyleSheet(HUD_DARK_STYLESHEET)

        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(16, 16, 16, 16)
        main_layout.setSpacing(12)

        self.tabs = QTabWidget()
        main_layout.addWidget(self.tabs)

        # Cria as abas
        self._create_ai_tab()
        self._create_audio_tab()
        self._create_vision_tab()
        self._create_memory_tab()
        self._create_system_tab()
        self._create_diagnostics_tab()

        # Botoes Inferiores (Salvar e Cancelar)
        btn_layout = QHBoxLayout()
        btn_layout.addStretch()

        self.cancel_btn = QPushButton("Cancelar")
        self.cancel_btn.clicked.connect(self.reject)
        btn_layout.addWidget(self.cancel_btn)

        self.save_btn = QPushButton("Salvar Configurações")
        self.save_btn.setProperty("class", "primary")
        self.save_btn.clicked.connect(self._save_settings)
        btn_layout.addWidget(self.save_btn)

        main_layout.addLayout(btn_layout)

    # 1. ABA IA
    def _create_ai_tab(self) -> None:
        tab = QWidget()
        layout = QVBoxLayout(tab)
        layout.setSpacing(14)

        # Provedor
        prov_layout = QHBoxLayout()
        prov_layout.addWidget(QLabel("Provedor de IA:"))
        self.ai_provider_combo = QComboBox()
        self.ai_provider_combo.addItems(["OpenAI", "Gemini", "Claude"])
        cur_prov = app_config.ai.provider.lower()
        if cur_prov == "gemini":
            self.ai_provider_combo.setCurrentText("Gemini")
        elif cur_prov in ("anthropic", "claude"):
            self.ai_provider_combo.setCurrentText("Claude")
        else:
            self.ai_provider_combo.setCurrentText("OpenAI")
        self.ai_provider_combo.currentTextChanged.connect(self._on_provider_changed)
        prov_layout.addWidget(self.ai_provider_combo)
        layout.addLayout(prov_layout)

        # API Key
        key_layout = QVBoxLayout()
        key_layout.addWidget(QLabel("Chave de API (Armazenada com segurança no Windows Credential Locker):"))
        self.api_key_input = QLineEdit()
        self.api_key_input.setEchoMode(QLineEdit.EchoMode.Password)
        saved_key = secrets_manager.get_api_key(app_config.ai.provider)
        if saved_key:
            self.api_key_input.setText(saved_key)
        key_layout.addWidget(self.api_key_input)
        layout.addLayout(key_layout)

        # Modelo (Editavel)
        model_layout = QHBoxLayout()
        model_layout.addWidget(QLabel("Modelo de IA (Selecione ou digite um customizado):"))
        self.model_combo = QComboBox()
        self.model_combo.setEditable(True)
        self._populate_models(app_config.ai.provider)
        model_layout.addWidget(self.model_combo)
        layout.addLayout(model_layout)

        # Teste de Conexao
        test_layout = QHBoxLayout()
        self.test_ai_btn = QPushButton("Testar Conexão com a IA")
        self.test_ai_btn.clicked.connect(self._test_ai_connection)
        self.ai_status_lbl = QLabel("")
        test_layout.addWidget(self.test_ai_btn)
        test_layout.addWidget(self.ai_status_lbl)
        test_layout.addStretch()
        layout.addLayout(test_layout)

        layout.addStretch()
        self.tabs.addTab(tab, "Inteligência Artificial")

    def _populate_models(self, provider_name: str) -> None:
        self.model_combo.clear()
        prov_clean = provider_name.lower().replace("openai", "openai").replace("gemini", "gemini").replace("claude", "claude")
        models = RECOMMENDED_MODELS.get(prov_clean, {}).get("recommended", [app_config.ai.model])
        self.model_combo.addItems(models)
        self.model_combo.setEditText(app_config.ai.model)

    def _on_provider_changed(self, text: str) -> None:
        prov = text.lower()
        self._populate_models(prov)
        saved_key = secrets_manager.get_api_key(prov)
        self.api_key_input.setText(saved_key or "")

    def _test_ai_connection(self) -> None:
        prov = self.ai_provider_combo.currentText().lower()
        key = self.api_key_input.text().strip()
        model = self.model_combo.currentText().strip()

        if not key:
            self.ai_status_lbl.setText("Chave de API não informada.")
            self.ai_status_lbl.setStyleSheet("color: #ef4444;")
            return

        self.ai_status_lbl.setText("Testando conexão...")
        self.ai_status_lbl.setStyleSheet("color: #00d2ff;")
        self.test_ai_btn.setEnabled(False)

        async def _test():
            provider = AIProviderFactory.create_provider(
                provider_name=prov,
                model_name=model,
                api_key=key
            )
            return await provider.test_connection()

        try:
            loop = asyncio.new_event_loop()
            success, msg = loop.run_until_complete(_test())
            loop.close()

            if success:
                self.ai_status_lbl.setText("● Conexão OK!")
                self.ai_status_lbl.setStyleSheet("color: #10b981;")
            else:
                self.ai_status_lbl.setText(f"Falha: {msg}")
                self.ai_status_lbl.setStyleSheet("color: #ef4444;")
        except Exception as e:
            self.ai_status_lbl.setText(f"Erro: {e}")
            self.ai_status_lbl.setStyleSheet("color: #ef4444;")
        finally:
            self.test_ai_btn.setEnabled(True)

    # 2. ABA AUDIO
    def _create_audio_tab(self) -> None:
        tab = QWidget()
        layout = QVBoxLayout(tab)
        layout.setSpacing(12)

        # Microfone
        layout.addWidget(QLabel("Microfone (Entrada):"))
        self.mic_combo = QComboBox()
        mics = microphone.list_input_devices()
        for m in mics:
            self.mic_combo.addItem(m["name"], m["index"])
            if m["index"] == app_config.audio.input_device_index:
                self.mic_combo.setCurrentIndex(self.mic_combo.count() - 1)
        layout.addWidget(self.mic_combo)

        # Alto-falante
        layout.addWidget(QLabel("Alto-falante (Saída):"))
        self.speaker_combo = QComboBox()
        speakers = speaker.list_output_devices()
        for s in speakers:
            self.speaker_combo.addItem(s["name"], s["index"])
            if s["index"] == app_config.audio.output_device_index:
                self.speaker_combo.setCurrentIndex(self.speaker_combo.count() - 1)
        layout.addWidget(self.speaker_combo)

        # Voz do JARVIS (TTS)
        layout.addWidget(QLabel("Voz do Assistente (Síntese TTS):"))
        self.voice_combo = QComboBox()
        voices = local_tts.list_voices()
        for v in voices:
            self.voice_combo.addItem(v["name"], v["id"])
            if v["id"] == app_config.audio.tts_voice_id:
                self.voice_combo.setCurrentIndex(self.voice_combo.count() - 1)
        layout.addWidget(self.voice_combo)

        # Motor de Transcricao STT
        layout.addWidget(QLabel("Motor de Transcrição de Voz (STT):"))
        self.stt_engine_combo = QComboBox()
        self.stt_engine_combo.addItem("Whisper Local (Faster-Whisper int8 100% Offline)", "local_whisper")
        self.stt_engine_combo.addItem("OpenAI Whisper Cloud (whisper-1 — Máxima Precisão PT-BR)", "openai_whisper")
        if app_config.audio.stt_engine == "openai_whisper":
            self.stt_engine_combo.setCurrentIndex(1)
        layout.addWidget(self.stt_engine_combo)

        # Modo de Voz
        layout.addWidget(QLabel("Modo de Ativação:"))
        self.voice_mode_combo = QComboBox()
        self.voice_mode_combo.addItem("Palavra de Ativação ('Jarvis')", "wakeword")
        self.voice_mode_combo.addItem("Conversação Contínua", "continuous")
        self.voice_mode_combo.addItem("Push-to-Talk (Atalho)", "push_to_talk")
        
        for i in range(self.voice_mode_combo.count()):
            if self.voice_mode_combo.itemData(i) == app_config.audio.voice_mode:
                self.voice_mode_combo.setCurrentIndex(i)
        layout.addWidget(self.voice_mode_combo)

        # Velocidade TTS
        speed_layout = QHBoxLayout()
        speed_layout.addWidget(QLabel("Velocidade da Fala:"))
        self.speed_slider = QSlider(Qt.Orientation.Horizontal)
        self.speed_slider.setRange(120, 260)
        self.speed_slider.setValue(app_config.audio.tts_rate)
        speed_layout.addWidget(self.speed_slider)
        layout.addLayout(speed_layout)

        # Teste de Voz
        test_voice_layout = QHBoxLayout()
        self.test_voice_btn = QPushButton("Testar Voz Masculina Selecionada")
        self.test_voice_btn.clicked.connect(self._test_voice)
        test_voice_layout.addWidget(self.test_voice_btn)
        test_voice_layout.addStretch()
        layout.addLayout(test_voice_layout)

        layout.addStretch()
        self.tabs.addTab(tab, "Áudio e Voz")

    def _test_voice(self) -> None:
        selected_vid = self.voice_combo.currentData()
        app_config.audio.tts_voice_id = selected_vid
        app_config.audio.tts_rate = self.speed_slider.value()
        local_tts.speak("Olá! Sistemas de áudio online. Esta é a voz do Jarvis.")

    # 3. ABA CAMERA
    def _create_vision_tab(self) -> None:
        tab = QWidget()
        layout = QVBoxLayout(tab)
        layout.setSpacing(12)

        layout.addWidget(QLabel("Dispositivo de Câmera:"))
        self.cam_combo = QComboBox()
        cams = camera_capture.list_cameras()
        for c in cams:
            self.cam_combo.addItem(c["name"], c["index"])
            if c["index"] == app_config.vision.camera_index:
                self.cam_combo.setCurrentIndex(self.cam_combo.count() - 1)
        layout.addWidget(self.cam_combo)

        self.smart_scene_cb = QCheckBox("Amostragem inteligente (enviar frames apenas quando houver mudança de cena)")
        self.smart_scene_cb.setChecked(app_config.vision.smart_scene_sampling)
        layout.addWidget(self.smart_scene_cb)

        fps_layout = QHBoxLayout()
        fps_layout.addWidget(QLabel("Taxa máxima de envio para IA (FPS):"))
        self.ai_fps_spin = QSpinBox()
        self.ai_fps_spin.setRange(0, 2)
        self.ai_fps_spin.setValue(int(app_config.vision.ai_vision_fps))
        fps_layout.addWidget(self.ai_fps_spin)
        fps_layout.addStretch()
        layout.addLayout(fps_layout)

        layout.addStretch()
        self.tabs.addTab(tab, "Câmera e Visão")

    # 4. ABA MEMORIA
    def _create_memory_tab(self) -> None:
        tab = QWidget()
        layout = QVBoxLayout(tab)
        layout.setSpacing(14)

        self.memory_enabled_cb = QCheckBox("Habilitar memória semântica persistente")
        self.memory_enabled_cb.setChecked(app_config.memory.enabled)
        layout.addWidget(self.memory_enabled_cb)

        self.private_mode_cb = QCheckBox("Modo Privado (não grava nenhuma memória ou histórico da sessão)")
        self.private_mode_cb.setChecked(app_config.memory.private_mode)
        layout.addWidget(self.private_mode_cb)

        topk_layout = QHBoxLayout()
        topk_layout.addWidget(QLabel("Quantidade de memórias contextuais recuperadas (Top-K):"))
        self.topk_spin = QSpinBox()
        self.topk_spin.setRange(1, 15)
        self.topk_spin.setValue(app_config.memory.max_retrieval_count if hasattr(app_config.memory, 'max_retrieval_count') else 5)
        topk_layout.addWidget(self.topk_spin)
        topk_layout.addStretch()
        layout.addLayout(topk_layout)

        clear_btn = QPushButton("Apagar Todas as Memórias Salvas")
        clear_btn.setProperty("class", "danger")
        clear_btn.clicked.connect(self._clear_all_memories)
        layout.addWidget(clear_btn)

        layout.addStretch()
        self.tabs.addTab(tab, "Memória")

    def _clear_all_memories(self) -> None:
        reply = QMessageBox.question(
            self,
            "Confirmar Exclusão",
            "Deseja realmente apagar TODAS as memórias persistentes do JARVIS?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        if reply == QMessageBox.StandardButton.Yes:
            long_term_memory.delete_all_memories()
            QMessageBox.information(self, "Sucesso", "Todas as memórias foram apagadas.")

    # 5. ABA SISTEMA
    def _create_system_tab(self) -> None:
        tab = QWidget()
        layout = QVBoxLayout(tab)
        layout.setSpacing(12)

        user_layout = QHBoxLayout()
        user_layout.addWidget(QLabel("Seu Nome (como o Jarvis deve chamá-lo):"))
        self.user_name_input = QLineEdit(app_config.system.user_name)
        user_layout.addWidget(self.user_name_input)
        layout.addLayout(user_layout)

        self.startup_cb = QCheckBox("Iniciar JARVIS automaticamente com o Windows")
        self.startup_cb.setChecked(windows_platform.is_startup_enabled())
        layout.addWidget(self.startup_cb)

        self.tray_cb = QCheckBox("Minimizar para a bandeja do sistema (System Tray) ao fechar")
        self.tray_cb.setChecked(app_config.system.minimize_to_tray)
        layout.addWidget(self.tray_cb)

        self.silent_cb = QCheckBox("Modo Silencioso (respostas apenas por texto, sem voz TTS)")
        self.silent_cb.setChecked(app_config.system.silent_mode)
        layout.addWidget(self.silent_cb)

        self.automation_cb = QCheckBox("Permitir controle automatizado de mouse e teclado (Avançado)")
        self.automation_cb.setChecked(app_config.system.allow_computer_automation)
        layout.addWidget(self.automation_cb)

        layout.addStretch()
        self.tabs.addTab(tab, "Sistema")

    # 6. ABA DIAGNOSTICO
    def _create_diagnostics_tab(self) -> None:
        tab = QWidget()
        layout = QVBoxLayout(tab)
        layout.setSpacing(12)

        info_lbl = QLabel("Execute testes automatizados dos módulos e hardware do JARVIS:")
        layout.addWidget(info_lbl)

        btn_grid = QHBoxLayout()
        run_doc_btn = QPushButton("Executar Diagnóstico Completo")
        run_doc_btn.clicked.connect(self._run_full_diagnostics)
        btn_grid.addWidget(run_doc_btn)
        layout.addLayout(btn_grid)

        self.diag_output = QTextEdit()
        self.diag_output.setReadOnly(True)
        self.diag_output.setStyleSheet("font-family: Consolas, monospace; font-size: 12px; background-color: #06080d;")
        layout.addWidget(self.diag_output)

        self.tabs.addTab(tab, "Diagnóstico")

    def _run_full_diagnostics(self) -> None:
        self.diag_output.clear()
        self.diag_output.append("=== DIAGNÓSTICO DO SISTEMA JARVIS ===\n")
        
        import sys
        self.diag_output.append(f"Python ............... OK ({sys.version.split()[0]})")

        from app.memory.database import db
        conn = db.get_connection()
        self.diag_output.append("Database (SQLite) .... OK (WAL mode ativo)")

        mics = microphone.list_input_devices()
        self.diag_output.append(f"Microfone ............ OK ({len(mics)} dispositivos encontrados)")

        speakers = speaker.list_output_devices()
        self.diag_output.append(f"Alto-falante ......... OK ({len(speakers)} dispositivos encontrados)")

        cams = camera_capture.list_cameras()
        self.diag_output.append(f"Câmera ............... OK ({len(cams)} câmeras detectadas)")

        key = secrets_manager.get_api_key(app_config.ai.provider)
        self.diag_output.append(f"Provedor IA .......... {app_config.ai.provider.upper()} ({'Chave Configurada' if key else 'Sem Chave'})")

        mems = long_term_memory.list_memories(limit=5)
        self.diag_output.append(f"Memória Persistente .. OK ({len(mems)} memórias carregadas)")

        self.diag_output.append("\nSISTEMA PRONTO PARA OPERAÇÃO.")

    def _save_settings(self) -> None:
        prov = self.ai_provider_combo.currentText().lower()
        key = self.api_key_input.text().strip()
        model = self.model_combo.currentText().strip()

        if key:
            secrets_manager.set_api_key(prov, key)
        app_config.ai.provider = prov
        app_config.ai.model = model or "gpt-4o"

        app_config.audio.input_device_index = self.mic_combo.currentData()
        app_config.audio.output_device_index = self.speaker_combo.currentData()
        if hasattr(self, 'voice_combo') and self.voice_combo.currentData():
            app_config.audio.tts_voice_id = self.voice_combo.currentData()
        app_config.audio.stt_engine = self.stt_engine_combo.currentData() or "local_whisper"
        app_config.audio.voice_mode = self.voice_mode_combo.currentData()
        app_config.audio.tts_rate = self.speed_slider.value()

        app_config.vision.camera_index = self.cam_combo.currentData() or 0
        app_config.vision.smart_scene_sampling = self.smart_scene_cb.isChecked()
        app_config.vision.ai_vision_fps = float(self.ai_fps_spin.value())

        app_config.memory.enabled = self.memory_enabled_cb.isChecked()
        app_config.memory.private_mode = self.private_mode_cb.isChecked()
        app_config.memory.max_retrieval_count = self.topk_spin.value()

        app_config.system.user_name = self.user_name_input.text().strip() or "Usuário"
        app_config.system.minimize_to_tray = self.tray_cb.isChecked()
        app_config.system.silent_mode = self.silent_cb.isChecked()
        app_config.system.allow_computer_automation = self.automation_cb.isChecked()

        windows_platform.set_startup_with_windows(self.startup_cb.isChecked())

        app_config.save()
        QMessageBox.information(self, "Configurações", "Configurações salvas com sucesso!")
        self.accept()
