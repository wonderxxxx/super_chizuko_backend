from flask import Flask
from flask_cors import CORS
from waitress import serve
import chromadb
import os
import sys

# 确保能正确导入情感状态机
if not os.path.abspath(os.path.join(os.path.dirname(os.path.dirname(__file__)), 'emotion_state_serv')) in sys.path:
    sys.path.append(os.path.abspath(os.path.join(os.path.dirname(os.path.dirname(__file__)), 'emotion_state_serv')))

from config.settings import Config
from core.memory.manager import MemoryManager
from core.ai.manager import AIManager
from prompt_generator import PromptGenerator
from core.chat.service import ChatService
from emo_serv import EmotionalStateMachine
from database import init_db

# 初始化数据库
init_db()

# 全局服务实例
_chat_service = None

def create_app():
    """创建Flask应用"""
    app = Flask(__name__)
    app.config.from_object(Config)
    
    # 启用CORS支持
    CORS(app, resources={"/*": {"origins": "*"}})
    
    # 确保Chroma持久化目录存在
    os.makedirs(Config.CHROMA_PERSIST_DIRECTORY, exist_ok=True)
    
    # 初始化向量数据库（持久化存储）
    chroma_client = chromadb.PersistentClient(path=Config.CHROMA_PERSIST_DIRECTORY)
    
    # 初始化各个组件
    emotional_machine = EmotionalStateMachine()
    ai_manager = AIManager()
    memory_manager = MemoryManager(chroma_client, ai_manager.embedding_model)
    prompt_generator = PromptGenerator(emotional_machine, memory_manager)
    
    # 初始化聊天服务
    global _chat_service
    _chat_service = ChatService(emotional_machine, memory_manager, ai_manager, prompt_generator, chroma_client)
    
    # 注册蓝图路由
    from app.routers.health import health_bp
    from app.routers.chat import chat_bp
    from app.routers.memory import memory_bp
    
    app.register_blueprint(health_bp)
    app.register_blueprint(chat_bp)
    app.register_blueprint(memory_bp)
    
    return app

def get_chat_service():
    """获取聊天服务实例"""
    return _chat_service

def main(app=None):
    """启动应用的主函数"""
    if app is None:
        app = create_app()
    
    # 启动服务
    print(f"聊天服务已启动，端口 {Config.FLASK_PORT}")
    print("支持的接口:")
    print("  - POST /chat: 简单聊天接口")
    print("  - GET /health: 健康检查")
    print(f"  - 使用模型: {Config.SILICONFLOW_MODEL}")
    print("  - 情感状态机已集成")
    print("  - 用户机制已集成，支持独立记忆")
    
    # 使用waitress启动服务器
    serve(app, host=Config.FLASK_HOST, port=Config.FLASK_PORT)

if __name__ == "__main__":
    # 创建应用实例
    app = create_app()
    main(app)