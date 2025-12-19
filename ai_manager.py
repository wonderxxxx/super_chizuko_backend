import os
# 移除 ollama 导入
import traceback
import concurrent.futures
from sentence_transformers import SentenceTransformer
from config import Config
import json

from emotion_state_serv.emo_serv import EmotionalStateMachine, generate_reply
import logging
import time
from siliconflow_client import SiliconFlowClient

# 配置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class AIManager:
    """AI模型管理器"""

    def __init__(self):
        # 移除 self.ollama_model = Config.OLLAMA_MODEL
        self.embedding_model = self._load_embedding_model()
        self.tools = {}
        self._register_default_tools()
        # 创建线程池用于异步执行记忆总结
        self.executor = concurrent.futures.ThreadPoolExecutor(max_workers=2)

        # 初始化硅基流动客户端（强制使用）
        self.siliconflow_client = None
        try:
            if Config.SILICONFLOW_API_KEY:
                self.siliconflow_client = SiliconFlowClient()
                logger.info("硅基流动API客户端初始化成功")
            else:
                # 即使没有API密钥也强制初始化（可以抛出异常或使用默认值）
                self.siliconflow_client = SiliconFlowClient()
                logger.info("硅基流动API客户端初始化成功")
        except Exception as e:
            logger.error(f"硅基流动API客户端初始化失败: {e}")
            raise  # 强制使用硅基流动，如果初始化失败就抛出异常

    # ... existing code ...

    def get_ai_response(self, prompt, think=False, raw=False, use_siliconflow=None):
        """
        获取AI模型响应，只使用硅基流动API

        Args:
            prompt: 输入提示
            think: 是否返回推理过程
            raw: 是否返回原始响应
            use_siliconflow: 参数保留但忽略，始终使用硅基流动

        Returns:
            包含响应和思考过程的字典
        """
        start_time = time.time()

        # 强制使用硅基流动API
        if self.siliconflow_client:
            return self._get_siliconflow_response(prompt, think, raw, start_time)
        else:
            raise Exception("硅基流动API客户端未初始化")

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
            logger.info(f"硅基流动API调用完成，响应长度: {len(response)} 字符，耗时: {end_time - start_time:.2f} 秒")
            # 硅基流动API直接返回文本，包装成与之前一致的格式
            return {
                "response": response,
                "thinking": None  # 硅基流动API暂不支持思考过程
            }

        except Exception as e:
            end_time = time.time()
            logger.error(f"硅基流动API调用失败: {e}，耗时: {end_time - start_time:.2f} 秒")
            logger.debug(traceback.format_exc())
            # 不再回退到Ollama
            raise  # 直接抛出异常

    # 移除 _get_ollama_response 方法

    def get_ollama_response(self, prompt, think=False, raw=False):
        """保持向后兼容性的方法，但实际调用硅基流动"""
        return self.get_ai_response(prompt, think, raw, use_siliconflow=True)

    def get_ai_response_with_tools(self, prompt, think=False, use_siliconflow=None):
        """
        获取AI模型响应（支持工具调用），只使用硅基流动API

        Args:
            prompt: 输入提示
            think: 是否返回推理过程
            use_siliconflow: 参数保留但忽略，始终使用硅基流动

        Returns:
            包含响应、思考和工具调用的字典
        """
        start_time = time.time()

        # 强制使用硅基流动API
        if self.siliconflow_client:
            return self._get_siliconflow_response_with_tools(prompt, think, start_time)
        else:
            raise Exception("硅基流动API客户端未初始化")

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
                        "parameters": {},  # 根据需要添加参数定义
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
            logger.info(
                f"硅基流动API（带工具）调用完成，响应长度: {response_length} 字符，工具调用数: {tool_calls_count}，耗时: {end_time - start_time:.2f} 秒")
            return response

        except Exception as e:
            end_time = time.time()
            logger.error(f"硅基流动API（带工具）调用失败: {e}，耗时: {end_time - start_time:.2f} 秒")
            logger.debug(traceback.format_exc())
            # 不再回退到Ollama
            raise  # 直接抛出异常

    # 移除 _get_ollama_response_with_tools 方法

    def get_ollama_response_with_tools(self, prompt, think=False):
        """保持向后兼容性的方法，但实际调用硅基流动"""
        return self.get_ai_response_with_tools(prompt, think, use_siliconflow=True)

    def _summarize_conversation_sync(self, user_msg, assistant_msg, current_state, use_siliconflow=None):
        """同步执行对话总结，只使用硅基流动"""
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

        # 强制使用硅基流动API
        try:
            if self.siliconflow_client:
                logger.info(f"开始调用硅基流动API（对话总结）({Config.SILICONFLOW_MODEL})")
                response = self.siliconflow_client.simple_chat(
                    prompt=prompt,
                    temperature=0.1,  # 对话总结需要较低的温度
                    top_p=0.9
                )
                raw_response = response.strip()
            else:
                raise Exception("硅基流动API客户端未初始化")

            end_time = time.time()
            summary_length = len(raw_response)
            logger.info(
                f"硅基流动API（对话总结）调用完成，原始响应长度: {summary_length} 字符，耗时: {end_time - start_time:.2f} 秒")

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
                required_fields = ["summary", "user_emotion", "ai_emotion", "affection_change", "heat_change",
                                   "sleepy_change"]
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

                logger.info(
                    f"成功解析对话总结，提取到情感变化: affection={summary_data['affection_change']}, heat={summary_data['heat_change']}, sleepy={summary_data['sleepy_change']}")

                # 将情感变化应用到情感状态机
                try:
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
            logger.error(f"调用硅基流动API失败（对话总结）: {e}，耗时: {end_time - start_time:.2f} 秒")
            logger.debug(traceback.format_exc())
            raise  # 直接抛出异常，不再回退到Ollama