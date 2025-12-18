import requests
import json
from typing import Dict, List, Any
from config import Config
import logging

# 配置日志
logger = logging.getLogger(__name__)

class SiliconFlowClient:
    """硅基流动API客户端"""
    
    def __init__(self):
        """初始化客户端"""
        self.api_key = Config.SILICONFLOW_API_KEY
        self.base_url = Config.SILICONFLOW_BASE_URL
        self.model = Config.SILICONFLOW_MODEL
        self.max_tokens = Config.SILICONFLOW_MAX_TOKENS
        
        if not self.api_key:
            raise ValueError("硅基流动API密钥未配置")
    
    def simple_chat(self, prompt: str, model: str = None, max_tokens: int = None, 
                    temperature: float = None, top_p: float = None, 
                    frequency_penalty: float = None) -> str:
        """简单聊天接口"""
        # 使用默认值如果未提供
        model = model or self.model
        max_tokens = max_tokens or self.max_tokens
        temperature = temperature or Config.SILICONFLOW_TEMPERATURE
        top_p = top_p or Config.SILICONFLOW_TOP_P
        frequency_penalty = frequency_penalty or Config.SILICONFLOW_FREQUENCY_PENALTY
        
        # 构建请求体
        payload = {
            "model": model,
            "messages": [
                {"role": "user", "content": prompt}
            ],
            "max_tokens": max_tokens,
            "temperature": temperature,
            "top_p": top_p,
            "frequency_penalty": frequency_penalty
        }
        
        # 发送请求
        return self._send_request(payload)
    
    def chat_with_tools(self, prompt: str, tools: List[Dict], model: str = None, 
                        max_tokens: int = None, temperature: float = None, 
                        top_p: float = None, frequency_penalty: float = None) -> Dict[str, Any]:
        """带工具的聊天接口"""
        # 使用默认值如果未提供
        model = model or self.model
        max_tokens = max_tokens or self.max_tokens
        temperature = temperature or Config.SILICONFLOW_TEMPERATURE
        top_p = top_p or Config.SILICONFLOW_TOP_P
        frequency_penalty = frequency_penalty or Config.SILICONFLOW_FREQUENCY_PENALTY
        
        # 构建请求体
        payload = {
            "model": model,
            "messages": [
                {"role": "user", "content": prompt}
            ],
            "tools": tools,
            "tool_choice": "auto",
            "max_tokens": max_tokens,
            "temperature": temperature,
            "top_p": top_p,
            "frequency_penalty": frequency_penalty
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
            response = requests.post(
                self.base_url,
                headers=headers,
                data=json.dumps(payload),
                timeout=30
            )
            
            response.raise_for_status()  # 检查HTTP错误
            
            result = response.json()
            
            # 处理响应
            if result.get("choices"):
                return result["choices"][0]["message"]["content"]
            elif result.get("tool_calls"):
                return result
            else:
                raise ValueError(f"硅基流动API响应格式错误: {result}")
                
        except requests.exceptions.RequestException as e:
            logger.error(f"硅基流动API请求失败: {e}")
            raise
        except json.JSONDecodeError as e:
            logger.error(f"硅基流动API响应解析失败: {e}")
            raise
        except Exception as e:
            logger.error(f"硅基流动API客户端错误: {e}")
            raise