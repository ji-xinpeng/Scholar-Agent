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

    # Redis（可选，未启用或连接失败时自动使用内存缓存）
    REDIS_ENABLED: bool = False  # 默认不依赖 Redis，设为 True 且启动 Redis 后可启用
    REDIS_HOST: str = "localhost"
    REDIS_PORT: int = 6379
    REDIS_DB: int = 0
    REDIS_PASSWORD: str = ""
    REDIS_DEFAULT_TTL: int = 3600  # 默认缓存 1 小时

    # 豆包 (Doubao) - 火山引擎
    DOUBAO_API_KEY: str = "2192cc18-ff14-41bd-a711-f4d35a85bc59"  # 已配置的 API Key
    DOUBAO_BASE_URL: str = "https://ark.cn-beijing.volces.com/api/v3"
    DOUBAO_MODEL: str = "doubao-seed-2-0-mini-260215"

    # 根据意图选择模型配置 - 豆包
    # 简单对话使用更便宜的模型
    SIMPLE_CHAT_MODEL: str = "doubao-seed-2-0-mini-260215"  # 豆包的经济模型
    
    # 论文问答使用适中的模型
    PAPER_QA_MODEL: str = "doubao-seed-2-0-lite-260215"
    
    # 智能体模式使用更强的模型
    AGENT_MODEL: str = "doubao-seed-2-0-pro-260215"  # 豆包的高级模型
    
    class Config:
        case_sensitive = True
        env_file = ".env"


settings = Settings()
