from PyQt6.QtWidgets import QWidget, QLabel
from PyQt6.QtCore import (
    Qt, QPropertyAnimation, QTimer, QPointF, pyqtProperty
)
from PyQt6.QtGui import (
    QPainter, QColor, QFont, QLinearGradient, QBrush
)
import random
import math


class Particle:
    def __init__(self, pos):
        self.pos = QPointF(pos)
        angle = random.uniform(0, 2 * math.pi)
        speed = random.uniform(1, 4)
        self.velocity = QPointF(math.cos(angle) * speed, math.sin(angle) * speed)
        self.life = 1.0
        self.size = random.uniform(1, 4)
        self.color = QColor(100, 255, 255, 255)

    def update(self):
        self.pos += self.velocity
        self.life -= 0.02
        alpha = max(0, int(255 * self.life))
        self.color.setAlpha(alpha)
        self.size *= 0.97


class TypewriterLabel(QLabel):
    def __init__(self, full_text, interval=100, parent=None):
        super().__init__(parent)
        self.full_text = full_text
        self.setText("")
        self.setStyleSheet("color: white;")
        self.setFont(QFont("Consolas", 28, QFont.Weight.Bold))
        self.index = 0
        self.timer = QTimer()
        self.timer.timeout.connect(self.add_next_char)
        self.interval = interval

    def start(self):
        self.index = 0
        self.setText("")
        self.timer.start(self.interval)

    def add_next_char(self):
        if self.index < len(self.full_text):
            self.setText(self.text() + self.full_text[self.index])
            self.index += 1
        else:
            self.timer.stop()
            self.parent().start_particle_burst()


class NexusSplash(QWidget):
    def __init__(self, next_step_callback):
        super().__init__()
        self.setWindowFlag(Qt.WindowType.FramelessWindowHint)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setFixedSize(600, 400)

        self.opacity = 0.0
        self._dummy = 0.0
        self.particles = []
        self.particle_timer = QTimer()
        self.particle_timer.timeout.connect(self.animate_particles)

        self.next_step_callback = next_step_callback

        self.label = TypewriterLabel("Nexus Editor 2.0", interval=100, parent=self)
        self.label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.label.setGeometry(0, self.height() // 2 - 40, self.width(), 80)

        self.fade_anim = QPropertyAnimation(self, b"dummy")
        self.fade_anim.setDuration(1500)
        self.fade_anim.setStartValue(0.0)
        self.fade_anim.setEndValue(1.0)
        self.fade_anim.valueChanged.connect(self.on_opacity_change)
        self.fade_anim.finished.connect(self.label.start)
        self.fade_anim.start()

    def on_opacity_change(self, val):
        self.opacity = val
        self.update()

    def start_particle_burst(self):
        center = QPointF(self.width() / 2, self.height() / 2)
        for _ in range(150):
            self.particles.append(Particle(center))

        self.particle_timer.start(16)
        QTimer.singleShot(2000, self.start_fade_out)

    def animate_particles(self):
        for p in self.particles[:]:
            p.update()
            if p.life <= 0 or p.size <= 0.1:
                self.particles.remove(p)
        self.update()

    def start_fade_out(self):
        self.fade_out_anim = QPropertyAnimation(self, b"dummy")
        self.fade_out_anim.setDuration(1000)
        self.fade_out_anim.setStartValue(self.opacity)
        self.fade_out_anim.setEndValue(0.0)
        self.fade_out_anim.valueChanged.connect(self.on_opacity_change)
        self.fade_out_anim.finished.connect(self.launch_main)
        self.fade_out_anim.start()

    def launch_main(self):
        self.close()
        self.next_step_callback()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        # Gradient background
        gradient = QLinearGradient(0, 0, 0, self.height())
        gradient.setColorAt(0, QColor(10, 10, 30, int(self.opacity * 255)))
        gradient.setColorAt(1, QColor(20, 20, 50, int(self.opacity * 255)))
        painter.fillRect(self.rect(), QBrush(gradient))

        # Particles
        for p in self.particles:
            painter.setBrush(p.color)
            painter.setPen(Qt.PenStyle.NoPen)
            painter.drawEllipse(p.pos, p.size, p.size)

    def get_dummy(self):
        return self._dummy

    def set_dummy(self, value):
        self._dummy = value

    dummy = pyqtProperty(float, fget=get_dummy, fset=set_dummy)
