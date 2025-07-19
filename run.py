# run.py
import threading
import uvicorn
import sys
from PyQt5.QtWidgets import QApplication

from api import app as fastapi_app
from gui import JarvisGUI
from core.config import settings

def run_fastapi():
    """在单独的线程中运行FastAPI服务器"""
    print("Starting FastAPI server...")
    uvicorn.run(
        fastapi_app,
        host=settings.API_HOST,
        port=settings.API_PORT,
        log_level="info" # 在生产中可以设置为 "warning"
    )
    print("FastAPI server stopped.")

def run_pyqt():
    """在主线程中运行PyQt5 GUI"""
    print("Starting PyQt5 GUI...")
    app = QApplication(sys.argv)
    main_win = JarvisGUI()
    main_win.show()
    sys.exit(app.exec_())

if __name__ == "__main__":
    # 创建并启动FastAPI服务器的后台线程
    # 设置为守护线程（daemon=True），这样当主线程（GUI）退出时，该线程也会被强制终止
    api_thread = threading.Thread(target=run_fastapi, daemon=True)
    api_thread.start()

    # 在主线程中运行GUI
    # GUI应用通常需要在主线程中运行
    run_pyqt()