# 硅基流动API集成说明

## 概述

本项目已集成硅基流动API，提供比本地Ollama更快的推理速度和更强的推理能力。系统支持自动选择API，并在API调用失败时自动回退到本地Ollama。

## 配置方法

### 1. 环境变量配置

设置硅基流动API密钥：

```bash
# Windows
set SILICONFLOW_API_KEY="your_api_key_here"

# Linux/Mac
export SILICONFLOW_API_KEY="your_api_key_here"
```

### 2. 配置文件修改（可选）

在 `config.py` 中可以修改以下配置：

```python
# 硅基流动API配置
SILICONFLOW_API_KEY = os.getenv("SILICONFLOW_API_KEY", "")
SILICONFLOW_BASE_URL = "https://api.siliconflow.cn/v1/chat/completions"
SILICONFLOW_MODEL = "Qwen/QwQ-32B"  # 默认模型
SILICONFLOW_MAX_TOKENS = 4096
SILICONFLOW_TEMPERATURE = 0.7
SILICONFLOW_TOP_P = 0.7
SILICONFLOW_TOP_K = 50
SILICONFLOW_FREQUENCY_PENALTY = 0.5
```

## 使用方法

### 1. AI管理器自动选择

```python
from ai_manager import AIManager

ai_manager = AIManager()

# 自动选择API（优先硅基流动，回退到本地Ollama）
response = ai_manager.get_ai_response("你好")
```

### 2. 强制使用特定API

```python
# 强制使用硅基流动API
response = ai_manager.get_ai_response("你好", use_siliconflow=True)

# 强制使用本地Ollama
response = ai_manager.get_ai_response("你好", use_siliconflow=False)
```

### 3. 带工具的调用

```python
# 自动选择API
response = ai_manager.get_ai_response_with_tools("现在几点了？")

# 强制使用硅基流动API
response = ai_manager.get_ai_response_with_tools(
    "现在几点了？", 
    use_siliconflow=True
)
```

### 4. 对话总结

```python
# 异步模式（默认）
ai_manager.summarize_conversation(user_msg, assistant_msg, current_state)

# 同步模式，使用硅基流动API
summary = ai_manager.summarize_conversation(
    user_msg, 
    assistant_msg, 
    current_state, 
    async_mode=False, 
    use_siliconflow=True
)
```

## API选择策略

### 自动选择逻辑

1. **优先级顺序**：
   - 硅基流动API（如果API密钥已配置）
   - 本地Ollama（作为回退选项）

2. **回退机制**：
   - 硅基流动API调用失败时自动回退到本地Ollama
   - 本地Ollama调用失败时返回默认响应

3. **性能考虑**：
   - 硅基流动API：云端推理，速度快，能力强
   - 本地Ollama：本地推理，无网络依赖，但速度较慢

## 测试方法

运行测试脚本：

```bash
python test_siliconflow.py
```

测试脚本将验证：
1. 硅基流动API客户端功能
2. AI管理器集成
3. API选择和回退机制

## 支持的模型

硅基流动API支持多种模型，常用的包括：

- `Qwen/QwQ-32B` - 强大的推理模型（默认）
- `Qwen/Qwen2.5-72B-Instruct` - 通用对话模型
- `deepseek-ai/DeepSeek-V3` - DeepSeek最新模型

可以在 `config.py` 中修改 `SILICONFLOW_MODEL` 来切换模型。

## 性能对比

| 特性 | 硅基流动API | 本地Ollama |
|------|------------|------------|
| 推理速度 | 快 | 慢 |
| 推理能力 | 强 | 中等 |
| 网络依赖 | 需要 | 不需要 |
| 成本 | 按使用量付费 | 免费 |
| 隐私性 | 云端处理 | 本地处理 |
| 可用性 | 99.9% | 依赖本地硬件 |

## 错误处理

### 常见错误及解决方案

1. **API密钥未设置**
   ```
   错误: 硅基流动API密钥未配置
   解决: 设置环境变量 SILICONFLOW_API_KEY
   ```

2. **网络连接问题**
   ```
   错误: API请求失败
   解决: 检查网络连接，系统会自动回退到本地Ollama
   ```

3. **模型不存在**
   ```
   错误: 模型不存在
   解决: 在 config.py 中修改 SILICONFLOW_MODEL
   ```

4. **本地Ollama未启动**
   ```
   错误: 连接Ollama失败
   解决: 启动本地Ollama服务: ollama serve
   ```

## 监控和日志

系统会记录所有API调用的详细信息：

- API选择决策
- 调用耗时
- 令牌使用量
- 错误信息和回退情况

日志级别可通过修改 `logging.basicConfig()` 调整。

## 注意事项

1. **API费用**：硅基流动API按使用量计费，请注意控制使用量
2. **网络依赖**：使用硅基流动API需要稳定的网络连接
3. **数据隐私**：通过硅基流动API发送的数据会在云端处理
4. **模型限制**：不同模型有不同的令牌限制和功能特性

## 升级和维护

- 定期检查 `requirements.txt` 中的依赖版本
- 关注硅基流动API的更新和变更
- 监控API使用量和费用
- 定期测试API集成功能

## 技术支持

如遇到问题，请检查：

1. API密钥是否正确设置
2. 网络连接是否正常
3. 模型名称是否正确
4. 配置文件是否正确

如有其他问题，请查看日志文件获取详细错误信息。