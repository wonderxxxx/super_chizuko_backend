import os
import ollama
import traceback
import concurrent.futures
from sentence_transformers import SentenceTransformer
from config import Config
import json
from typing import Dict, List, Any
import logging
import time
from siliconflow_client import SiliconFlowClient

# 配置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class AIManager:
    """AI模型管理器"""
    
    def __init__(self):
        self.ollama_model = Config.OLLAMA_MODEL
        self.embedding_model = self._load_embedding_model()
        self.tools = {}
        self._register_default_tools()
        # 创建线程池用于异步执行记忆总结
        self.executor = concurrent.futures.ThreadPoolExecutor(max_workers=2)
        
        # 初始化硅基流动客户端
        self.siliconflow_client = None
        try:
            if Config.SILICONFLOW_API_KEY:
                self.siliconflow_client = SiliconFlowClient()
                logger.info("硅基流动API客户端初始化成功")
            else:
                logger.info("硅基流动API密钥未配置，将使用本地Ollama")
        except Exception as e:
            logger.error(f"硅基流动API客户端初始化失败: {e}")
            self.siliconflow_client = None
    
    def _register_default_tools(self):
        """注册默认工具"""
        from tools.currentTimeTool import CurrentTimeTool
        current_time_tool = CurrentTimeTool()
        self.register_tool("getCurrentTime", current_time_tool.getCurrentTime, "为了感知当前时间，你可以调用这个工具")

        from emo_serv import EmotionalStateMachine, generate_reply
        def emotion_tool(message: str, state: str = None):
            esm = EmotionalStateMachine()
            if state:
                esm.current_state = state
            new_state = esm.determine_state(message)
            reply = generate_reply(new_state, message, esm)
            return {
                "reply": reply,
                "new_state": new_state,
                "state_description": esm.get_state_description(new_state),
                "variables": esm.variables
            }
        self.register_tool("emotion_state_machine", emotion_tool, "根据消息检测情感状态并生成符合人格的回复")
    
    def register_tool(self, name: str, func: callable, description: str):
        """注册工具"""
        self.tools[name] = {
            "func": func,
            "description": description
        }
    
    def _load_embedding_model(self):
        """加载嵌入模型"""
        start_time = time.time()
        try:
            # 自动检测可用设备
            import torch
            device = "cuda" if torch.cuda.is_available() else "cpu"
            logger.info(f"开始加载嵌入模型，使用设备: {device}")
            
            # 首先尝试使用本地模型路径
            if os.path.exists(Config.LOCAL_MODEL_PATH):
                embedding_model = SentenceTransformer(Config.LOCAL_MODEL_PATH, device=device)
                end_time = time.time()
                logger.info(f"成功加载本地嵌入模型: {Config.LOCAL_MODEL_PATH}，设备: {device}，耗时: {end_time - start_time:.2f} 秒")
            else:
                try:
                    from modelscope.hub.snapshot_download import snapshot_download
                    models_dir = os.path.join(Config.BASE_DIR, 'models')
                    logger.info(f"本地模型不存在，尝试从ModelScope下载模型")
                    download_start = time.time()
                    local_dir = snapshot_download(
                        model_id=getattr(Config, 'MODELSCOPE_MODEL_ID', 'Xorbits/bge-small-zh-v1.5'),
                        cache_dir=models_dir,
                        local_files_only=False
                    )
                    download_end = time.time()
                    logger.info(f"成功从ModelScope下载模型: {local_dir}，下载耗时: {download_end - download_start:.2f} 秒")
                    
                    load_start = time.time()
                    embedding_model = SentenceTransformer(local_dir, device=device)
                    end_time = time.time()
                    logger.info(f"成功加载ModelScope嵌入模型: {local_dir}，设备: {device}，加载耗时: {end_time - load_start:.2f} 秒，总耗时: {end_time - start_time:.2f} 秒")
                except Exception as _e:
                    end_time = time.time()
                    logger.error(f"从ModelScope下载模型失败 {_e}，耗时: {end_time - start_time:.2f} 秒")
                    raise _e
            return embedding_model
        except Exception as e:
            end_time = time.time()
            logger.error(f"模型加载失败 {e}, 使用简化的向量化方案，耗时: {end_time - start_time:.2f} 秒")
            logger.debug(traceback.format_exc())
            # 降级方案：使用简单的关键词匹配
            return None
    
    def get_ai_response(self, prompt, think=False, raw=False, use_siliconflow=None):
        """
        获取AI模型响应，支持选择使用硅基流动API或本地Ollama
        
        Args:
            prompt: 输入提示
            think: 是否返回推理过程
            raw: 是否返回原始响应
            use_siliconflow: 是否使用硅基流动API，None表示自动选择
            
        Returns:
            包含响应和思考过程的字典
        """
        start_time = time.time()
        
        # 决定使用哪种API
        if use_siliconflow is None:
            # 自动选择：优先使用硅基流动API
            use_siliconflow = self.siliconflow_client is not None
        
        if use_siliconflow and self.siliconflow_client:
            return self._get_siliconflow_response(prompt, think, raw, start_time)
        else:
            return self._get_ollama_response(prompt, think, raw, start_time)
    
    def _get_siliconflow_response(self, prompt, think, raw, start_time):
        """使用硅基流动API获取响应"""
        try:
            logger.info(f"开始调用硅基流动API ({Config.SILICONFLOW_MODEL})，think={think}, raw={raw}")
            response = self.siliconflow_client.simple_chat(
                prompt=prompt,
                think=think,
                raw=raw,
                temperature=Config.SILICONFLOW_TEMPERATURE,
                top_p=Config.SILICONFLOW_TOP_P,
                frequency_penalty=Config.SILICONFLOW_FREQUENCY_PENALTY
            )
            
            if raw:
                end_time = time.time()
                logger.info(f"硅基流动API调用完成，耗时: {end_time - start_time:.2f} 秒")
                return response
            
            end_time = time.time()
            logger.info(f"硅基流动API调用完成，响应长度: {len(response.get('response', ''))} 字符，耗时: {end_time - start_time:.2f} 秒")
            return response
            
        except Exception as e:
            end_time = time.time()
            logger.error(f"硅基流动API调用失败: {e}，耗时: {end_time - start_time:.2f} 秒，回退到本地Ollama")
            logger.debug(traceback.format_exc())
            # 回退到本地Ollama
            return self._get_ollama_response(prompt, think, raw, start_time)
    
    def _get_ollama_response(self, prompt, think, raw, start_time):
        """使用本地Ollama获取响应"""
        try:
            logger.info(f"开始调用本地Ollama模型 ({self.ollama_model})，think={think}, raw={raw}")
            response = ollama.generate(
                model=self.ollama_model,
                prompt=prompt,
                think=think,
                stream=False,
                options={"temperature": 0.6, "top_p": 0.9, "gpu_layers": 999, "num_thread": 12, "n_ctx": 4096}
            )
            
            if raw:
                end_time = time.time()
                logger.info(f"本地Ollama模型调用完成，耗时: {end_time - start_time:.2f} 秒")
                return response
            
            ollama_response = response.get("response", "")
            # 只清理多余的换行和空格，不再截断响应长度
            cleaned_response = ollama_response.replace('\n', '').replace('\r', '').replace('  ', ' ').strip()
            
            # 一次调用获取响应和思考过程，返回包含两者的字典
            result = {
                "response": cleaned_response,
                "thinking": response.get("thinking")
            }
            
            end_time = time.time()
            logger.info(f"本地Ollama模型调用完成，响应长度: {len(cleaned_response)} 字符，耗时: {end_time - start_time:.2f} 秒")
            return result
        except Exception as e:
            end_time = time.time()
            logger.error(f"本地Ollama调用失败: {e}，耗时: {end_time - start_time:.2f} 秒")
            logger.debug(traceback.format_exc())
            # 返回包含默认值的字典，确保调用者能正常处理
            return {
                "response": "抱歉，我现在有点忙，稍后再聊吧～",
                "thinking": None
            }
    
    def get_ollama_response(self, prompt, think=False, raw=False):
        """保持向后兼容性的方法，调用新的get_ai_response方法"""
        return self.get_ai_response(prompt, think, raw, use_siliconflow=False)
    
    def get_ai_response_with_tools(self, prompt, think=False, use_siliconflow=None):
        """
        获取AI模型响应（支持工具调用），可选择使用硅基流动API或本地Ollama
        
        Args:
            prompt: 输入提示
            think: 是否返回推理过程
            use_siliconflow: 是否使用硅基流动API，None表示自动选择
            
        Returns:
            包含响应、思考和工具调用的字典
        """
        start_time = time.time()
        
        # 决定使用哪种API
        if use_siliconflow is None:
            use_siliconflow = self.siliconflow_client is not None
        
        if use_siliconflow and self.siliconflow_client:
            return self._get_siliconflow_response_with_tools(prompt, think, start_time)
        else:
            return self._get_ollama_response_with_tools(prompt, think, start_time)
    
    def _get_siliconflow_response_with_tools(self, prompt, think, start_time):
        """使用硅基流动API获取带工具的响应"""
        try:
            logger.info(f"开始调用硅基流动API（带工具）({Config.SILICONFLOW_MODEL})，think={think}")
            
            # 转换工具格式为硅基流动API格式
            tools_for_siliconflow = []
            for tool_name, tool_info in self.tools.items():
                tools_for_siliconflow.append({
                    "type": "function",
                    "function": {
                        "name": tool_name,
                        "description": tool_info["description"],
                        "parameters": {},
                        "strict": False
                    }
                })
            
            response = self.siliconflow_client.chat_with_tools(
                prompt=prompt,
                tools=tools_for_siliconflow,
                think=think,
                temperature=Config.SILICONFLOW_TEMPERATURE,
                top_p=Config.SILICONFLOW_TOP_P,
                frequency_penalty=Config.SILICONFLOW_FREQUENCY_PENALTY
            )
            
            end_time = time.time()
            response_length = len(response.get("response", ""))
            tool_calls_count = len(response.get("tool_calls", []))
            logger.info(f"硅基流动API（带工具）调用完成，响应长度: {response_length} 字符，工具调用数: {tool_calls_count}，耗时: {end_time - start_time:.2f} 秒")
            return response
            
        except Exception as e:
            end_time = time.time()
            logger.error(f"硅基流动API（带工具）调用失败: {e}，耗时: {end_time - start_time:.2f} 秒，回退到本地Ollama")
            logger.debug(traceback.format_exc())
            # 回退到本地Ollama
            return self._get_ollama_response_with_tools(prompt, think, start_time)
    
    def _get_ollama_response_with_tools(self, prompt, think, start_time):
        """使用本地Ollama获取带工具的响应"""
        try:
            logger.info(f"开始调用本地Ollama模型（带工具）({self.ollama_model})，think={think}")
            response = ollama.generate(
                model=self.ollama_model,
                prompt=prompt,
                think=think,
                stream=False,
                options={"temperature": 0.6, "top_p": 0.9, "gpu_layers": 999, "num_thread": 12, "n_ctx": 4096}
            )
            # 过滤掉不需要的元数据，只保留必要的字段
            filtered_response = {
                "response": response.get("response", ""),
                "thinking": response.get("thinking"),
                "tool_calls": response.get("tool_calls", [])
            }
            
            end_time = time.time()
            response_length = len(filtered_response.get("response", ""))
            tool_calls_count = len(filtered_response.get("tool_calls", []))
            logger.info(f"本地Ollama模型（带工具）调用完成，响应长度: {response_length} 字符，工具调用数: {tool_calls_count}，耗时: {end_time - start_time:.2f} 秒")
            return filtered_response
        except Exception as e:
            end_time = time.time()
            logger.error(f"本地Ollama（带工具）调用失败: {e}，耗时: {end_time - start_time:.2f} 秒")
            logger.debug(traceback.format_exc())
            return {"response": "抱歉，我现在有点忙，稍后再聊吧～", "thinking": None, "tool_calls": []}
    
    def get_ollama_response_with_tools(self, prompt, think=False):
        """保持向后兼容性的方法，调用新的get_ai_response_with_tools方法"""
        return self.get_ai_response_with_tools(prompt, think, use_siliconflow=False)
    
    def execute_tool_call(self, tool_call):
        """执行工具调用"""
        start_time = time.time()
        tool_name = tool_call.get("name")
        arguments = tool_call.get("arguments", {})
        
        if tool_name not in self.tools:
            logger.error(f"工具 {tool_name} 不存在")
            return {"error": f"Tool {tool_name} not found"}
        
        try:
            # 执行工具函数
            logger.info(f"开始执行工具: {tool_name}")
            result = self.tools[tool_name]["func"]() if not arguments else self.tools[tool_name]["func"](**arguments)
            end_time = time.time()
            logger.info(f"工具 {tool_name} 执行完成，耗时: {end_time - start_time:.2f} 秒")
            return result
        except Exception as e:
            end_time = time.time()
            logger.error(f"工具 {tool_name} 执行失败: {e}，耗时: {end_time - start_time:.2f} 秒")
            logger.debug(traceback.format_exc())
            return {"error": str(e)}
    
    def _summarize_conversation_sync(self, user_msg, assistant_msg, current_state, use_siliconflow=None):
        """同步执行对话总结"""
        start_time = time.time()
        prompt = f"""
        请严格按照以下要求总结用户与智子的对话：
        
        用户: {user_msg}
        智子: {assistant_msg}
        当前情感状态: {current_state}
        
        要求：
        1. 必须输出有效的JSON格式内容，禁止任何其他文本
        2. summary字段必须非常简洁（最多50字）
        3. 所有情感相关字段必须准确反映对话内容
        4. 数值字段必须是-5到+5之间的整数
        
        JSON格式：
        {{
            "summary": "对话核心内容总结（≤50字）",
            "user_emotion": "用户核心情感",
            "ai_emotion": "智子核心情感",
            "affection_change": 0,  // 亲密度变化值
            "heat_change": 0,  // 热度变化值
            "sleepy_change": 0  // 困倦度变化值
        }}
        
        示例输出：
        {{"summary":"用户邀请智子睡觉，智子害羞接受并关心对方","user_emotion":"亲昵","ai_emotion":"害羞","affection_change":3,"heat_change":2,"sleepy_change":1}}
        """

        # 决定使用哪种API
        if use_siliconflow is None:
            use_siliconflow = self.siliconflow_client is not None
        
        try:
            if use_siliconflow and self.siliconflow_client:
                logger.info(f"开始调用硅基流动API（对话总结）({Config.SILICONFLOW_MODEL})")
                response = self.siliconflow_client.simple_chat(
                    prompt=prompt,
                    think=False,
                    temperature=0.1,  # 对话总结需要较低的温度
                    top_p=0.9
                )
                raw_response = response.get("response", "").strip()
            else:
                logger.info(f"开始调用本地Ollama模型（对话总结）({Config.OLLAMA_MODEL})")
                response = ollama.generate(
                    model=Config.OLLAMA_MODEL,
                    prompt=prompt,
                    think=False,
                    stream=False,
                    options={"temperature": 0.1, "gpu_layers": 999, "num_thread": 12, "n_ctx": 4096}
                )
                raw_response = response.get("response", "").strip()
            
            end_time = time.time()
            summary_length = len(raw_response)
            api_name = "硅基流动API" if (use_siliconflow and self.siliconflow_client) else "本地Ollama"
            logger.info(f"{api_name}（对话总结）调用完成，原始响应长度: {summary_length} 字符，耗时: {end_time - start_time:.2f} 秒")
            
            # 解析JSON响应
            try:
                # 去除可能的Markdown代码块标记
                clean_response = raw_response.strip()
                if clean_response.startswith('```json') and clean_response.endswith('```'):
                    clean_response = clean_response[7:-3].strip()
                elif clean_response.startswith('```') and clean_response.endswith('```'):
                    clean_response = clean_response[3:-3].strip()
                    
                summary_data = json.loads(clean_response)
                
                # 验证必要字段
                required_fields = ["summary", "user_emotion", "ai_emotion", "affection_change", "heat_change", "sleepy_change"]
                if not all(field in summary_data for field in required_fields):
                    logger.error(f"对话总结JSON格式不完整: {raw_response}")
                    return {"error": "JSON格式不完整"}
                
                # 验证数值字段范围
                for field in ["affection_change", "heat_change", "sleepy_change"]:
                    value = summary_data[field]
                    if not isinstance(value, int) or value < -5 or value > 5:
                        logger.error(f"对话总结数值字段超出范围: {field} = {value}")
                        return {"error": f"数值字段超出范围: {field}"}
                
                # 验证summary长度
                if len(summary_data["summary"]) > 50:
                    logger.warning(f"对话总结summary长度超过50字: {len(summary_data['summary'])} 字符")
                    # 仍返回结果，但记录警告
                
                logger.info(f"成功解析对话总结，提取到情感变化: affection={summary_data['affection_change']}, heat={summary_data['heat_change']}, sleepy={summary_data['sleepy_change']}")
                
                # 将情感变化应用到情感状态机
                try:
                    from emo_serv import EmotionalStateMachine
                    esm = EmotionalStateMachine()
                    esm.update_from_summary(summary_data)
                    logger.info(f"已将对话总结中的情感变化应用到EmotionalStateMachine: {esm.variables}")
                except Exception as esm_e:
                    logger.error(f"应用情感变化到EmotionalStateMachine失败: {esm_e}")
                    logger.debug(traceback.format_exc())
                
                return summary_data
                
            except json.JSONDecodeError as je:
                logger.error(f"解析对话总结JSON失败: {je}，原始响应: {raw_response}")
                return {"error": "JSON解析失败"}
                
        except Exception as e:
            end_time = time.time()
            logger.error(f"调用Ollama失败（对话总结）: {e}，耗时: {end_time - start_time:.2f} 秒")
            logger.debug(traceback.format_exc())
            return {"error": "模型调用失败"}
    
    def summarize_conversation(self, user_msg, assistant_msg, current_state, async_mode=True, use_siliconflow=None):
        """
        使用 LLM 总结对话并生成情感摘要，支持异步执行
        
        Args:
            user_msg: 用户消息
            assistant_msg: 助手消息
            current_state: 当前情感状态
            async_mode: 是否异步执行
            use_siliconflow: 是否使用硅基流动API，None表示自动选择
        """
        if async_mode:
            # 异步模式：提交到线程池执行，不阻塞主流程
            self.executor.submit(self._summarize_conversation_sync, user_msg, assistant_msg, current_state, use_siliconflow)
            return None  # 异步模式下不返回结果，避免阻塞
        else:
            # 同步模式：直接执行并返回结果
            return self._summarize_conversation_sync(user_msg, assistant_msg, current_state, use_siliconflow)
