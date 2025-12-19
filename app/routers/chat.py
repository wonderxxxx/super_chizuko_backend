from flask import Blueprint, request, jsonify

chat_bp = Blueprint('chat', __name__)

# 这里需要在app/main.py中注册服务实例，然后通过app上下文访问
# 暂时保留路由结构，后续会通过依赖注入或其他方式获取服务实例
@chat_bp.route('/chat', methods=['POST'])
def chat():
    """
    处理聊天请求
    """
    # 后续会通过依赖注入获取chat_service实例
    from app.main import get_chat_service
    chat_service = get_chat_service()
    return chat_service._handle_chat_request()

@chat_bp.route('/chat/initial', methods=['POST'])
def initial_message():
    """
    生成首次对话的开场白
    """
    from app.main import get_chat_service
    chat_service = get_chat_service()
    return chat_service._handle_initial_message_request()

@chat_bp.route('/chat/history', methods=['GET'])
def get_chat_history():
    """
    获取特定用户的聊天记录
    """
    from app.main import get_chat_service
    chat_service = get_chat_service()
    return chat_service._handle_get_chat_history_request()

@chat_bp.route('/chat/history/clear', methods=['POST'])
def clear_chat_history():
    """
    清空特定用户的所有聊天记录
    """
    from app.main import get_chat_service
    chat_service = get_chat_service()
    return chat_service._handle_clear_chat_history_request()

@chat_bp.route('/auth/send-verification', methods=['POST'])
def send_verification():
    """
    发送邮箱验证码
    """
    from app.main import get_chat_service
    chat_service = get_chat_service()
    return chat_service._handle_send_verification_request()

@chat_bp.route('/auth/verify', methods=['POST'])
def verify_email():
    """
    验证邮箱验证码
    """
    from app.main import get_chat_service
    chat_service = get_chat_service()
    return chat_service._handle_verify_email_request()