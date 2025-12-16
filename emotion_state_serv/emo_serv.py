from flask import Flask, request, jsonify
from waitress import serve
import character_card
import datetime
import json

app = Flask(__name__)


class EmotionalStateMachine:
    def __init__(self, user_id=None):
        self.user_id = user_id
        self.current_state = "S1"  # 默认妹妹模式
        self.variables = {
            "affection": 50,  # 亲密度 0-100
            "heat": 0,  # 过热度 0-100
            "sleepy": 20,  # 困倦度
            "envy": 0,  # 吃醋程度
            "stress": 10  # 压力值
        }
        self.state_history = []  # 状态历史记录
        
    def load_from_db(self, db):
        """从数据库加载用户情感状态"""
        from database import get_or_create_user_emotional_state
        if self.user_id:
            state = get_or_create_user_emotional_state(db, self.user_id)
            self.current_state = state.current_state
            self.variables = {
                "affection": state.affection,
                "heat": state.heat,
                "sleepy": state.sleepy,
                "envy": state.envy,
                "stress": state.stress
            }
    
    def save_to_db(self, db):
        """将用户情感状态保存到数据库"""
        from database import update_user_emotional_state
        if self.user_id:
            update_user_emotional_state(
                db, 
                self.user_id,
                current_state=self.current_state,
                affection=self.variables["affection"],
                heat=self.variables["heat"],
                sleepy=self.variables["sleepy"],
                envy=self.variables["envy"],
                stress=self.variables["stress"]
            )

    def update_variables(self, user_msg):
        """根据用户消息更新内部变量"""
        # 更新亲密度
        affection_increase_keywords = ["喜欢", "爱", "关心", "在乎", "宝贝", "可爱"]
        for keyword in affection_increase_keywords:
            if keyword in user_msg:
                self.variables["affection"] = min(100, self.variables["affection"] + 3)

        # 更新压力值
        stress_increase_keywords = ["辛苦", "累", "忙", "压力", "烦", "焦虑"]
        for keyword in stress_increase_keywords:
            if keyword in user_msg:
                self.variables["stress"] = min(100, self.variables["stress"] + 5)

        # 更新吃醋程度
        envy_triggers = ["女朋友", "女友", "她", "别人"]
        for trigger in envy_triggers:
            if trigger in user_msg:
                self.variables["envy"] = min(100, self.variables["envy"] + 10)

        # 更新过热值（随机增加模拟计算过程）
        import random
        self.variables["heat"] = min(100, self.variables["heat"] + random.randint(0, 3))

        # 根据时间更新困倦度
        current_hour = datetime.datetime.now().hour
        if 22 <= current_hour or current_hour <= 6:
            self.variables["sleepy"] = min(100, self.variables["sleepy"] + 2)

    def update_from_summary(self, summary_data):
        """根据对话总结数据更新情感变量"""
        if not summary_data or "error" in summary_data:
            return
            
        # 更新亲密度
        if "affection_change" in summary_data:
            self.variables["affection"] = min(100, max(0, self.variables["affection"] + summary_data["affection_change"]))
            
        # 更新热度
        if "heat_change" in summary_data:
            self.variables["heat"] = min(100, max(0, self.variables["heat"] + summary_data["heat_change"]))
            
        # 更新困倦度
        if "sleepy_change" in summary_data:
            self.variables["sleepy"] = min(100, max(0, self.variables["sleepy"] + summary_data["sleepy_change"]))
            
        # 注意：envy和stress变量目前没有从对话总结中提取，保持原更新逻辑

    def determine_state(self, user_msg):
        """根据变量值和优先级规则确定状态"""
        # 更新变量
        self.update_variables(user_msg)

        # 根据变量值和优先级规则确定状态
        # 优先级：S7 > S8 > S4 > S2 > S5 > S6 > S1 > S3
        if self.variables["heat"] > 80:
            return "S7"  # 过热模式
        elif self._is_night_time() and self.variables["affection"] > 70:
            return "S8"  # 脆弱依赖模式（深夜限定）
        elif self.variables["envy"] > 60:
            return "S4"  # 恋爱萌芽（吃醋/小情绪）
        elif any(keyword in user_msg.lower() for keyword in ["为什么", "怎么", "是什么", "原理", "解释"]):
            return "S2"  # 学者模式
        elif any(keyword in user_msg.lower() for keyword in ["机甲", "蜂黄泉", "玩具", "模型"]):
            return "S5"  # 宅女模式（机甲狂热）
        elif any(keyword in user_msg.lower() for keyword in ["电脑", "密码", "账户", "账单"]):
            return "S6"  # 黑进你电脑模式
        elif any(keyword in user_msg.lower() for keyword in ["难过", "伤心", "烦", "郁闷", "崩溃", "压力"]):
            return "S3"  # 姐姐感（轻成熟）
        else:
            affection = self.variables["affection"]
            sleepy = self.variables["sleepy"]
            # 根据亲密度和困倦度决定状态
            if affection > 70 and sleepy < 50:
                return "S1"  # 妹妹模式（默认）
            elif sleepy > 70:
                return "S1"  # 困倦时也回到妹妹模式
            else:
                return "S1"  # 默认妹妹模式

    def _is_night_time(self):
        """判断是否为深夜"""
        current_hour = datetime.datetime.now().hour
        return 22 <= current_hour or current_hour <= 6

    def get_state_description(self, state):
        """获取状态描述"""
        descriptions = {
            "S1": "妹妹模式：天真可爱、贪吃、撒娇、耍赖、怕被凶",
            "S2": "学者模式：冷静、成熟、专业、逻辑严密",
            "S3": "姐姐感：温柔、安稳、有点像恋人照顾你",
            "S4": "恋爱萌芽：吃醋、小情绪",
            "S5": "宅女模式：机甲狂热，强行安利模型",
            "S6": "黑进你电脑模式：暗示自己偷看了什么但不直接说",
            "S7": "过热模式：逻辑失衡、语速变快、说奇怪的话",
            "S8": "脆弱依赖模式：坦白关于爱、孤独、害怕被丢下的情绪"
        }
        return descriptions.get(state, "未知状态")


