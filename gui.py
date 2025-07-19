# gui.py
import os
import sys
import json
import requests
import threading
from typing import Iterable

from PyQt5.QtWidgets import (
    QApplication, QMainWindow, QTextBrowser, QLineEdit,
    QPushButton, QVBoxLayout, QWidget
)
from PyQt5.QtCore import pyqtSignal, QObject, QThread

from core.config import settings
from core.voice_handler import record_audio, synthesize_speech_stream


# ---------------- 线程安全的信号 ----------------
class WorkerSignals(QObject):
    append_chat = pyqtSignal(str)
    set_input   = pyqtSignal(str)
    enable_record = pyqtSignal(bool)


# ---------------- 聊天请求线程 ----------------
class ChatThread(QThread):
    def __init__(self, api_url: str, text: str):
        super().__init__()
        self.api_url = api_url
        self.text = text
        self.signals = WorkerSignals()

    def run(self):
        try:
            response = requests.post(
                f"{self.api_url}/chat",
                json={"message": self.text},
                stream=True
            )
            response.raise_for_status()

            full_response = ""
            for chunk in response.iter_content(chunk_size=None):
                if chunk:
                    decoded = chunk.decode("utf-8")
                    full_response += decoded
                    self.signals.append_chat.emit(decoded)

            def gen():
                yield full_response
            threading.Thread(
                target=synthesize_speech_stream,
                args=(gen(),)
            ).start()

        except requests.RequestException as e:
            self.signals.append_chat.emit(f"\n**Error:** {e}\n\n---\n")


# ---------------- 录音线程 ----------------
class RecordThread(QThread):
    def __init__(self, api_url: str):
        super().__init__()
        self.api_url = api_url
        self.signals = WorkerSignals()

    def run(self):
        try:
            audio_path = record_audio()
            with open(audio_path, "rb") as f:
                files = {"file": (os.path.basename(audio_path), f, "audio/wav")}
                r = requests.post(f"{self.api_url}/transcribe", files=files)
            r.raise_for_status()
            text = r.json().get("transcription", "")
            self.signals.set_input.emit(text)
        except Exception as e:
            print("Record/Transcribe error:", e)
        finally:
            self.signals.enable_record.emit(True)


# ---------------- 主窗口 ----------------
class JarvisGUI(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Jarvis AI Assistant")
        self.setGeometry(100, 100, 800, 600)

        # 1. 记录运行中的线程
        self.threads = []

        # UI
        self.chat_display = QTextBrowser()
        self.chat_display.setOpenExternalLinks(True)

        self.input_box = QLineEdit()
        self.input_box.setPlaceholderText("Type your message here or press Record...")

        self.send_btn = QPushButton("Send")
        self.rec_btn = QPushButton("Record (5s)")

        # Layout
        layout = QVBoxLayout()
        layout.addWidget(self.chat_display)
        layout.addWidget(self.input_box)
        layout.addWidget(self.send_btn)
        layout.addWidget(self.rec_btn)

        container = QWidget()
        container.setLayout(layout)
        self.setCentralWidget(container)

        # Signals
        self.api_url = f"http://{settings.API_HOST}:{settings.API_PORT}"
        self.send_btn.clicked.connect(self.on_send)
        self.input_box.returnPressed.connect(self.on_send)
        self.rec_btn.clicked.connect(self.on_record)

    # 2. 追加消息
    def append_md(self, role: str, text: str):
        if role.lower() == "user":
            html = f"<b>You:</b><br/>{text}<hr/>"
        else:
            html = f"<b>Jarvis:</b><br/>{text}"
        self.chat_display.append(html)

    # 3. 发送文本
    def on_send(self):
        text = self.input_box.text().strip()
        if not text:
            return
        self.append_md("user", text)
        self.input_box.clear()

        thread = ChatThread(self.api_url, text)
        thread.signals.append_chat.connect(self.chat_display.insertPlainText)
        thread.finished.connect(lambda: self.threads.remove(thread))
        self.threads.append(thread)
        thread.start()

    # 4. 录音
    def on_record(self):
        self.rec_btn.setEnabled(False)
        self.rec_btn.setText("Recording...")

        thread = RecordThread(self.api_url)
        thread.signals.set_input.connect(self.input_box.setText)
        thread.signals.enable_record.connect(self.rec_btn.setEnabled)
        thread.signals.enable_record.connect(lambda _: self.rec_btn.setText("Record (5s)"))
        thread.signals.set_input.connect(self.on_send)
        thread.finished.connect(lambda: self.threads.remove(thread))
        self.threads.append(thread)
        thread.start()

    # 5. 优雅退出
    def closeEvent(self, event):
        for t in self.threads[:]:
            if t.isRunning():
                t.quit()
                t.wait()
        event.accept()


# ---------------- 入口 ----------------
if __name__ == "__main__":
    app = QApplication(sys.argv)
    win = JarvisGUI()
    win.show()
    sys.exit(app.exec_())