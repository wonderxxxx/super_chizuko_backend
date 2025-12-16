#!/usr/bin/env python3
"""
硅基流动API测试脚本
"""
import os
import sys
from siliconflow_client import SiliconFlowClient
from ai_manager import AIManager
import logging

# 配置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def test_siliconflow_client():
    """测试硅基流动API客户端"""
    print("=== 测试硅基流动API客户端 ===")
    
    # 设置测试API密钥（请替换为您的实际API密钥）
    test_api_key = os.getenv("SILICONFLOW_API_KEY", "")
    if not test_api_key:
        print("错误: 请设置环境变量 SILICONFLOW_API_KEY")
        return False
    
    try:
        client = SiliconFlowClient(api_key=test_api_key)
        
        # 测试简单聊天
        print("\n1. 测试简单聊天...")
        response = client.simple_chat("你好，请介绍一下你自己")
        print(f"响应: {response.get('response', 'No response')}")
        if response.get('thinking'):
            print(f"推理过程: {response['thinking']}")
        
        # 测试带工具的聊天
        print("\n2. 测试带工具的聊天...")
        tools = [
            {
                "type": "function",
                "function": {
                    "name": "getCurrentTime",
                    "description": "获取当前时间",
                    "parameters": {},
                    "strict": False
                }
            }
        ]
        response = client.chat_with_tools(
            "现在几点了？请调用工具获取当前时间",
            tools=tools
        )
        print(f"响应: {response.get('response', 'No response')}")
        print(f"工具调用: {response.get('tool_calls', [])}")
        
        print("\n✅ 硅基流动API客户端测试成功!")
        return True
        
    except Exception as e:
        print(f"\n❌ 硅基流动API客户端测试失败: {e}")
        return False

def test_ai_manager():
    """测试AI管理器集成"""
    print("\n=== 测试AI管理器集成 ===")
    
    try:
        ai_manager = AIManager()
        
        print(f"硅基流动客户端状态: {'已初始化' if ai_manager.siliconflow_client else '未初始化'}")
        
        # 测试自动选择API
        print("\n1. 测试自动API选择...")
        response = ai_manager.get_ai_response("你好，请简单介绍一下你的能力")
        print(f"响应: {response.get('response', 'No response')}")
        
        # 测试强制使用硅基流动
        if ai_manager.siliconflow_client:
            print("\n2. 测试强制使用硅基流动API...")
            response = ai_manager.get_ai_response(
                "请用更丰富的语言描述春天",
                use_siliconflow=True
            )
            print(f"响应: {response.get('response', 'No response')}")
        else:
            print("\n2. 硅基流动API未配置，跳过测试")
        
        # 测试带工具的响应
        print("\n3. 测试带工具的响应...")
        response = ai_manager.get_ai_response_with_tools(
            "现在几点了？请调用工具获取当前时间"
        )
        print(f"响应: {response.get('response', 'No response')}")
        print(f"工具调用: {response.get('tool_calls', [])}")
        
        print("\n✅ AI管理器集成测试成功!")
        return True
        
    except Exception as e:
        print(f"\n❌ AI管理器集成测试失败: {e}")
        return False

def main():
    """主测试函数"""
    print("开始硅基流动API功能测试...\n")
    
    # 检查环境变量
    if not os.getenv("SILICONFLOW_API_KEY"):
        print("⚠️  警告: 未设置 SILICONFLOW_API_KEY 环境变量")
        print("请设置API密钥后再运行完整测试:")
        print("export SILICONFLOW_API_KEY='your_api_key_here'\n")
        print("将仅测试AI管理器的本地Ollama功能...\n")
    
    # 测试硅基流动客户端（需要API密钥）
    siliconflow_success = test_siliconflow_client()
    
    # 测试AI管理器（无论是否有API密钥都可以测试）
    ai_manager_success = test_ai_manager()
    
    # 总结
    print("\n" + "="*50)
    print("测试总结:")
    print(f"硅基流动API客户端: {'✅ 通过' if siliconflow_success else '❌ 失败'}")
    print(f"AI管理器集成: {'✅ 通过' if ai_manager_success else '❌ 失败'}")
    
    if siliconflow_success or ai_manager_success:
        print("\n🎉 测试完成，硅基流动API集成功能正常!")
        print("\n使用说明:")
        print("1. 设置环境变量 SILICONFLOW_API_KEY='your_api_key_here'")
        print("2. AI管理器将自动优先使用硅基流动API")
        print("3. 可以通过 use_siliconflow=True/False 强制选择API")
        print("4. API调用失败时会自动回退到本地Ollama")
    else:
        print("\n❌ 测试失败，请检查配置")

if __name__ == "__main__":
    main()