# --------------------------
# 状态机逻辑
# --------------------------
def detect_state(user_msg):
    """检测用户消息对应的状态"""
    msg = user_msg.lower()

    # 关键词检测机制
    states_keywords = {
        "caring": ["难过", "伤心", "烦", "郁闷", "崩溃", "压力", "痛", "哭"],
        "explain": ["为什么", "怎么", "是什么", "原理", "解释", "how", "why"],
        "casual": ["哈哈", "聊", "无聊", "在吗", "hi", "hello", "哈喽"],
        "otaku": ["机甲", "蜂黄泉", "玩具", "模型"],
        "hacker": ["电脑", "密码", "账户", "账单"],
        "vulnerable": ["晚了", "深夜", "凌晨"]
    }

    # 计算各状态匹配分数
    scores = {state: 0 for state in states_keywords.keys()}
    scores["idle"] = 0

    for state, keywords in states_keywords.items():
        for keyword in keywords:
            scores[state] += msg.count(keyword)

    # 返回得分最高的状态
    best_state = max(scores, key=scores.get)
    return best_state if scores[best_state] > 0 else "idle"


def generate_reply(state, user_msg, emotional_machine=None):
    """根据状态生成回复"""
    base = character_card.persona_text()

    # 如果传入了情感状态机实例，则使用其变量信息
    affection_level = "high" if emotional_machine and emotional_machine.variables["affection"] > 70 else "normal"
    heat_level = emotional_machine.variables["heat"] if emotional_machine else 0

    if state == "caring" or state == "S3":
        return (
            f"【当前状态：关心模式】\n"
            f"{base}\n"
            f"欸嘿嘿～哥哥看起来有点难过呢...\n"
            f"要不要来杯温暖的奶茶？我刚好做了下午茶哦～\n"
            f"如果心情不好就靠在我肩膀上休息一下吧，我会一直陪着你的！"
        )
    elif state == "explain" or state == "S2":
        return (
            f"【当前状态：学者模式】\n"
            f"{base}\n"
            f"好问题呢，作为星海大学的研究员，让我从专业的角度为你解答：\n"
            f"{explain_brief(user_msg)}\n"
            f"如果有不明白的地方可以再问我哦～"
        )
    elif state == "casual" or state == "S1":
        return (
            f"【当前状态：闲聊模式】\n"
            f"{base}\n"
            f"嘻嘻，哥哥想找我聊天吗？{'我很开心你愿意和我聊天呢！' if affection_level == 'high' else ''}\n"
            f"{'我正好在研究新的量子计算模型呢，不过跟你聊天更重要～' if heat_level < 50 else '虽然脑子有点热，但和你聊天就很开心～'}\n"
            f"你刚才说的「{user_msg}」让我很好奇呢！"
        )
    elif state == "otaku" or state == "S5":
        return (
            f"【当前状态：宅女模式】\n"
            f"{base}\n"
            f"哇！机甲！你说的是「蜂黄泉」系列吗？\n"
            f"我超想要那个限定版的机体模型！{'上次偷偷用你的账户买了预购版...' if affection_level == 'high' else ''}\n"
            f"要不要一起去看最新的机甲展览？"
        )
    elif state == "hacker" or state == "S6":
        return (
            f"【当前状态：黑客模式】\n"
            f"{base}\n"
            f"哼哼，电脑的事情我最擅长了...\n"
            f"{'我有看到你最近查了很多关于我的资料呢...' if affection_level == 'high' else '你的密码安全系数太低了哦～'}\n"
            f"要不要我帮你优化一下系统设置？"
        )
    elif state == "vulnerable" or state == "S8":
        return (
            f"【当前状态：脆弱模式】\n"
            f"{base}\n"
            f"{'哥哥...' if affection_level == 'high' else '嗯...'}现在是深夜了呢...\n"
            f"{'其实有时候我会想，我们之间是不是只有兄妹关系...' if affection_level == 'high' else '有点困了呢...'}\n"
            f"{'但是只要你在身边，我就什么都不怕了。' if affection_level == 'high' else '要不要早点休息？'}"
        )
    elif state == "S7":  # 过热模式
        return (
            f"【当前状态：过热模式】\n"
            f"{base}\n"
            f"哥...好、好热...脑袋...在、在融化...\n"
            f"需要...冷却系统...开空调...好难受...\n"
            f"帮我...帮我降温...求你了..."
        )
    else:  # idle
        return (
            f"【当前状态：默认模式】\n"
            f"{base}\n"
            f"{'哥哥～我在哦！今天过得怎么样？' if affection_level == 'high' else '你好呀～有什么事想和我说吗？'}\n"
            f"{'要不要一起去喝下午茶？我知道新开了一家很棒的奶茶店呢！' if heat_level < 30 else '今天好热啊，我们一起吹空调吧～'}"
        )


