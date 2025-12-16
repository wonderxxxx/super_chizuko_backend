"""
SiliconFlow API 客户端
用于与 SiliconFlow API 进行交互
"""

import requests
import json
import os
from typing import Dict, List, Optional, Any
import logging
from datetime import datetime

# 配置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class SiliconFlowClient:
    """
    SiliconFlow API 客户端类
    提供与 SiliconFlow API 的完整交互功能
    """
    
    def __init__(self, api_key: str = None, base_url: str = None):
        """
        初始化 SiliconFlow 客户端
        
        Args:
            api_key: API 密钥
            base_url: API 基础 URL
        """
        self.api_key = api_key or os.getenv('SILICONFLOW_API_KEY')
        self.base_url = base_url or "https://api.siliconflow.cn/v1"
        
        if not self.api_key:
            raise ValueError("API Key 是必需的，请设置 SILICONFLOW_API_KEY 环境变量或传入 api_key 参数")
        
        self.headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
        
        # 支持的模型列表
        self.supported_models = [
            "deepseek-ai/deepseek-chat",
            "deepseek-ai/deepseek-coder",
            "meta-llama/Llama-3.1-8B-Instruct",
            "meta-llama/Llama-3.1-70B-Instruct",
            "Qwen/Qwen2.5-7B-Instruct",
            "Qwen/Qwen2.5-72B-Instruct",
            "01-ai/Yi-1.5-34B-Chat",
            "mistralai/Mistral-7B-Instruct-v0.2"
        ]
    
    def get_available_models(self) -> List[str]:
        """获取可用的模型列表"""
        try:
            response = requests.get(f"{self.base_url}/models", headers=self.headers)
            response.raise_for_status()
            models_data = response.json()
            
            # 提取模型 ID
            available_models = []
            for model in models_data.get('data', []):
                model_id = model.get('id', '')
                if model_id:
                    available_models.append(model_id)
            
            logger.info(f"获取到 {len(available_models)} 个可用模型")
            return available_models
            
        except requests.RequestException as e:
            logger.error(f"获取模型列表失败: {e}")
            return self.supported_models
    
    def chat_completion(
        self, 
        messages: List[Dict[str, str]], 
        model: str = "deepseek-ai/deepseek-chat",
        temperature: float = 0.7,
        max_tokens: int = 2000,
        stream: bool = False,
        **kwargs
    ) -> Dict[str, Any]:
        """
        发起聊天完成请求
        
        Args:
            messages: 消息列表，格式为 [{"role": "user", "content": "..."}]
            model: 使用的模型名称
            temperature: 温度参数，控制输出的随机性
            max_tokens: 最大生成 token 数
            stream: 是否使用流式输出
            **kwargs: 其他参数
            
        Returns:
            API 响应结果
        """
        url = f"{self.base_url}/chat/completions"
        
        payload = {
            "model": model,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens,
            "stream": stream,
            **kwargs
        }
        
        try:
            response = requests.post(url, headers=self.headers, json=payload)
            response.raise_for_status()
            
            if stream:
                return self._handle_stream_response(response)
            else:
                return response.json()
                
        except requests.RequestException as e:
            logger.error(f"聊天完成请求失败: {e}")
            raise
    
    def _handle_stream_response(self, response):
        """处理流式响应"""
        for line in response.iter_lines():
            if line:
                line = line.decode('utf-8')
                if line.startswith('data: '):
                    data = line[6:]
                    if data == '[DONE]':
                        break
                    try:
                        yield json.loads(data)
                    except json.JSONDecodeError:
                        continue
    
    def text_embedding(
        self, 
        input_text: str, 
        model: str = "BAAI/bge-large-zh-v1.5"
    ) -> List[float]:
        """
        获取文本嵌入向量
        
        Args:
            input_text: 输入文本
            model: 嵌入模型名称
            
        Returns:
            嵌入向量
        """
        url = f"{self.base_url}/embeddings"
        
        payload = {
            "model": model,
            "input": input_text
        }
        
        try:
            response = requests.post(url, headers=self.headers, json=payload)
            response.raise_for_status()
            result = response.json()
            
            embeddings = result.get('data', [])[0].get('embedding', [])
            logger.info(f"成功获取嵌入向量，维度: {len(embeddings)}")
            return embeddings
            
        except requests.RequestException as e:
            logger.error(f"获取嵌入向量失败: {e}")
            raise
    
    def moderation(self, input_text: str) -> Dict[str, Any]:
        """
        内容审核
        
        Args:
            input_text: 待审核的文本
            
        Returns:
            审核结果
        """
        url = f"{self.base_url}/moderations"
        
        payload = {
            "input": input_text
        }
        
        try:
            response = requests.post(url, headers=self.headers, json=payload)
            response.raise_for_status()
            result = response.json()
            
            logger.info(f"内容审核完成")
            return result
            
        except requests.RequestException as e:
            logger.error(f"内容审核失败: {e}")
            raise
    
    def get_model_info(self, model: str) -> Dict[str, Any]:
        """
        获取特定模型信息
        
        Args:
            model: 模型名称
            
        Returns:
            模型信息
        """
        url = f"{self.base_url}/models/{model}"
        
        try:
            response = requests.get(url, headers=self.headers)
            response.raise_for_status()
            return response.json()
            
        except requests.RequestException as e:
            logger.error(f"获取模型信息失败: {e}")
            raise
    
    def validate_api_key(self) -> bool:
        """
        验证 API Key 是否有效
        
        Returns:
            bool: API Key 是否有效
        """
        try:
            # 尝试获取模型列表来验证 API Key
            models = self.get_available_models()
            return len(models) > 0
        except Exception:
            return False
    
    def health_check(self) -> Dict[str, Any]:
        """
        健康检查
        
        Returns:
            包含服务状态信息的字典
        """
        try:
            # 检查 API Key
            is_valid_key = self.validate_api_key()
            
            # 获取可用模型数量
            models = self.get_available_models()
            
            return {
                "status": "healthy" if is_valid_key else "unhealthy",
                "api_key_valid": is_valid_key,
                "available_models_count": len(models),
                "timestamp": datetime.now().isoformat(),
                "base_url": self.base_url
            }
            
        except Exception as e:
            return {
                "status": "unhealthy",
                "error": str(e),
                "timestamp": datetime.now().isoformat()
            }
    
    def simple_chat(self, message: str, model: str = "deepseek-ai/deepseek-chat") -> str:
        """
        简单聊天接口
        
        Args:
            message: 用户消息
            model: 使用的模型
            
        Returns:
            模型回复
        """
        messages = [{"role": "user", "content": message}]
        
        try:
            response = self.chat_completion(messages=messages, model=model)
            return response['choices'][0]['message']['content']
        except Exception as e:
            logger.error(f"简单聊天失败: {e}")
            raise
    
    def batch_chat(
        self, 
        messages_list: List[List[Dict[str, str]]], 
        model: str = "deepseek-ai/deepseek-chat"
    ) -> List[str]:
        """
        批量聊天
        
        Args:
            messages_list: 消息列表的列表
            model: 使用的模型
            
        Returns:
            回复列表
        """
        results = []
        
        for messages in messages_list:
            try:
                response = self.chat_completion(messages=messages, model=model)
                result = response['choices'][0]['message']['content']
                results.append(result)
            except Exception as e:
                logger.error(f"批量聊天中的某个请求失败: {e}")
                results.append(f"Error: {str(e)}")
        
        return results
    
    def chat_with_tools(
        self,
        prompt: str,
        tools: List[Dict[str, Any]],
        model: str = "deepseek-ai/deepseek-chat",
        temperature: float = 0.7,
        **kwargs
    ) -> Dict[str, Any]:
        """
        带工具的聊天完成
        
        Args:
            prompt: 用户提示
            tools: 工具列表
            model: 使用的模型名称
            temperature: 温度参数
            **kwargs: 其他参数
            
        Returns:
            包含响应和工具调用的字典
        """
        messages = [{"role": "user", "content": prompt}]
        
        try:
            response = self.chat_completion(
                messages=messages,
                model=model,
                temperature=temperature,
                tools=tools,
                tool_choice="auto",
                **kwargs
            )
            
            # 解析响应
            message = response['choices'][0]['message']
            content = message.get('content', '')
            tool_calls = message.get('tool_calls', [])
            
            # 转换工具调用格式
            formatted_tool_calls = []
            for tool_call in tool_calls:
                if tool_call.get('type') == 'function':
                    function = tool_call.get('function', {})
                    formatted_tool_calls.append({
                        'name': function.get('name'),
                        'arguments': function.get('arguments', {})
                    })
            
            return {
                'response': content,
                'thinking': None,
                'tool_calls': formatted_tool_calls
            }
            
        except Exception as e:
            logger.error(f"带工具聊天失败: {e}")
            return {
                'response': f"Error: {str(e)}",
                'thinking': None,
                'tool_calls': []
            }


# 便捷函数
def create_client(api_key: str = None, base_url: str = None) -> SiliconFlowClient:
    """
    创建 SiliconFlow 客户端实例
    
    Args:
        api_key: API 密钥
        base_url: API 基础 URL
        
    Returns:
        SiliconFlowClient 实例
    """
    return SiliconFlowClient(api_key=api_key, base_url=base_url)


# 测试函数
def test_client():
    """测试客户端功能"""
    try:
        client = SiliconFlowClient()
        
        # 健康检查
        health = client.health_check()
        print("健康检查结果:", health)
        
        if health["status"] == "healthy":
            # 简单聊天测试
            response = client.simple_chat("你好，请介绍一下自己。")
            print("模型回复:", response)
            
            # 获取可用模型
            models = client.get_available_models()
            print(f"可用模型数量: {len(models)}")
            print("前5个模型:", models[:5])
        else:
            print("客户端不健康，无法进行测试")
            
    except Exception as e:
        print(f"测试失败: {e}")


if __name__ == "__main__":
    test_client()