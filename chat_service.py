from flask import request, jsonify
import traceback
import threading
from config import Config
from database import (
    get_db, get_or_create_user, get_or_create_memory_collection,
    create_verification_code, verify_email_code, check_user_verified,
    get_user_by_email
)
from memory_manager import MemoryManager
from emo_serv import EmotionalStateMachine
from email_service import email_service

class ChatService:
    """聊天服务类"""
    
    def __init__(self, emotional_machine, memory_manager, ai_manager, prompt_generator, chroma_client):
        self.emotional_machine = emotional_machine
        self.memory_manager = memory_manager
        self.ai_manager = ai_manager
        self.prompt_generator = prompt_generator
        self.chroma_client = chroma_client
    
    def register_routes(self, app):
        """注册路由"""
        # 直接在应用上注册路由，不使用蓝图
        @app.route("/chat", methods=["POST"])
        def chat():
            """
            处理聊天请求
            """
            return self._handle_chat_request()
        
        @app.route("/mcp/chat", methods=["POST"])
        def mcp_chat():
            """
            MCP协议兼容的聊天接口
            """
            return self._handle_mcp_chat_request()
        
        @app.route("/health", methods=["GET"])
        def health_check():
            """
            健康检查接口
            """
            return self._health_check()
        
        @app.route("/memory/clear", methods=["POST"])
        def clear_memory():
            """
            清空特定用户的所有记忆
            """
            return self._handle_clear_memory_request()
        
        @app.route("/chat/initial", methods=["POST"])
        def initial_message():
            """
            生成首次对话的开场白
            """
            return self._handle_initial_message_request()
        
        @app.route("/chat/history", methods=["GET"])
        def get_chat_history():
            """
            获取特定用户的聊天记录
            """
            return self._handle_get_chat_history_request()
        
        @app.route("/chat/history/clear", methods=["POST"])
        def clear_chat_history():
            """
            清空特定用户的所有聊天记录
            """
            return self._handle_clear_chat_history_request()
        
        @app.route("/auth/send-verification", methods=["POST"])
        def send_verification():
            """
            发送邮箱验证码
            """
            return self._handle_send_verification_request()
        
        @app.route("/auth/verify", methods=["POST"])
        def verify_email():
            """
            验证邮箱验证码
            """
            return self._handle_verify_email_request()
    
    def _handle_user_identity(self, data):
        """处理用户身份，获取或创建用户及其记忆集合"""
        # 获取用户邮箱
        email = data.get("email", "default@example.com")
        
        # 获取数据库会话
        db_gen = get_db()
        db = next(db_gen)
        
        try:
            # 检查用户是否已验证
            if not check_user_verified(db, email):
                return None, None, "邮箱未验证，请先验证邮箱"
            
            # 获取或创建用户
            user = get_or_create_user(db, email)
            print(f"用户: {user.email}, ID: {user.id}")
            
            # 获取或创建用户的记忆集合
            memory_collection = get_or_create_memory_collection(db, user.id, user.email)
            print(f"记忆集合: {memory_collection.collection_name}")
            
            return user.id, memory_collection.collection_name, None
        finally:
            # 关闭数据库会话
            next(db_gen, None)
    
    def _handle_chat_request(self):
        """处理聊天请求的内部方法"""
        try:
            data = request.get_json()
            user_msg = data.get("message", "")
            
            if not user_msg:
                return jsonify({"error": "缺少message参数"}), 400
            
            # 处理用户身份，获取或创建用户及其记忆集合
            user_id, collection_name, error = self._handle_user_identity(data)
            if error:
                return jsonify({"error": error, "need_verification": True}), 401
            
            # 创建临时情感状态机实例，避免共享状态
            emotional_machine = EmotionalStateMachine(user_id)
            db_gen = get_db()
            db = next(db_gen)
            try:
                emotional_machine.load_from_db(db)
            finally:
                next(db_gen, None)
            
            # 更新情感状态（统一通过工具调用）
            tool_res = self.ai_manager.execute_tool_call({
                "name": "emotion_state_machine",
                "arguments": {"message": user_msg, "state": emotional_machine.current_state}
            })
            new_state = tool_res.get("new_state", emotional_machine.current_state)
            emotional_machine.current_state = new_state
            if isinstance(tool_res, dict) and tool_res.get("variables"):
                emotional_machine.variables = tool_res["variables"]
            
            # 保存更新后的情感状态
            db_gen = get_db()
            db = next(db_gen)
            try:
                emotional_machine.save_to_db(db)
            finally:
                next(db_gen, None)
            
            # 保存当前记忆管理器的集合，以便后续恢复
            original_collection = self.memory_manager.collection_name
            try:
                # 设置当前用户的记忆集合
                self.memory_manager.set_collection_by_name(collection_name)
                
                prompt = self.prompt_generator.generate_smart_chat_prompt(user_msg, new_state)
                include_thinking = bool(data.get("include_thinking", False))
                
                # 一次调用获取响应和思考过程，避免两次API请求
                ai_result = self.ai_manager.get_ai_response(prompt, think=include_thinking)
                final_text = ai_result["response"]
                thinking_text = ai_result["thinking"] if include_thinking else None
                
                print(f"AI 回复: {final_text}")
                # 确保final_text始终是字符串，避免将GenerateResponse对象传递给add_memory
                if not isinstance(final_text, str):
                    final_text = str(final_text)
                
                # 异步执行聊天记忆总结和保存
                def async_memory_summary():
                    try:
                        summary = self.ai_manager.summarize_conversation(user_msg, final_text, new_state, async_mode=False)
                        # 创建临时记忆管理器实例，避免共享状态
                        temp_memory_manager = MemoryManager(self.chroma_client, self.ai_manager.embedding_model)
                        temp_memory_manager.set_collection_by_name(collection_name)
                        # 使用智能重要性评分，不手动指定importance
                        temp_memory_manager.add_memory(user_msg, summary, new_state)
                        
                        # 启动异步记忆优化
                        temp_memory_manager.async_memory_optimization(user_id)
                    except Exception as e:
                        print(f"异步记忆总结失败: {e}")
                        print(traceback.format_exc())
                
                # 使用线程异步执行，不阻塞响应返回
                threading.Thread(target=async_memory_summary, daemon=True).start()
            finally:
                # 恢复原始记忆集合
                if original_collection:
                    self.memory_manager.set_collection_by_name(original_collection)
                else:
                    # 如果原来没有设置集合，清除当前集合
                    self.memory_manager.collection_name = None
                    self.memory_manager.collection = None
            
            # 保存聊天记录
            db_gen = get_db()
            db = next(db_gen)
            try:
                from database import create_chat_history
                create_chat_history(db, user_id, user_msg, final_text, new_state)
            finally:
                next(db_gen, None)
            
            resp_payload = {
                "response": final_text,
                "current_state": new_state,
                "state_description": emotional_machine.get_state_description(new_state),
                "emotional_variables": emotional_machine.variables
            }
            if thinking_text:
                resp_payload["thinking"] = thinking_text
            return jsonify(resp_payload)
            
        except Exception as e:
            print(f"聊天服务错误: {e}")
            print(traceback.format_exc())
            return jsonify({"error": f"服务器内部错误: {str(e)}"}), 500
    
    def _handle_mcp_chat_request(self):
        """处理MCP聊天请求的内部方法"""
        try:
            data = request.get_json()
            
            if not data or "method" not in data:
                return jsonify({
                    "jsonrpc": "2.0",
                    "error": {"code": -32700, "message": "Invalid JSON-RPC request"},
                    "id": None
                }), 400
            
            method = data["method"]
            params = data.get("params", {})
            request_id = data.get("id")
            
            if method == "chat":
                user_msg = params.get("message", "")
                include_thinking = bool(params.get("include_thinking", False))
                
                if not user_msg:
                    return jsonify({
                        "jsonrpc": "2.0",
                        "error": {"code": -32602, "message": "缺少message参数"},
                        "id": request_id
                    }), 400
                
                # 处理用户身份，获取或创建用户及其记忆集合
                user_id, collection_name, error = self._handle_user_identity(params)
                if error:
                    return jsonify({
                        "jsonrpc": "2.0",
                        "error": {"code": -32001, "message": error, "need_verification": True},
                        "id": request_id
                    }), 401
                
                # 创建临时情感状态机实例，避免共享状态
                emotional_machine = EmotionalStateMachine(user_id)
                db_gen = get_db()
                db = next(db_gen)
                try:
                    emotional_machine.load_from_db(db)
                finally:
                    next(db_gen, None)
                
                # 更新情感状态（统一通过工具调用）
                tool_res = self.ai_manager.execute_tool_call({
                    "name": "emotion_state_machine",
                    "arguments": {"message": user_msg, "state": emotional_machine.current_state}
                })
                new_state = tool_res.get("new_state", emotional_machine.current_state)
                emotional_machine.current_state = new_state
                if isinstance(tool_res, dict) and tool_res.get("variables"):
                    emotional_machine.variables = tool_res["variables"]
                
                # 保存更新后的情感状态
                db_gen = get_db()
                db = next(db_gen)
                try:
                    emotional_machine.save_to_db(db)
                finally:
                    next(db_gen, None)
                
                # 保存当前记忆管理器的集合，以便后续恢复
                original_collection = self.memory_manager.collection_name
                try:
                    # 设置当前用户的记忆集合
                    self.memory_manager.set_collection_by_name(collection_name)
                    
                    # 使用智能记忆检索生成提示
                    prompt = self.prompt_generator.generate_smart_chat_prompt(user_msg, new_state)
                    
                    # 调用 AI 获取响应，支持工具调用
                    ai_response = self.ai_manager.get_ai_response_with_tools(prompt, think=include_thinking)
                    
                    final_response = ai_response.get("response", "")
                    thinking_text = ai_response.get("thinking")
                    
                    # 检查是否有工具调用
                    if "tool_calls" in ai_response and ai_response["tool_calls"]:
                        tool_calls = ai_response["tool_calls"]
                        tool_results = []
                        
                        # 执行所有工具调用
                        for tool_call in tool_calls:
                            tool_name = tool_call["name"]
                            arguments = tool_call["arguments"]
                            
                            # 执行工具调用
                            result = self.ai_manager.execute_tool_call({
                                "name": tool_name,
                                "arguments": arguments
                            })
                            
                            tool_results.append({
                                "tool_call_id": tool_call.get("id", ""),
                                "result": result
                            })
                        
                        # 如果有工具调用结果，再次调用模型获取最终回复
                        if tool_results:
                            # 构建带有工具结果的提示
                            tool_result_prompt = f"{prompt}\n\n"
                            for tool_result in tool_results:
                                tool_result_prompt += f"工具调用结果: {json.dumps(tool_result['result'])}\n"
                            
                            # 调用模型获取最终回复
                            final_response_data = self.ai_manager.get_ai_response(tool_result_prompt)
                            final_response = final_response_data["response"]
                finally:
                    # 恢复原始记忆集合
                    if original_collection:
                        self.memory_manager.set_collection_by_name(original_collection)
                    else:
                        # 如果原来没有设置集合，清除当前集合
                        self.memory_manager.collection_name = None
                        self.memory_manager.collection = None
                
                # 异步执行聊天记忆总结和保存
                def async_memory_summary():
                    try:
                        summary = self.ai_manager.summarize_conversation(user_msg, final_response, new_state, async_mode=False)
                        # 创建临时记忆管理器实例，避免共享状态
                        temp_memory_manager = MemoryManager(self.chroma_client, self.ai_manager.embedding_model)
                        temp_memory_manager.set_collection_by_name(collection_name)
                        # 使用智能重要性评分，不手动指定importance
                        temp_memory_manager.add_memory(user_msg, summary, new_state)
                        
                        # 启动异步记忆优化
                        temp_memory_manager.async_memory_optimization(user_id)
                    except Exception as e:
                        print(f"异步记忆总结失败: {e}")
                        print(traceback.format_exc())
                
                # 使用线程异步执行，不阻塞响应返回
                threading.Thread(target=async_memory_summary, daemon=True).start()
                
                # 存储聊天记录到数据库
                db_gen = get_db()
                db = next(db_gen)
                try:
                    from database import create_chat_history
                    create_chat_history(db, user_id, user_msg, final_response, new_state)
                finally:
                    next(db_gen, None)
                
                return jsonify({
                    "jsonrpc": "2.0",
                    "result": {
                        "response": final_response,
                        "thinking": thinking_text,
                        "state": new_state,
                        "state_description": emotional_machine.get_state_description(new_state),
                        "variables": emotional_machine.variables
                    },
                    "id": request_id
                })
            
            else:
                return jsonify({
                    "jsonrpc": "2.0",
                    "error": {"code": -32601, "message": f"Method not found: {method}"},
                    "id": request_id
                }), 404
                
        except Exception as e:
            print(f"MCP聊天服务错误: {e}")
            print(traceback.format_exc())
            return jsonify({
                "jsonrpc": "2.0",
                "error": {"code": -32603, "message": f"Internal error: {str(e)}"},
                "id": None
            }), 500
    
    def _handle_initial_message_request(self):
        try:
            data = request.get_json()
            user_id, collection_name, error = self._handle_user_identity(data)
            if error:
                return jsonify({"error": error, "need_verification": True}), 401
            
            # 创建临时情感状态机实例，避免共享状态
            emotional_machine = EmotionalStateMachine(user_id)
            db_gen = get_db()
            db = next(db_gen)
            try:
                emotional_machine.load_from_db(db)
            finally:
                next(db_gen, None)
            
            # 保存当前记忆管理器的集合，以便后续恢复
            original_collection = self.memory_manager.collection_name
            try:
                # 设置当前用户的记忆集合
                self.memory_manager.set_collection_by_name(collection_name)
                
                if self.memory_manager.has_any_memory():
                    return jsonify({"status": "skipped", "message": "已有历史记忆，不再生成开场白"})
                state = emotional_machine.current_state
                prompt = self.prompt_generator.generate_initial_prompt(state)
                result = self.ai_manager.get_ai_response(prompt)
                final_text = result["response"]
                self.memory_manager.add_memory("[INIT]", final_text, state, memory_type="conversation", category="system")
            finally:
                # 恢复原始记忆集合
                if original_collection:
                    self.memory_manager.set_collection_by_name(original_collection)
                else:
                    # 如果原来没有设置集合，清除当前集合
                    self.memory_manager.collection_name = None
                    self.memory_manager.collection = None
            
            # 保存聊天记录
            db_gen = get_db()
            db = next(db_gen)
            try:
                from database import create_chat_history
                create_chat_history(db, user_id, "[INIT]", final_text, state)
            finally:
                next(db_gen, None)
            
            return jsonify({"status": "success", "response": final_text, "current_state": state, "state_description": emotional_machine.get_state_description(state), "emotional_variables": emotional_machine.variables})
        except Exception as e:
            print(f"生成开场白服务错误: {e}")
            print(traceback.format_exc())
            return jsonify({"error": f"服务器内部错误: {str(e)}"}), 500

    def _health_check(self):
        """健康检查"""
        return jsonify({"status": "ok", "service": "Ollama Chat Service with Emotion State Machine"})
    
    def _handle_clear_memory_request(self):
        """处理清空记忆请求的内部方法"""
        try:
            data = request.get_json()
            
            email = data.get("email", "default@example.com")
            user_id, collection_name, error = self._handle_user_identity(data)
            if error:
                return jsonify({"error": error, "need_verification": True}), 401
            
            # 保存当前记忆管理器的集合，以便后续恢复
            original_collection = self.memory_manager.collection_name
            try:
                # 设置当前用户的记忆集合
                self.memory_manager.set_collection_by_name(collection_name)
                
                self.memory_manager.clear_all_memories()
                
                # 创建临时情感状态机实例，避免共享状态
                emotional_machine = EmotionalStateMachine(user_id)
                db_gen = get_db()
                db = next(db_gen)
                try:
                    emotional_machine.load_from_db(db)
                finally:
                    next(db_gen, None)
                state = emotional_machine.current_state
                prompt = self.prompt_generator.generate_initial_prompt(state)
                result = self.ai_manager.get_ai_response(prompt)
                initial_text = result["response"]
                self.memory_manager.add_memory("[INIT]", initial_text, state, memory_type="conversation", category="system")
            finally:
                # 恢复原始记忆集合
                if original_collection:
                    self.memory_manager.set_collection_by_name(original_collection)
                else:
                    # 如果原来没有设置集合，清除当前集合
                    self.memory_manager.collection_name = None
                    self.memory_manager.collection = None
            
            # 保存聊天记录
            db_gen = get_db()
            db = next(db_gen)
            try:
                from database import create_chat_history
                create_chat_history(db, user_id, "[INIT]", initial_text, state)
            finally:
                next(db_gen, None)
            
            return jsonify({
                "status": "success",
                "message": f"用户 {email} 的记忆已成功清空",
                "collection_name": collection_name,
                "initial_message": initial_text,
                "current_state": state,
                "state_description": emotional_machine.get_state_description(state),
                "emotional_variables": emotional_machine.variables
            })
            
        except Exception as e:
            print(f"清空记忆服务错误: {e}")
            print(traceback.format_exc())
            return jsonify({"error": f"服务器内部错误: {str(e)}"}), 500
    
    def _handle_get_chat_history_request(self):
        """处理获取聊天记录请求的内部方法"""
        try:
            # 获取用户邮箱
            email = request.args.get("email", "default@example.com")
            
            # 获取数据库会话
            db_gen = get_db()
            db = next(db_gen)
            
            try:
                # 获取或创建用户
                from database import get_user_by_email, get_chat_histories_by_user
                user = get_user_by_email(db, email)
                
                if not user:
                    return jsonify({"status": "success", "chat_history": []})
                
                # 获取用户聊天记录
                chat_histories = get_chat_histories_by_user(db, user.id)
                
                # 转换为前端可用的格式
                chat_history_list = []
                for chat in chat_histories:
                    chat_history_list.append({
                        "id": chat.id,
                        "user_message": chat.user_message,
                        "assistant_message": chat.assistant_message,
                        "state": chat.state,
                        "created_at": chat.created_at.isoformat()
                    })
                
                return jsonify({
                    "status": "success",
                    "chat_history": chat_history_list,
                    "user_email": user.email
                })
            finally:
                next(db_gen, None)
            
        except Exception as e:
            print(f"获取聊天记录服务错误: {e}")
            print(traceback.format_exc())
            return jsonify({"error": f"服务器内部错误: {str(e)}"}), 500
    
    def _handle_clear_chat_history_request(self):
        """处理清空聊天记录请求的内部方法"""
        try:
            data = request.get_json()
            
            email = data.get("email", "default@example.com") # 获取email用于消息显示
            # 处理用户身份，获取或创建用户及其记忆集合
            user_id, _, error = self._handle_user_identity(data)
            if error:
                return jsonify({"error": error, "need_verification": True}), 401
            
            # 获取数据库会话
            db_gen = get_db()
            db = next(db_gen)
            
            try:
                # 清空该用户的所有聊天记录
                from database import clear_chat_histories_by_user
                deleted_count = clear_chat_histories_by_user(db, user_id)
                
                return jsonify({
                    "status": "success",
                    "message": f"用户 {email} 的聊天记录已成功清空",
                    "deleted_count": deleted_count
                })
            finally:
                next(db_gen, None)
            
        except Exception as e:
            print(f"清空聊天记录服务错误: {e}")
            print(traceback.format_exc())
            return jsonify({"error": f"服务器内部错误: {str(e)}"}), 500
    
    def _handle_send_verification_request(self):
        """处理发送验证码请求的内部方法"""
        try:
            data = request.get_json()
            email = data.get("email", "").strip()
            
            if not email:
                return jsonify({"error": "邮箱不能为空"}), 400
            
            # 获取数据库会话
            db_gen = get_db()
            db = next(db_gen)
            
            try:
                # 创建验证码
                user, error = create_verification_code(db, email)
                if error:
                    return jsonify({"error": error}), 400
                
                # 发送邮件
                success, message = email_service.send_verification_code(email, user.verification_code)
                if not success:
                    return jsonify({"error": message}), 500
                
                return jsonify({
                    "success": True,
                    "message": "验证码发送成功",
                    "email": email
                })
                
            finally:
                next(db_gen, None)
                
        except Exception as e:
            print(f"发送验证码服务错误: {e}")
            print(traceback.format_exc())
            return jsonify({"error": f"服务器内部错误: {str(e)}"}), 500
    
    def _handle_verify_email_request(self):
        """处理验证邮箱请求的内部方法"""
        try:
            data = request.get_json()
            email = data.get("email", "").strip()
            code = data.get("code", "").strip()
            
            if not email or not code:
                return jsonify({"error": "邮箱和验证码不能为空"}), 400
            
            # 获取数据库会话
            db_gen = get_db()
            db = next(db_gen)
            
            try:
                # 验证邮箱验证码
                success, message = verify_email_code(db, email, code)
                
                if success:
                    return jsonify({
                        "success": True,
                        "message": message,
                        "email": email
                    })
                else:
                    return jsonify({"error": message}), 400
                    
            finally:
                next(db_gen, None)
                
        except Exception as e:
            print(f"验证邮箱服务错误: {e}")
            print(traceback.format_exc())
            return jsonify({"error": f"服务器内部错误: {str(e)}"}), 500
