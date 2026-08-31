"""
Estilos e Temas Visuais (QSS) para a Interface do JARVIS.
Estetica futurista e elegante HUD Dark Theme com acentos em Ciano Neon, Azul Eletrico e Grafite Profundo.
"""

HUD_DARK_STYLESHEET = """
/* === CONFIGURACOES GLOBAIS === */
QWidget {
    background-color: #0b0e14;
    color: #e2e8f0;
    font-family: 'Segoe UI', 'Segoe UI Variable', -apple-system, sans-serif;
    font-size: 13px;
    selection-background-color: #00d2ff;
    selection-color: #0b0e14;
}

/* === JANELAS E PAINEIS === */
QMainWindow, QDialog {
    background-color: #080a0f;
    border: 1px solid #1e293b;
}

QFrame.card {
    background-color: #111722;
    border: 1px solid #1e293b;
    border-radius: 12px;
    padding: 12px;
}

QFrame.card:hover {
    border: 1px solid #00d2ff;
}

QGroupBox {
    background-color: #111722;
    border: 1px solid #1e293b;
    border-radius: 8px;
    margin-top: 24px;
    padding: 16px;
    font-weight: bold;
    color: #00d2ff;
}

QGroupBox::title {
    subcontrol-origin: margin;
    subcontrol-position: top left;
    padding: 2px 10px;
    background-color: #080a0f;
    border: 1px solid #00d2ff;
    border-radius: 4px;
    color: #00d2ff;
}

/* === BOTOES === */
QPushButton {
    background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #1e293b, stop:1 #0f172a);
    color: #f8fafc;
    border: 1px solid #334155;
    border-radius: 8px;
    padding: 8px 18px;
    font-weight: 600;
    font-size: 13px;
    min-height: 24px;
}

QPushButton:hover {
    background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #0284c7, stop:1 #0369a1);
    border: 1px solid #38bdf8;
    color: #ffffff;
}

QPushButton:pressed {
    background-color: #075985;
    border: 1px solid #0284c7;
}

QPushButton.primary {
    background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #00d2ff, stop:1 #3a7bd5);
    color: #0b0e14;
    border: 1px solid #00d2ff;
    font-weight: bold;
}

QPushButton.primary:hover {
    background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #38bdf8, stop:1 #60a5fa);
    border: 1px solid #ffffff;
    color: #000000;
}

QPushButton.danger {
    background-color: #7f1d1d;
    border: 1px solid #ef4444;
    color: #fef2f2;
}

QPushButton.danger:hover {
    background-color: #991b1b;
    border: 1px solid #f87171;
}

QPushButton.icon-btn {
    background-color: #1e293b;
    border: 1px solid #334155;
    border-radius: 20px;
    min-width: 40px;
    max-width: 40px;
    min-height: 40px;
    max-height: 40px;
}

QPushButton.icon-btn:hover {
    border: 1px solid #00d2ff;
    background-color: #0f172a;
}

/* === CAMPOS DE ENTRADA === */
QLineEdit, QTextEdit, QPlainTextEdit {
    background-color: #0f172a;
    color: #f1f5f9;
    border: 1px solid #334155;
    border-radius: 8px;
    padding: 8px 12px;
    font-size: 13px;
}

QLineEdit:focus, QTextEdit:focus, QPlainTextEdit:focus {
    border: 1px solid #00d2ff;
    background-color: #0b1329;
}

/* === COMBOBOX E SLIDERS === */
QComboBox {
    background-color: #0f172a;
    color: #f8fafc;
    border: 1px solid #334155;
    border-radius: 8px;
    padding: 6px 12px;
    min-height: 24px;
}

QComboBox:hover {
    border: 1px solid #00d2ff;
}

QComboBox::drop-down {
    border: none;
    width: 24px;
}

QComboBox QAbstractItemView {
    background-color: #0f172a;
    border: 1px solid #00d2ff;
    selection-background-color: #0284c7;
    selection-color: #ffffff;
    color: #f8fafc;
}

QSlider::groove:horizontal {
    height: 6px;
    background: #1e293b;
    border-radius: 3px;
}

QSlider::sub-page:horizontal {
    background: #00d2ff;
    border-radius: 3px;
}

QSlider::handle:horizontal {
    background: #ffffff;
    border: 2px solid #00d2ff;
    width: 16px;
    margin-top: -5px;
    margin-bottom: -5px;
    border-radius: 8px;
}

/* === SCROLLBARS === */
QScrollBar:vertical {
    border: none;
    background-color: #080a0f;
    width: 8px;
    margin: 0px;
}

QScrollBar::handle:vertical {
    background-color: #334155;
    min-height: 30px;
    border-radius: 4px;
}

QScrollBar::handle:vertical:hover {
    background-color: #00d2ff;
}

QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
    height: 0px;
}

/* === TAB WIDGET === */
QTabWidget::pane {
    border: 1px solid #1e293b;
    background-color: #0b0e14;
    border-radius: 8px;
}

QTabBar::tab {
    background-color: #0f172a;
    color: #94a3b8;
    padding: 10px 20px;
    margin-right: 4px;
    border-top-left-radius: 8px;
    border-top-right-radius: 8px;
    font-weight: 600;
}

QTabBar::tab:selected {
    background-color: #1e293b;
    color: #00d2ff;
    border-bottom: 2px solid #00d2ff;
}

QTabBar::tab:hover:!selected {
    color: #f8fafc;
    background-color: #162032;
}

/* === TABELAS E LISTAS === */
QTableWidget, QListWidget {
    background-color: #0f172a;
    border: 1px solid #1e293b;
    border-radius: 8px;
    gridline-color: #1e293b;
    color: #f8fafc;
}

QHeaderView::section {
    background-color: #1e293b;
    color: #00d2ff;
    padding: 8px;
    border: 1px solid #0b0e14;
    font-weight: bold;
}

QTableWidget::item:selected, QListWidget::item:selected {
    background-color: #0369a1;
    color: #ffffff;
}

/* === BADGES E STATUS === */
QLabel.badge-online {
    background-color: #064e3b;
    color: #34d399;
    border: 1px solid #10b981;
    border-radius: 10px;
    padding: 2px 10px;
    font-weight: bold;
    font-size: 11px;
}

QLabel.badge-offline {
    background-color: #7f1d1d;
    color: #f87171;
    border: 1px solid #ef4444;
    border-radius: 10px;
    padding: 2px 10px;
    font-weight: bold;
    font-size: 11px;
}

QLabel.badge-active {
    background-color: #0c4a6e;
    color: #38bdf8;
    border: 1px solid #0284c7;
    border-radius: 10px;
    padding: 2px 10px;
    font-weight: bold;
    font-size: 11px;
}
"""
