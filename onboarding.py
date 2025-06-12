from PyQt6.QtWidgets import QWidget, QVBoxLayout, QLabel, QPushButton
from PyQt6.QtGui import QFont
from PyQt6.QtCore import Qt


class OnboardingScreen(QWidget):
    def __init__(self, finish_callback):
        super().__init__()
        self.setWindowTitle("Welcome to Nexus Editor 2.0")
        self.setFixedSize(700, 500)
        self.setStyleSheet("background-color: #1e1e1e; color: white; font-family: Consolas;")

        layout = QVBoxLayout(self)
        layout.setAlignment(Qt.AlignmentFlag.AlignTop)

        label = QLabel("👋 Welcome to Nexus Editor 2.0\n", self)
        label.setFont(QFont("Consolas", 20, QFont.Weight.Bold))
        label.setAlignment(Qt.AlignmentFlag.AlignCenter)

        features = QLabel("""
🚀 Features:
- Git status integration
- Full search and replace
- Integrated terminal
- Tabbed editing & split view
- Live preview for Markdown & HTML
- File/project sidebar

⌨️ Shortcuts:
- Ctrl+S: Save file
- Ctrl+T: Toggle theme
- Ctrl+K: Open folder
- Ctrl+\\: Split tabs
""", self)
        features.setFont(QFont("Consolas", 14))
        features.setAlignment(Qt.AlignmentFlag.AlignLeft)
        features.setStyleSheet("padding: 20px;")

        button = QPushButton("Start Editing", self)
        button.setFont(QFont("Consolas", 14))
        button.setStyleSheet("padding: 10px; background-color: #3a3a3a; color: white;")
        button.clicked.connect(lambda: self._finish(finish_callback))

        layout.addWidget(label)
        layout.addWidget(features)
        layout.addStretch()
        layout.addWidget(button, alignment=Qt.AlignmentFlag.AlignCenter)

    def _finish(self, callback):
        self.close()
        callback()
