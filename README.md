# Super Chizuko Backend

这是超级智子，一个衍生于奇点chat千夜智子的山寨版本，具有情绪管理、记忆功能和智能对话能力。

## 🌟 功能特性

- **智能对话**：基于AI模型的自然语言处理和对话生成
- **情绪管理**：实现了情绪状态服务，支持角色情感表达
- **记忆系统**：使用Chroma DB进行向量存储，支持长期记忆和上下文理解
- **工具集成**：支持调用外部工具（如当前时间查询）
- **模块化设计**：清晰的代码结构，便于扩展和维护
- **数据库支持**：使用SQLite进行数据持久化

## 🛠️ 技术栈

- **Python**：主要开发语言
- **FastAPI**：Web框架（推测，基于常见后端架构）
- **SQLite**：关系型数据库
- **Chroma DB**：向量数据库
- **Xorbits**：中文嵌入模型，用于向量化记忆（bge-small-zh-v1.5）
- **情绪状态服务**：独立的情绪管理模块

## 📦 安装步骤

### 1. 克隆项目

```bash
git clone <repository-url>
cd super_chizuko_backend
```

### 2. 安装依赖

```bash
pip install -r requirements.txt
```

### 3. 安装情绪状态服务依赖

```bash
cd emotion_state_serv
pip install -r requirements.txt
cd ..
```

### 4. 下载AI模型

```bash
python download_model.py
```

### 5. 初始化数据库

```bash
python init_data.py
```

## 🚀 运行项目

### 1. 启动情绪状态服务

```bash
cd emotion_state_serv
python emo_serv_http.py
```

### 2. 启动主应用

```bash
python app.py
```

## 📁 项目结构

```
super_chizuko_backend/
├── ai_manager.py          # AI模型管理
├── app.py                 # 主应用入口
├── chat_service.py        # 聊天服务
├── config.py              # 配置文件
├── database.py            # 数据库操作
├── download_model.py      # 模型下载脚本
├── email_service.py       # 邮件服务
├── emotion_state_serv/    # 情绪状态服务
│   ├── character_card.py  # 角色卡片管理
│   ├── emo_serv.py        # 情绪服务核心
│   ├── emo_serv_http.py   # 情绪服务HTTP接口
│   └── system_prompt_chizuko.txt  # 角色系统提示
├── init_data.py           # 数据初始化
├── memory_manager.py      # 记忆管理
├── prompt_generator.py    # 提示生成器
├── tools/                 # 工具目录
│   └── currentTimeTool.py # 当前时间查询工具
└── requirements.txt       # 项目依赖
```

## 🔧 主要组件说明

### AI管理器 (ai_manager.py)
管理AI模型的加载、推理和调用，是系统的核心智能组件。

### 聊天服务 (chat_service.py)
处理用户与AI的对话流程，包括消息接收、处理和响应生成。

### 记忆管理器 (memory_manager.py)
使用Chroma DB实现对话记忆的存储和检索，支持上下文理解和长期记忆。

### 情绪状态服务 (emotion_state_serv/)
独立的情绪管理模块，处理AI角色的情绪表达和状态变化。

### 提示生成器 (prompt_generator.py)
根据对话历史和上下文生成高质量的AI提示，提升对话质量。

## ⚙️ 配置说明

主要配置文件：`config.py`

配置项包括：
- AI模型参数
- 数据库连接
- 服务端口
- 情绪服务配置

## 📖 使用说明

### API接口

项目启动后，可通过以下主要接口与系统交互：

- **POST /chat**：发送聊天消息
- **GET /memory**：获取记忆信息
- **POST /emotion**：设置情绪状态

### 工具调用

系统支持调用工具，例如：
```json
{
  "tool_call": {
    "name": "currentTimeTool",
    "params": {}
  }
}
```

## 🤝 贡献指南

1. Fork项目
2. 创建功能分支 (`git checkout -b feature/AmazingFeature`)
3. 提交更改 (`git commit -m 'Add some AmazingFeature'`)
4. 推送到分支 (`git push origin feature/AmazingFeature`)
5. 开启Pull Request

## 📄 许可证

MIT License


---
