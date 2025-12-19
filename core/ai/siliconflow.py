import requests
import json
import traceback
from typing import Dict, List, Any
from config.settings import Config
from .base import AIProvider
import logging

# 配置日志
logger = logging.getLogger(__name__)

class SiliconFlowClient(AIProvider):
    """硅基流动API客户端，继承自AIProvider抽象类"""
    
    def __init__(self):
        """初始化客户端"""
        self.api_key = Config.SILICONFLOW_API_KEY
        self.base_url = Config.SILICONFLOW_BASE_URL
        self.model = Config.SILICONFLOW_MODEL
        self.max_tokens = Config.SILICONFLOW_MAX_TOKENS
        
        if not self.api_key:
            raise ValueError("硅基流动API密钥未配置")
    
    def chat(self, prompt: str, model: str = None, max_tokens: int = None, 
                    temperature: float = None, top_p: float = None, 
                    frequency_penalty: float = None, **kwargs) -> Dict[str, Any]:
        """聊天接口，实现AIProvider抽象方法"""
        # 使用默认值如果未提供
        model = model or self.model
        max_tokens = max_tokens or self.max_tokens
        temperature = temperature or Config.SILICONFLOW_TEMPERATURE
        top_p = top_p or Config.SILICONFLOW_TOP_P
        frequency_penalty = frequency_penalty or Config.SILICONFLOW_FREQUENCY_PENALTY
         
        # 构建请求体，参考官网示例
        payload = {
            "model": model,
            "messages": [
                {"role": "user", "content": prompt}
            ],
            "stream": False,
            "max_tokens": max_tokens,
            "enable_thinking": False,
            "thinking_budget": 4096,
            "min_p": 0.05,
            "stop": None,
            "temperature": temperature,
            "top_p": top_p,
            "top_k": Config.SILICONFLOW_TOP_K,
            "frequency_penalty": frequency_penalty,
            "n": 1,
            "response_format": {"type": "text"}
        }
        # 发送请求
        return self._send_request(payload)
    
    def chat_with_tools(self, prompt: str, tools: List[Dict], model: str = None, 
                        max_tokens: int = None, temperature: float = None, 
                        top_p: float = None, frequency_penalty: float = None, **kwargs) -> Dict[str, Any]:
        """带工具的聊天接口，实现AIProvider抽象方法"""
        # 使用默认值如果未提供
        model = model or self.model
        max_tokens = max_tokens or self.max_tokens
        temperature = temperature or Config.SILICONFLOW_TEMPERATURE
        top_p = top_p or Config.SILICONFLOW_TOP_P
        frequency_penalty = frequency_penalty or Config.SILICONFLOW_FREQUENCY_PENALTY
        
        # 构建请求体，参考官网示例
        payload = {
            "model": model,
            "messages": [
                {"role": "user", "content": prompt}
            ],
            "stream": False,
            "max_tokens": max_tokens,
            "enable_thinking": False,
            "thinking_budget": 4096,
            "min_p": 0.05,
            "stop": None,
            "temperature": temperature,
            "top_p": top_p,
            "top_k": Config.SILICONFLOW_TOP_K,
            "frequency_penalty": frequency_penalty,
            "n": 1,
            "response_format": {"type": "text"},
            "tools": tools
        }
        
        # 发送请求
        return self._send_request(payload)
    
    def _send_request(self, payload: Dict[str, Any]) -> Any:
        """发送HTTP请求到硅基流动API"""
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
        
        try:
            # 添加调试信息
            logger.info(f"开始发送请求到硅基流动API: {self.base_url}")
            logger.info(f"API密钥长度: {len(self.api_key) if self.api_key else 0}")
            logger.info(f"请求超时设置: 30秒")
            
            response = requests.post(
                self.base_url,
                headers=headers,
                json=payload,  # 使用json参数自动序列化，与官网示例保持一致
                timeout=30
            )
            
            logger.info(f"请求完成，响应状态码: {response.status_code}")
            
            response.raise_for_status()  # 检查HTTP错误
            
            result = response.json()
            logger.info(f"成功解析响应JSON")
            
            # 处理响应
            if result.get("choices"):
                choice = result["choices"][0]
                response_data = {
                    "response": choice["message"]["content"]
                }
                # 处理思考过程
                if "thinking" in choice:
                    response_data["thinking"] = choice["thinking"]
                    logger.info(f"响应包含思考过程，长度: {len(response_data['thinking'])} 字符")
                logger.info(f"响应内容长度: {len(response_data['response'])} 字符")
                return response_data
            elif result.get("tool_calls"):
                logger.info(f"响应包含工具调用，数量: {len(result['tool_calls'])}")
                return result
            else:
                logger.error(f"硅基流动API响应格式错误，缺少choices或tool_calls字段")
                raise ValueError(f"硅基流动API响应格式错误: {result}")
                
        except requests.exceptions.Timeout:
            logger.error(f"硅基流动API请求超时（30秒）")
            logger.debug(traceback.format_exc())
            raise
        except requests.exceptions.ConnectionError:
            logger.error(f"硅基流动API连接失败")
            logger.debug(traceback.format_exc())
            raise
        except requests.exceptions.HTTPError as e:
            logger.error(f"硅基流动APIHTTP错误: {e.response.status_code} - {e.response.text}")
            logger.debug(traceback.format_exc())
            raise
        except requests.exceptions.RequestException as e:
            logger.error(f"硅基流动API请求失败: {e}")
            logger.debug(traceback.format_exc())
            raise
        except json.JSONDecodeError as e:
            logger.error(f"硅基流动API响应解析失败: {e}")
            logger.debug(traceback.format_exc())
            raise
        except Exception as e:
            logger.error(f"硅基流动API客户端错误: {e}")
            logger.debug(traceback.format_exc())
            raise
