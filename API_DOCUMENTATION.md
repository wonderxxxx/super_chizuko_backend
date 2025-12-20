# 后端接口文档

## 1. 概述

本文档描述了Super Chizuko后端服务提供的所有API接口。该服务是一个基于Flask的聊天机器人后端，集成了情感状态机、记忆管理和AI对话功能。

## 2. 接口列表

| 路径 | 方法 | 功能描述 |
|------|------|----------|
| /chat | POST | 简单聊天接口 |
| /mcp/chat | POST | MCP协议兼容的聊天接口 |
| /health | GET | 健康检查 |
| /memory/clear | POST | 清空特定用户的所有记忆 |
| /chat/initial | POST | 生成首次对话的开场白 |
| /chat/history | GET | 获取特定用户的聊天记录 |
| /chat/history/clear | POST | 清空特定用户的所有聊天记录 |
| /auth/send-verification | POST | 发送邮箱验证码 |
| /auth/verify | POST | 验证邮箱验证码 |

## 3. 详细接口说明

### 3.1 聊天接口

#### 3.1.1 POST /chat

**功能描述**：处理简单的聊天请求，返回AI响应并更新用户的情感状态。

**请求参数**：

| 参数名 | 类型 | 必选 | 描述 |
|--------|------|------|------|
| message | string | 是 | 用户输入的消息内容 |
| email | string | 否 | 用户邮箱，默认为"default@example.com" |
| include_thinking | boolean | 否 | 是否返回思考过程，默认为false |

**请求示例**：
```json
{
  "message": "你好！",
  "email": "user@example.com",
  "include_thinking": true
}
```

**响应格式**：

```json
{
  "response": "你好呀！有什么可以帮你的吗？",
  "current_state": "happy",
  "state_description": "愉快的",
  "emotional_variables": {
    "joy": 0.8,
    "sadness": 0.2,
    "anger": 0.0
  },
  "thinking": "用户说'你好！'，我应该友好地回应..."
}
```

**错误响应**：

```json
{
  "error": "缺少message参数"
}
```

```json
{
  "error": "邮箱未验证，请先验证邮箱",
  "need_verification": true
}
```

### 3.2 MCP协议兼容的聊天接口

#### 3.2.1 POST /mcp/chat

**功能描述**：提供MCP (Model Communication Protocol) 协议兼容的聊天接口，支持工具调用。

**请求参数**：

```json
{
  "jsonrpc": "2.0",
  "method": "chat",
  "params": {
    "message": "你好！",
    "email": "user@example.com",
    "include_thinking": true
  },
  "id": 1
}
```

**响应格式**：

```json
{
  "jsonrpc": "2.0",
  "result": {
    "response": "你好呀！有什么可以帮你的吗？",
    "thinking": "用户说'你好！'，我应该友好地回应...",
    "state": "happy",
    "state_description": "愉快的",
    "variables": {
      "joy": 0.8,
      "sadness": 0.2,
      "anger": 0.0
    }
  },
  "id": 1
}
```

**错误响应**：

```json
{
  "jsonrpc": "2.0",
  "error": {
    "code": -32602,
    "message": "缺少message参数"
  },
  "id": 1
}
```

### 3.3 健康检查

#### 3.3.1 GET /health

**功能描述**：检查服务的健康状态。

**请求参数**：无

**响应格式**：

```json
{
  "status": "ok",
  "service": "Ollama Chat Service with Emotion State Machine"
}
```

### 3.4 记忆管理

#### 3.4.1 POST /memory/clear

**功能描述**：清空特定用户的所有记忆，并重新生成初始对话。

**请求参数**：

| 参数名 | 类型 | 必选 | 描述 |
|--------|------|------|------|
| email | string | 否 | 用户邮箱，默认为"default@example.com" |

**请求示例**：
```json
{
  "email": "user@example.com"
}
```

**响应格式**：

```json
{
  "status": "success",
  "message": "用户 user@example.com 的记忆已成功清空",
  "collection_name": "user_123",
  "initial_message": "你好！我是Chizuko，很高兴认识你！",
  "current_state": "happy",
  "state_description": "愉快的",
  "emotional_variables": {
    "joy": 0.8,
    "sadness": 0.2,
    "anger": 0.0
  }
}
```

### 3.5 聊天初始化

#### 3.5.1 POST /chat/initial

**功能描述**：为新用户生成首次对话的开场白。

**请求参数**：

| 参数名 | 类型 | 必选 | 描述 |
|--------|------|------|------|
| email | string | 否 | 用户邮箱，默认为"default@example.com" |