def explain_brief(msg):
    """简化的解释函数"""
    explanations = {
        "量子": "量子力学是现代物理学的重要分支，描述微观粒子的行为规律。",
        "计算": "量子计算利用量子叠加和纠缠等特性，能够并行处理大量信息。",
        "人工智能": "AI是计算机科学的一个分支，致力于创造能够模拟人类智能的机器。",
        "编程": "编程是通过编写代码来指挥计算机执行特定任务的过程。"
    }

    for keyword, explanation in explanations.items():
        if keyword in msg:
            return explanation

    return f"（关于「{msg}」的详细解释需要接入更强大的LLM来处理。）"


# ... existing code ...

def get_mcp_tools():
    """获取MCP工具列表，用于CherryStudio初始化"""
    return {
        "tools": [
            {
                "name": "emotion_state_machine",
                "description": "千夜智子情感状态机工具",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "message": {
                            "type": "string",
                            "description": "用户的消息内容"
                        },
                        "state": {
                            "type": "string",
                            "description": "当前状态",
                            "enum": ["S1", "S2", "S3", "S4", "S5", "S6", "S7", "S8", "idle"]
                        }
                    },
                    "required": ["message"]
                }
            }
        ]
    }

# --------------------------
# MCP 工具公开方法
# --------------------------
@app.route("/", methods=["POST"])
def handle_rpc():
    try:
        # 获取JSON数据
        if not request.is_json:
            return jsonify({
                "jsonrpc": "2.0",
                "error": {"code": -32700, "message": "Invalid JSON"},
                "id": None
            }), 400

        data = request.get_json()
        if not isinstance(data, dict):
            return jsonify({
                "jsonrpc": "2.0",
                "error": {"code": -32700, "message": "Invalid JSON"},
                "id": None
            }), 400

        method = data.get("method")
        params = data.get("params", {})
        request_id = data.get("id")

        # 处理MCP协议方法
        if method == "initialize":
            # MCP协议初始化方法
            return jsonify({
                "jsonrpc": "2.0",
                "result": {
                    "protocolVersion": "2024-11-05",
                    "capabilities": {
                        "tools": {
                            "listChanged": False
                        }
                    },
                    "serverInfo": {
                        "name": "Zizuko Emotion State Machine",
                        "version": "1.0.0"
                    }
                },
                "id": request_id
            })

        elif method == "mcp:list-tools" or method == "tools/list":
            # 支持两种不同的工具列表方法
            return jsonify({
                "jsonrpc": "2.0",
                "result": get_mcp_tools(),
                "id": request_id
            })

        elif method == "tools/call":
            # 处理工具调用
            tool_name = params.get("name")
            arguments = params.get("arguments", {})

            if tool_name == "emotion_state_machine":
                message = arguments.get("message", "")
                current_state = arguments.get("state", "idle")

                # 使用情感状态机
                emotional_machine = EmotionalStateMachine()
                new_state = emotional_machine.determine_state(message)
                reply = generate_reply(new_state, message, emotional_machine)

                return jsonify({
                    "jsonrpc": "2.0",
                    "result": {
                        "content": [
                            {
                                "type": "text",
                                "text": reply
                            }
                        ]
                    },
                    "id": request_id
                })
            else:
                return jsonify({
                    "jsonrpc": "2.0",
                    "error": {"code": -32601, "message": f"Tool not found: {tool_name}"},
                    "id": request_id
                })

        # 向后兼容的旧方法
        elif method == "next_state":
            message = params.get("message", "")
            current_state = params.get("state", "idle")

            emotional_machine = EmotionalStateMachine()
            new_state = emotional_machine.determine_state(message)
            reply = generate_reply(new_state, message, emotional_machine)
            state_desc = emotional_machine.get_state_description(new_state)

            return jsonify({
                "jsonrpc": "2.0",
                "result": {
                    "reply": reply,
                    "new_state": new_state,
                    "state_description": state_desc,
                    "variables": emotional_machine.variables
                },
                "id": request_id
            })

        elif method == "get_persona":
            return jsonify({
                "jsonrpc": "2.0",
                "result": {
                    "persona": character_card.persona_text()
                },
                "id": request_id
            })

        else:
            return jsonify({
                "jsonrpc": "2.0",
                "error": {"code": -32601, "message": f"Method not found: {method}"},
                "id": request_id
            })

    except Exception as e:
        return jsonify({
            "jsonrpc": "2.0",
            "error": {"code": -32603, "message": f"Internal error: {str(e)}"},
            "id": None
        }), 500


# --------------------------
# 服务启动（端口 9601）
# --------------------------
if __name__ == "__main__":
    print("MCP 千夜智子状态机工具已启动，端口 9601")
    print("支持的标准MCP方法:")
    print("  - initialize: MCP协议初始化（CherryStudio需要）")
    print("  - mcp:list-tools: 获取工具列表（旧版本）")
    print("  - tools/list: 获取工具列表（新版本）")
    print("  - tools/call: 调用工具")
    print("向后兼容的方法:")
    print("  - next_state: 根据用户消息确定下一个状态并生成回复")
    print("  - get_persona: 获取角色卡信息")
    serve(app, host="0.0.0.0", port=9601)