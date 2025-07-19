# core/config.py
import os
from pydantic_settings import BaseSettings, SettingsConfigDict

# 获取项目根目录的绝对路径
# 这使得无论从哪里运行脚本，路径都能保持正确
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

class Settings(BaseSettings):
    """
    应用配置类，自动从.env文件和环境变量中读取配置。
    """
    #.env文件的路径
    model_config = SettingsConfigDict(env_file=os.path.join(BASE_DIR, '.env'), env_file_encoding='utf-8')

    # LLM API配置
    DEEPSEEK_API_KEY: str
    DEEPSEEK_BASE_URL: str = "https://api.deepseek.com/v1"
    DEEPSEEK_MODEL: str = "deepseek-chat"

    # STT API配置 (Whisper)
    OPENAI_API_KEY: str
    OPENAI_BASE_URL: str = "https://api.openai.com/v1"
    WHISPER_MODEL: str = "whisper-1"

    # TTS API配置
    ELEVENLABS_API_KEY: str

    # Neo4j数据库配置
    NEO4J_URI: str
    NEO4J_USER: str
    NEO4J_PASSWORD: str

    # API服务器配置
    API_HOST: str = "127.0.0.1"
    API_PORT: int = 8000

# 创建一个全局可用的配置实例
settings = Settings()

# 打印部分配置以验证加载成功（仅用于调试）
if __name__ == '__main__':
    print("--- Configuration Loaded ---")
    print(f"DeepSeek Model: {settings.DEEPSEEK_MODEL}")
    print(f"Neo4j URI: {settings.NEO4J_URI}")
    print(f"Base Directory: {BASE_DIR}")
    print("--------------------------")