**请求示例**：
```json
{
  "email": "user@example.com"
}
```

**响应格式**：

```json
{
  "status": "success",
  "response": "你好！我是Chizuko，很高兴认识你！",
  "current_state": "happy",
  "state_description": "愉快的",
  "emotional_variables": {
    "joy": 0.8,
    "sadness": 0.2,
    "anger": 0.0
  }
}
```

### 3.6 聊天历史管理

#### 3.6.1 GET /chat/history

**功能描述**：获取特定用户的聊天记录。

**请求参数**：

| 参数名 | 类型 | 必选 | 描述 |
|--------|------|------|------|
| email | string | 否 | 用户邮箱，默认为"default@example.com" |

**请求示例**：
```
GET /chat/history?email=user@example.com
```

**响应格式**：

```json
{
  "status": "success",
  "chat_history": [
    {
      "id": 1,
      "user_message": "你好！",
      "assistant_message": "你好呀！有什么可以帮你的吗？",
      "state": "happy",
      "created_at": "2023-10-01T12:00:00"
    },
    {
      "id": 2,
      "user_message": "今天天气怎么样？",
      "assistant_message": "今天天气很好，阳光明媚！",
      "state": "happy",
      "created_at": "2023-10-01T12:05:00"
    }
  ],
  "user_email": "user@example.com"
}
```

#### 3.6.2 POST /chat/history/clear

**功能描述**：清空特定用户的所有聊天记录。

**请求参数**：

| 参数名 | 类型 | 必选 | 描述 |
|--------|------|------|------|
| email | string | 否 | 用户邮箱，默认为"default@example.com" |

**请求示例**：
```json
{
  "email": "user@example.com"
}
```

**响应格式**：

```json
{
  "status": "success",
  "message": "用户 user@example.com 的聊天记录已成功清空",
  "deleted_count": 5
}
```

### 3.7 邮箱认证

#### 3.7.1 POST /auth/send-verification

**功能描述**：发送邮箱验证码用于用户验证。

**请求参数**：

| 参数名 | 类型 | 必选 | 描述 |
|--------|------|------|------|
| email | string | 是 | 用户邮箱 |

**请求示例**：
```json
{
  "email": "user@example.com"
}
```

**响应格式**：

```json
{
  "success": true,
  "message": "验证码发送成功",
  "email": "user@example.com"
}
```

**错误响应**：

```json
{
  "error": "邮箱不能为空"
}
```

#### 3.7.2 POST /auth/verify

**功能描述**：验证用户提供的邮箱验证码。

**请求参数**：

| 参数名 | 类型 | 必选 | 描述 |
|--------|------|------|------|
| email | string | 是 | 用户邮箱 |
| code | string | 是 | 验证码 |

**请求示例**：
```json
{
  "email": "user@example.com",
  "code": "123456"
}
```

**响应格式**：

```json
{
  "success": true,
  "message": "邮箱验证成功",
  "email": "user@example.com"
}
```

**错误响应**：

```json
{
  "error": "邮箱和验证码不能为空"
}
```

```json
{
  "error": "验证码错误"
}
```

## 4. 状态码说明

| 状态码 | 描述 |
|--------|------|
| 200 | 请求成功 |
| 400 | 请求参数错误 |
| 401 | 未授权（邮箱未验证） |
| 404 | 请求的资源不存在 |
| 500 | 服务器内部错误 |

## 5. 情感状态说明

情感状态机支持多种情绪状态，每个状态都有相应的描述和变量：

| 状态 | 描述 |
|------|------|
| happy | 愉快的 |
| sad | 悲伤的 |
| angry | 生气的 |
| neutral | 中性的 |
| excited | 兴奋的 |
| tired | 疲惫的 |

## 6. 注意事项

1. 所有需要用户身份的接口都需要提供有效的邮箱地址
2. 首次使用前需要通过邮箱验证
3. 聊天记录和记忆会根据用户邮箱进行隔离
4. 记忆管理使用异步处理，可能会有延迟

## 7. 示例代码

### Python 示例

```python
import requests

# 发送聊天请求
response = requests.post(
    "http://localhost:5000/chat",
    json={
        "message": "你好！",
        "email": "user@example.com"
    }
)

print(response.json())
```

### JavaScript 示例

```javascript
fetch('http://localhost:5000/chat', {
    method: 'POST',
    headers: {
        'Content-Type': 'application/json'
    },
    body: JSON.stringify({
        message: '你好！',
        email: 'user@example.com'
    })
})
.then(response => response.json())
.then(data => console.log(data));
```
