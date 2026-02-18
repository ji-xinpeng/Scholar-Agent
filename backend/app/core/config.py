import os
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    PROJECT_NAME: str = "Scholar Agent"
    API_V1_STR: str = "/api/v1"

    # 数据库
    DATABASE_PATH: str = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), "data", "scholar_agent.db")

    # 上传目录
    UPLOAD_DIR: str = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), "data", "uploads")
    
    # 日志文件
    LOG_FILE_PATH: str = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), "data", "app.log")

    # 后端端口
    BACKEND_PORT: int = 8088

    # Redis
    REDIS_HOST: str = "localhost"
    REDIS_PORT: int = 6379
    REDIS_DB: int = 0
    REDIS_PASSWORD: str = ""
    REDIS_DEFAULT_TTL: int = 3600  # 默认缓存 1 小时

    # Qwen
    QWEN_API_KEY: str = "sk-ea68b4e98b634f37872b7ab3dbb51a7e"
    QWEN_BASE_URL: str = "https://dashscope.aliyuncs.com/compatible-mode/v1"
    QWEN_MODEL: str = "qwen-plus"

    # DeepSeek
    DEEPSEEK_API_KEY: str = "sk-cf60007aadf148aa9639fffed8f5bf2b"
    DEEPSEEK_BASE_URL: str = "https://api.deepseek.com"
    DEEPSEEK_MODEL: str = "deepseek-chat"

    # 默认 LLM 提供商
    DEFAULT_LLM_PROVIDER: str = "deepseek"

    class Config:
        case_sensitive = True
        env_file = ".env"


settings = Settings()
