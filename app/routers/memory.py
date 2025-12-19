from flask import Blueprint, request, jsonify

memory_bp = Blueprint('memory', __name__)

@memory_bp.route('/memory/clear', methods=['POST'])
def clear_memory():
    """
    清空特定用户的所有记忆
    """
    from app.main import get_chat_service
    chat_service = get_chat_service()
    return chat_service._handle_clear_memory_request()