# api.py

import uvicorn
from fastapi import FastAPI, HTTPException, UploadFile, File
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
import asyncio
import shutil
import tempfile
import os

# 导入我们的配置和核心处理器
from core.config import settings
from core.llm_handler import get_chat_response_stream
from core.voice_handler import transcribe_audio_file, synthesize_speech_and_play

# 初始化FastAPI应用
app = FastAPI(
    title="My Jarvis AI Assistant API",
    description="API for a multi-modal AI assistant.",
    version="1.0.0"
)

# --- API数据模型 ---

class ChatRequest(BaseModel):
    """聊天请求的数据模型"""
    message: str
    session_id: str = "default_session" # 用于支持多用户会话

class TTSRequest(BaseModel):
    """文本转语音请求的数据模型"""
    text: str

# --- API路由/端点 ---

@app.get("/")
async def read_root():
    """根端点，用于健康检查"""
    return {"status": "ok", "message": "Welcome to Jarvis API!"}

@app.post("/chat")
async def chat_endpoint(request: ChatRequest):
    """
    处理聊天请求并以流式响应返回AI的回答。
    """
    try:
        # 调用LLM处理器获取一个异步生成器
        response_generator = get_chat_response_stream(request.message, request.session_id)
        # 使用StreamingResponse将生成器的内容流式传输给客户端
        return StreamingResponse(response_generator, media_type="text/event-stream")
    except Exception as e:
        # 异常处理
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/transcribe")
async def transcribe_endpoint(file: UploadFile = File(...)):
    """接收音频文件并返回转录文本"""
    try:
        # 将上传的文件保存到临时位置
        with tempfile.NamedTemporaryFile(delete=False, suffix=".wav") as tmp:
            shutil.copyfileobj(file.file, tmp)
            tmp_path = tmp.name
        
        # 调用语音处理器进行转录
        text = transcribe_audio_file(tmp_path)
        
        # 清理临时文件
        os.remove(tmp_path)
        
        return {"transcription": text}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        # 确保文件句柄被关闭
        await file.close()

@app.post("/synthesize")
async def synthesize_endpoint(request: TTSRequest):
    """接收文本并触发语音合成（在服务器端播放）"""
    try:
        # 注意：这是一个后台任务，它会在服务器端播放声音。
        # 在实际应用中，您可能希望返回音频流让客户端播放。
        synthesize_speech_and_play(request.text)
        return {"status": "ok", "message": "Speech synthesis started."}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# --- 用于直接运行API服务器的入口 ---
if __name__ == "__main__":
    # 使用uvicorn来运行FastAPI应用
    # reload=True可以在代码变更时自动重启服务器，非常适合开发阶段
    uvicorn.run(
        "api:app", 
        host=settings.API_HOST, 
        port=settings.API_PORT, 
        reload=True
    )