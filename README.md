# 🤖 JARVIS — Assistente Pessoal Multimodal Local para Desktop

O **JARVIS** é um assistente pessoal desktop completo, modular, rápido e multimodal para **Windows 10 e Windows 11 (64-bit)**.

Inspirado no conceito de um verdadeiro copiloto inteligente e contínuo, o JARVIS conecta-se a **uma única API de Inteligência Artificial** à sua escolha (**OpenAI**, **Google Gemini** ou **Anthropic Claude**), enquanto todo o restante da pilha (síntese de voz, reconhecimento de fala, detecção de palavra-chave, visão computacional, banco de dados de memória semântica, agendamento de lembretes e automação de ferramentas do computador) é executado **100% localmente no seu computador**.

---

## ⚡ Principais Funcionalidades

* 🎙️ **Conversação por Voz Contínua e Wake Word**: Ativação local pela palavra **"Jarvis"**, suporte a Push-to-Talk e modo contínuo sem gastar APIs externas para escuta.
* 🛑 **Barge-in / Interrupção Instantânea**: Interrompa a resposta do Jarvis a qualquer momento dizendo *"Jarvis, pare"*, *"Silêncio"* ou simplesmente começando a falar.
* 👁️ **Visão Multimodal com Webcam e Análise de Tela**: Aponte objetos para a câmera ou pergunte *"O que você está vendo?"* ou *"O que está acontecendo nessa tela?"*. O Jarvis amostra e envia imagens inteligentemente apenas quando necessário.
* 🧠 **Memória Semântica Persistente com Busca Vetorial**: Lembra de fatos, preferências e conversas passadas usando embeddings e SQLite local. Comandos de voz diretos como *"Jarvis, lembre que meu carro é um Corolla"* ou *"Jarvis, esqueça tudo sobre..."*.
* 🛠️ **Ferramentas do Sistema (Function Calling Seguro)**:
  * Consultar status do PC (CPU, Memória RAM, Disco, Bateria, Rede);
  * Abrir aplicativos instalados (Spotify, Chrome, VS Code, Bloco de Notas, etc.);
  * Pesquisar arquivos nas pastas do usuário;
  * Ler e escrever na Área de Transferência (Clipboard);
  * Capturar screenshots;
  * Criar e ler notas rápidas locais;
  * Agendar lembretes persistentes com notificações nativas do Windows.
* 🌐 **HUD Futurista em PySide6**: Interface moderna com tema escuro, central animada (ORB com efeitos de pulso e partículas reativos), visualizador de áudio (VU Meter), preview colapsável de câmera e barra de status.
* 🔒 **Privacidade e Segurança**: Chaves de API salvas no **Windows Credential Manager (Keyring)**. Nenhum frame de vídeo gravado em disco (RAM-only). Classificação de segurança de ferramentas (SAFE, SENSITIVE, DESTRUCTIVE com confirmação).
* 🗔 **System Tray**: Minimiza para a bandeja do sistema mantendo monitoramento de lembretes e escuta em segundo plano.

---

## 💻 Requisitos do Sistema

* **Sistema Operacional**: Windows 10 ou Windows 11 (64-bit).
* **Python**: Versão 3.12 ou 3.13 (64-bit).
* **Hardware**:
  * Microfone e Alto-falante;
  * Webcam (opcional, para recursos de visão);
  * 4 GB de memória RAM mínima (8 GB recomendados).
* **Chave de API (Apenas UMA das seguintes)**:
  * OpenAI API Key (`sk-...`), OU
  * Google Gemini API Key (`AIza...`), OU
  * Anthropic Claude API Key (`sk-ant-...`).

---

## 🚀 Instalação Rápida

### Opção 1: Via Prompt de Comando (CMD)
Dê um duplo clique no arquivo:
```cmd
setup.bat
```

### Opção 2: Via PowerShell
Execute:
```powershell
.\setup.ps1
```

O instalador irá automaticamente:
1. Validar a instalação do Python;
2. Criar o ambiente virtual isolado `.venv`;
3. Instalar todas as dependências oficiais necessárias;
4. Inicializar o banco de dados SQLite local (`data/jarvis.db`);
5. Executar o auto-diagnóstico do sistema.

