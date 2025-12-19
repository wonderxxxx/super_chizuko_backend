from abc import ABC, abstractmethod
from typing import Dict, List, Any


class AIProvider(ABC):
    """AI服务提供商抽象基类"""

    @abstractmethod
    def chat(self, prompt: str, **kwargs) -> Dict[str, Any]:
        """
        聊天接口
        
        Args:
            prompt: 输入提示
            **kwargs: 其他参数，如model、max_tokens、temperature等
            
        Returns:
            包含响应的字典
        """
        pass

    @abstractmethod
    def chat_with_tools(self, prompt: str, tools: List[Dict], **kwargs) -> Dict[str, Any]:
        """
        带工具的聊天接口
        
        Args:
            prompt: 输入提示
            tools: 可用工具列表
            **kwargs: 其他参数
            
        Returns:
            包含响应和工具调用的字典
        """
        pass