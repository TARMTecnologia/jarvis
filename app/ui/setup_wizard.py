"""
Assistente de Configuracao Inicial (Setup Wizard) do JARVIS.
Guia o usuario no primeiro uso para configurar Provider de IA, API Key, Microfone, Alto-falante e Webcam.
"""

import asyncio
from typing import Optional
from PySide6.QtCore import Qt, QTimer
from PySide6.QtWidgets import (
    QWizard, QWizardPage, QVBoxLayout, QHBoxLayout, QLabel, QRadioButton,
    QButtonGroup, QLineEdit, QPushButton, QComboBox, QWidget, QMessageBox, QFrame
)
from app.core.config import app_config, RECOMMENDED_MODELS
from app.security.secrets import secrets_manager
from app.ai.provider_factory import AIProviderFactory
from app.audio.microphone import microphone
from app.audio.speaker import speaker
from app.audio.tts import local_tts
from app.vision.camera import camera_capture
from app.vision.vision_manager import vision_manager
from app.ui.styles import HUD_DARK_STYLESHEET


class WelcomePage(QWizardPage):
    def __init__(self):
        super().__init__()
        self.setTitle("Bem-vindo ao JARVIS")
        self.setSubTitle("Assistente Pessoal Inteligente Multimodal para Desktop")

        layout = QVBoxLayout(self)
        layout.setSpacing(16)

        info = QLabel(
            "O JARVIS está pronto para ser configurado no seu computador.\n\n"
            "• Escolha um único provedor de IA (OpenAI, Gemini ou Claude);\n"
            "• Suas chaves de API ficam guardadas com segurança no Windows;\n"
            "• Todo o processamento de voz, visão e banco de memória é 100% local.\n\n"
            "Clique em 'Avançar' para iniciar o assistente de configuração."
        )
        info.setWordWrap(True)
        info.setStyleSheet("font-size: 14px; line-height: 1.5; color: #cbd5e1;")
        layout.addWidget(info)


class ProviderPage(QWizardPage):
    def __init__(self):
        super().__init__()
        self.setTitle("Passo 1: Escolha seu Provedor de IA")
        self.setSubTitle("Selecione qual inteligência artificial você deseja utilizar:")

        layout = QVBoxLayout(self)
        layout.setSpacing(14)

        self.btn_group = QButtonGroup(self)

        self.rb_openai = QRadioButton("OpenAI (GPT-4o, GPT-4o-mini, Realtime)")
        self.rb_gemini = QRadioButton("Google Gemini (Gemini 2.0 Flash, Gemini 1.5 Pro)")
        self.rb_claude = QRadioButton("Anthropic Claude (Claude 3.5 Sonnet, Claude 3.5 Haiku)")

        # Seleciona padrao atual
        current = app_config.ai.provider.lower()
        if current == "gemini":
            self.rb_gemini.setChecked(True)
        elif current in ("anthropic", "claude"):
            self.rb_claude.setChecked(True)
        else:
            self.rb_openai.setChecked(True)

        self.btn_group.addButton(self.rb_openai, 1)
        self.btn_group.addButton(self.rb_gemini, 2)
        self.btn_group.addButton(self.rb_claude, 3)

        for rb in (self.rb_openai, self.rb_gemini, self.rb_claude):
            rb.setStyleSheet("font-size: 14px; padding: 6px;")
            layout.addWidget(rb)

    def get_selected_provider(self) -> str:
        if self.rb_gemini.isChecked():
            return "gemini"
        elif self.rb_claude.isChecked():
            return "claude"
        return "openai"


class ApiKeyPage(QWizardPage):
    def __init__(self):
        super().__init__()
        self.setTitle("Passo 2: Chave de API e Modelo")
        self.setSubTitle("Informe sua chave de API para o provedor selecionado:")

        layout = QVBoxLayout(self)
        layout.setSpacing(12)

        self.key_input = QLineEdit()
        self.key_input.setPlaceholderText("Cole sua API Key aqui...")
        self.key_input.setEchoMode(QLineEdit.EchoMode.Password)
        layout.addWidget(QLabel("Chave de API:"))
        layout.addWidget(self.key_input)

        self.model_combo = QComboBox()
        layout.addWidget(QLabel("Modelo Recomendado:"))
        layout.addWidget(self.model_combo)

        # Botao de Teste
        test_layout = QHBoxLayout()
        self.test_btn = QPushButton("Testar Conexão com a IA")
        self.test_btn.clicked.connect(self._test_connection)
        self.status_lbl = QLabel("")
        self.status_lbl.setStyleSheet("font-weight: bold;")
        test_layout.addWidget(self.test_btn)
        test_layout.addWidget(self.status_lbl)
        test_layout.addStretch()
        layout.addLayout(test_layout)

    def initializePage(self):
        wizard: SetupWizard = self.wizard()
        prov = wizard.provider_page.get_selected_provider()
        
        # Popula combo de modelos
        self.model_combo.clear()
        models = RECOMMENDED_MODELS.get(prov, {}).get("recommended", ["default"])
        self.model_combo.addItems(models)

        # Carrega chave salva se houver
        saved_key = secrets_manager.get_api_key(prov)
        if saved_key:
            self.key_input.setText(saved_key)

    def _test_connection(self):
        prov = self.wizard().provider_page.get_selected_provider()
        key = self.key_input.text().strip()
        model = self.model_combo.currentText().strip()

        if not key:
            self.status_lbl.setText("Informe a chave de API.")
            self.status_lbl.setStyleSheet("color: #ef4444;")
            return

        self.status_lbl.setText("Testando conexão...")
        self.status_lbl.setStyleSheet("color: #00d2ff;")
        self.test_btn.setEnabled(False)

        async def _test():
            provider = AIProviderFactory.create_provider(
                provider_name=prov,
                model_name=model,
                api_key=key
            )
            success, msg = await provider.test_connection()
            return success, msg

        try:
            loop = asyncio.new_event_loop()
            success, msg = loop.run_until_complete(_test())
            loop.close()

            if success:
                self.status_lbl.setText("● Conexão Estabelecida com Sucesso!")
                self.status_lbl.setStyleSheet("color: #10b981;")
                # Salva chave no Keyring
                secrets_manager.set_api_key(prov, key)
                app_config.ai.provider = prov
                app_config.ai.model = model
                app_config.save()
            else:
                self.status_lbl.setText(f"Falha: {msg}")
                self.status_lbl.setStyleSheet("color: #ef4444;")
        except Exception as e:
            self.status_lbl.setText(f"Erro: {str(e)}")
            self.status_lbl.setStyleSheet("color: #ef4444;")
        finally:
            self.test_btn.setEnabled(True)