---

## 🏃 Como Executar

Após a instalação, basta executar:

```cmd
run.bat
```
*(ou no PowerShell: `.\run.ps1`)*

No **primeiro uso**, o **Setup Wizard (Assistente de Configuração)** será aberto para você escolher seu provedor de IA, colar sua chave de API, testar a conexão e selecionar seus dispositivos de áudio e câmera.

---

## 🩺 Diagnóstico e Auto-Teste do Sistema

Para verificar a integridade de hardware, banco de dados, chaves e dependências, execute a qualquer momento:

```powershell
.venv\Scripts\python.exe -m app.doctor
```

Exemplo de saída:
```text
=======================================================
              JARVIS DIAGNOSTIC & SELF-TEST             
=======================================================

Python (3.13.5) ...................... [OK]
Database (SQLite) ...................... [OK] (7 tabelas)
Microfone .............................. [OK] (14 detectados)
Alto-falante ........................... [OK] (14 detectados)
Camera (OpenCV DirectShow) ............. [OK] (1 detectada)
Keyring (Windows Credential Locker) .... [OK]
Conexao Internet ....................... [OK]
Motor Local TTS (SAPI5) ................ [OK] (9 vozes)
Embeddings Semanticos Locais ........... [OK] (dimensao 384)
Provedor IA (OPENAI) .................. [OK] (Chave Configurada)

-------------------------------------------------------
                     SYSTEM READY                      
=======================================================
```

---

## 🗣️ Exemplos de Conversação e Comandos

### 1. Visão e Câmera
> **Você:** *"Jarvis, o que você está vendo aqui?"*  
> **Jarvis:** *(captura frame da webcam)* *"Vejo uma mesa de trabalho com um notebook, uma caneta e um copo de café."*

### 2. Memória Semântica
> **Você:** *"Jarvis, lembre que meu carro é um Corolla."*  
> **Jarvis:** *"Certo, guardei em minha memória: 'meu carro é um Corolla'."*  
> *(dias depois)*  
> **Você:** *"Qual é o meu carro mesmo?"*  
> **Jarvis:** *"Você me disse que seu carro é um Corolla."*

### 3. Diagnóstico do Computador
> **Você:** *"Jarvis, como está o uso do meu computador?"*  
> **Jarvis:** *(executa get_system_status)* *"Seu processador está em aproximadamente 14%, a memória RAM está em 58% e você possui 210 GB livres na unidade C:."*

### 4. Controle e Automação
> **Você:** *"Jarvis, abra o Spotify."*  
> **Jarvis:** *(executa open_application)* *"Spotify aberto com sucesso."*

### 5. Lembretes Locais
> **Você:** *"Jarvis, me lembre às 17:30 de enviar o relatório."*  
> **Jarvis:** *"Lembrete agendado para 31/08 às 17:30: 'enviar o relatório'."*  
> *(no horário exato, o Windows exibirá uma notificação e o Jarvis avisará por voz)*

---

## 📦 Gerando Executável Standalone (.exe)

Para gerar uma versão executável compilada para Windows (sem necessidade de Python instalado):

```powershell
.\build.ps1
```

O aplicativo standalone será gerado em:
```
dist/Jarvis/Jarvis.exe
```

Opcionalmente, caso utilize o **Inno Setup**, você pode compilar o script `installer.iss` para gerar o instalador `JarvisSetup.exe`.

---

## 🧪 Executando os Testes Automatizados

O projeto inclui uma suíte completa de testes unitários e de integração:

```powershell
.venv\Scripts\pytest.exe -v
```

---

## 🔒 Arquitetura e Privacidade

* **Armazenamento 100% Local**: O banco `data/jarvis.db`, o histórico e as configurações permanecem no seu computador.
* **Privacidade da Câmera**: Os frames de vídeo para análise da IA são mantidos exclusivamente em memória RAM e descartados após o processamento. Nenhuma gravação contínua é feita.
* **Segurança de Chaves**: As chaves de API nunca são registradas em arquivos de log nem armazenadas em texto plano sem proteção.

---

## 📄 Licença

Desenvolvido para uso pessoal e profissional no Windows.
