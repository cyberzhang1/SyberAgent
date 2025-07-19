# core/voice_handler.py
from openai import OpenAI
from elevenlabs.client import ElevenLabs
from elevenlabs import play, stream
import sounddevice as sd
import numpy as np
from scipy.io.wavfile import write
import tempfile
import os

from.config import settings

# --- STT (Speech-to-Text) using Whisper ---
stt_client = OpenAI(
    api_key=settings.OPENAI_API_KEY,
    base_url=settings.OPENAI_BASE_URL
)

def transcribe_audio_file(file_path: str) -> str:
    """使用Whisper API转录音频文件"""
    with open(file_path, "rb") as audio_file:
        transcript = stt_client.audio.transcriptions.create(
            model=settings.WHISPER_MODEL,
            file=audio_file
        )
    return transcript.text

# --- TTS (Text-to-Speech) using ElevenLabs ---
tts_client = ElevenLabs(api_key=settings.ELEVENLABS_API_KEY)

def synthesize_speech_and_play(text: str):
    """合成语音并直接播放"""
    audio = tts_client.generate(
        text=text,
        voice="Rachel", # 可以选择你喜欢的声音
        model="eleven_multilingual_v2"
    )
    play(audio)

def synthesize_speech_stream(text_generator):
    """接收一个文本生成器，流式合成并播放语音"""
    audio_stream = tts_client.generate(
        text=text_generator,
        voice="Rachel",
        model="eleven_multilingual_v2",
        stream=True
    )
    stream(audio_stream)

# --- 音频录制功能 ---
def record_audio(duration: int = 5, sample_rate: int = 44100) -> str:
    """
    录制指定时长的音频并保存为临时WAV文件。
    返回文件路径。
    """
    print("开始录音...")
    recording = sd.rec(int(duration * sample_rate), samplerate=sample_rate, channels=1, dtype='int16')
    sd.wait() # 等待录音完成
    print("录音结束。")

    # 创建一个临时文件来保存录音
    temp_file = tempfile.NamedTemporaryFile(delete=False, suffix=".wav")
    write(temp_file.name, sample_rate, recording)
    return temp_file.name