class HardwarePage(QWizardPage):
    def __init__(self):
        super().__init__()
        self.setTitle("Passo 3: Microfone e Alto-falante")
        self.setSubTitle("Selecione seus dispositivos de áudio e faça um teste:")

        layout = QVBoxLayout(self)
        layout.setSpacing(12)

        # Microfone
        layout.addWidget(QLabel("Microfone (Entrada):"))
        self.mic_combo = QComboBox()
        layout.addWidget(self.mic_combo)

        # Alto-falante
        layout.addWidget(QLabel("Alto-falante (Saída):"))
        self.speaker_combo = QComboBox()
        layout.addWidget(self.speaker_combo)

        # Teste de Voz
        btn_layout = QHBoxLayout()
        self.test_voice_btn = QPushButton("Testar Voz do JARVIS")
        self.test_voice_btn.clicked.connect(self._test_voice)
        btn_layout.addWidget(self.test_voice_btn)
        btn_layout.addStretch()
        layout.addLayout(btn_layout)

    def initializePage(self):
        self.mic_combo.clear()
        mics = microphone.list_input_devices()
        for m in mics:
            self.mic_combo.addItem(m["name"], m["index"])

        self.speaker_combo.clear()
        speakers = speaker.list_output_devices()
        for s in speakers:
            self.speaker_combo.addItem(s["name"], s["index"])

    def _test_voice(self):
        mic_idx = self.mic_combo.currentData()
        speaker_idx = self.speaker_combo.currentData()

        app_config.audio.input_device_index = mic_idx
        app_config.audio.output_device_index = speaker_idx
        app_config.save()

        local_tts.speak("Sistemas de áudio do JARVIS configurados com sucesso.")


class ReadyPage(QWizardPage):
    def __init__(self):
        super().__init__()
        self.setTitle("Tudo Pronto!")
        self.setSubTitle("O JARVIS está pronto para atendê-lo.")

        layout = QVBoxLayout(self)
        layout.setSpacing(16)

        ready_label = QLabel(
            "Configuração concluída com sucesso!\n\n"
            "Como usar o JARVIS:\n"
            "• Fale 'Jarvis' no microfone para chamar o assistente;\n"
            "• Pergunte sobre seu computador ('Como está a CPU?');\n"
            "• Peça para abrir programas ('Abra o Spotify', 'Abra o Chrome');\n"
            "• Faça perguntas visuais mostrando objetos para a webcam;\n"
            "• Guarde informações ('Lembre que meu carro é um Corolla').\n\n"
            "Clique em 'Concluir' para abrir a central principal do JARVIS."
        )
        ready_label.setWordWrap(True)
        ready_label.setStyleSheet("font-size: 14px; line-height: 1.5; color: #38bdf8;")
        layout.addWidget(ready_label)


class SetupWizard(QWizard):
    """Assistente de primeira execucao do JARVIS."""

    def __init__(self, parent: QWidget = None):
        super().__init__(parent)
        self.setWindowTitle("JARVIS — Assistente de Configuração")
        self.resize(640, 480)
        self.setStyleSheet(HUD_DARK_STYLESHEET)

        self.welcome_page = WelcomePage()
        self.provider_page = ProviderPage()
        self.api_key_page = ApiKeyPage()
        self.hardware_page = HardwarePage()
        self.ready_page = ReadyPage()

        self.addPage(self.welcome_page)
        self.addPage(self.provider_page)
        self.addPage(self.api_key_page)
        self.addPage(self.hardware_page)
        self.addPage(self.ready_page)

        self.button(QWizard.WizardButton.FinishButton).clicked.connect(self._on_finish)

    def _on_finish(self):
        app_config.system.first_run_completed = True
        app_config.save()
