from flask import Flask, g
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
    
    # 初始化全局共享组件
    ai_manager = AIManager()
    
    # 将共享组件存储在app配置中
    app.config['CHROMA_CLIENT'] = chroma_client
    app.config['AI_MANAGER'] = ai_manager
    
    # 注册蓝图路由
    from app.routers.health import health_bp
    from app.routers.chat import chat_bp
    from app.routers.memory import memory_bp
    
    app.register_blueprint(health_bp)
    app.register_blueprint(chat_bp)
    app.register_blueprint(memory_bp)
    
    return app

def get_chat_service():
    """获取聊天服务实例，为每个请求创建独立实例"""
    from flask import current_app
    
    # 从当前应用配置中获取共享组件
    chroma_client = current_app.config['CHROMA_CLIENT']
    ai_manager = current_app.config['AI_MANAGER']
    
    # 为每个请求创建独立的组件实例
    emotional_machine = EmotionalStateMachine()
    memory_manager = MemoryManager(chroma_client, ai_manager.embedding_model)
    prompt_generator = PromptGenerator(emotional_machine, memory_manager)
    
    # 创建独立的聊天服务实例
    chat_service = ChatService(emotional_machine, memory_manager, ai_manager, prompt_generator, chroma_client)
    
    return chat_service

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