import os
import sys

# 禁用遥测功能
os.environ['POSTHOG_DISABLED'] = 'true'
os.environ['DISABLE_POSTHOG'] = 'true'
os.environ['DO_NOT_TRACK'] = '1'

# 添加情感状态机工具箱到Python路径
sys.path.append(os.path.join(os.path.dirname(__file__), 'emotion_state_serv'))

class Config:
    """配置类"""
    # Ollama模型配置
    OLLAMA_MODEL = "deepseek-r1:8b"
    OLLAMA_URL = "http://127.0.0.1:11434/api/generate"
    
    # 硅基流动API配置
    SILICONFLOW_API_KEY = os.getenv("SILICONFLOW_API_KEY", "")  # 环境变量获取API密钥
    SILICONFLOW_BASE_URL = "https://api.siliconflow.cn/v1/chat/completions"
    SILICONFLOW_MODEL = "Qwen/QwQ-32B"  # 默认使用Qwen/QwQ-32B模型
    SILICONFLOW_MAX_TOKENS = 4096
    SILICONFLOW_TEMPERATURE = 0.7
    SILICONFLOW_TOP_P = 0.7
    SILICONFLOW_TOP_K = 50
    SILICONFLOW_FREQUENCY_PENALTY = 0.5
    
    # 记忆配置
    MEMORY_EXPIRY_TIME = 30 * 24 * 60 * 60  # 30天
    RELEVANT_MEMORIES_COUNT = 3  # 检索相关记忆数量
    
    # 分层记忆配置
    MEMORY_RELEVANCE_THRESHOLD = 0.5  # 记忆相关性阈值
    PRIORITY_WEIGHTS = {
        "high": 0.9,
        "medium": 0.5,
        "low": 0.2
    }  # 优先级权重
    IMPORTANCE_WEIGHT = 0.3  # 重要性权重
    ACCESS_COUNT_WEIGHT = 0.2  # 访问频率权重
    STATE_RELEVANCE_WEIGHT = 0.2  # 状态相关性权重
    
    # 记忆类型配置
    MEMORY_TYPE_CONFIG = {
        "system_setting": {
            "expiry_time": float('inf'),
            "weight": 1.5
        },
        "user_profile": {
            "expiry_time": 365 * 24 * 60 * 60,
            "weight": 1.2
        },
        "fact": {
            "expiry_time": 180 * 24 * 60 * 60,
            "weight": 1.0
        },
        "preference": {
            "expiry_time": 90 * 24 * 60 * 60,
            "weight": 1.0
        },
        "conversation": {
            "expiry_time": 30 * 24 * 60 * 60,
            "weight": 0.9
        },
        "context": {
            "expiry_time": 7 * 24 * 60 * 60,
            "weight": 0.7
        }
    }  # 记忆类型配置
    
    # 情感配置
    SENTIMENT_ADJUSTMENT = {
        "positive": 1.0,
        "neutral": 1.0,
        "negative": 0.8
    }  # 情感调整系数
    
    # 记忆清理配置
    DEFAULT_CLEANUP_STATE = "idle"  # 默认清理状态
    
    # Flask应用配置
    FLASK_HOST = "0.0.0.0"
    FLASK_PORT = 9602
    SECRET_KEY = os.urandom(24)  # 用于会话管理
    
    # 模型配置
    BASE_DIR = os.path.dirname(os.path.abspath(__file__))
    MODELSCOPE_MODEL_ID = "Xorbits/bge-small-zh-v1.5"
    LOCAL_MODEL_PATH = os.path.join(BASE_DIR, 'models', 'bge-small-zh-v1.5', 'ai-modelscope', 'bge-small-zh-v1___5')
    FALLBACK_MODEL = None
    
    # 情感状态机配置
    EMOTION_STATE_MODULE = "emo_serv"
    CHARACTER_CARD_MODULE = "character_card"
    
    # 数据库配置
    DB_PATH = os.path.join(BASE_DIR, 'data.db')  # SQLite数据库路径
    DATABASE_URL = f'sqlite:///{DB_PATH}'
    
    # Chroma配置
    CHROMA_PERSIST_DIRECTORY = os.path.join(BASE_DIR, 'chroma_db')  # Chroma持久化目录
    
    # Redis配置（可选）
    REDIS_URL = None  # 如果使用Redis，设置为redis://localhost:6379/0

    # SMTP服务器配置（以Gmail为例）
    SMTP_SERVER = 'smtp.qq.com'
    SMTP_PORT = '587'

    # 邮箱账号配置
    SMTP_USERNAME = 'lemonadeandriceroll@foxmail.com'
    SMTP_PASSWORD = 'oaymoeecyoptbcea'
    FROM_EMAIL = 'lemonadeandriceroll@foxmail.com'