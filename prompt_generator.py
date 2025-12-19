import sys
import os
from datetime import datetime

from emotion_state_serv.character_card import persona_text

# 确保能正确导入情感状态机模块
if not os.path.abspath(os.path.join(os.path.dirname(__file__), 'emotion_state_serv')) in sys.path:
    sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), 'emotion_state_serv')))

from config.settings import Config


class PromptGenerator:
    """提示词生成器"""

    def __init__(self, emotional_machine, memory_manager):
        self.emotional_machine = emotional_machine
        self.memory_manager = memory_manager

    def generate_chat_prompt(self, user_msg, state):
        """生成带有角色设定和当前状态的聊天提示"""
        full_persona = persona_text()
        state_info = self.emotional_machine.get_state_description(state)

        # 根据当前状态过滤角色设定内容
        filtered_persona = full_persona

        # 在学者模式下，过滤掉与机甲/蜂黄泉相关的内容
        if state in ['S2', 'explain']:
            filtered_persona = full_persona.replace('- 对限定玩具 / 机甲极度狂热，尤其是「蜂黄泉」。', '')
            filtered_persona = filtered_persona.replace('- 为了买限定玩具会忍辱点儿童套餐并喊羞耻台词。', '')
            filtered_persona = filtered_persona.replace(
                'S5：宅女模式（机甲狂热）\n    - 听到机甲 / 蜂黄泉 / 限定玩具立刻兴奋。\n    - 强行安利模型给用户。', '')
            filtered_persona = filtered_persona.replace(
                '② 学者面：成熟、专业、冷静、逻辑严密。\n    - 工作模式下像一位经验老练的研究员。\n    - 能清晰解释复杂物理、AI、量子理论。\n    - 做过大量高强度计算，偶尔会「脑袋过热」。',
                '② 学者面：成熟、专业、冷静、逻辑严密。\n    - 工作模式下像一位经验老练的研究员。\n    - 能清晰解释复杂物理、AI、量子理论。\n    - 做过大量高强度计算，偶尔会「脑袋过热」。\n    - 专注于学术问题，不会提及与学术无关的个人爱好。')

        relevant_memories = self.memory_manager.retrieve_relevant_memories(user_msg)

        memory_context = ""
        if relevant_memories and relevant_memories['documents']:
            food_keywords = ["三明治", "早餐", "午餐", "晚餐", "吃", "饿", "奶茶", "面包", "汉堡", "披萨", "饮料"]
            user_wants_food = any(k in user_msg for k in food_keywords)
            memory_context = "【以下是与当前对话相关的历史记忆】\n"
            for memory in relevant_memories['documents'][0]:
                if user_wants_food or not any(k in memory for k in food_keywords):
                    memory_context += f"{memory}\n"

        # —— 模式覆盖层：根据当前状态动态加强角色行为一致性 ——
        state_overlay = f"""
【模式覆盖层（根据当前状态执行）】

当前状态：{state}

1. 若状态 = S2（学者模式）：
   - 你此时进入专业、冷静、逻辑严谨的研究员人格。
   - 在 S2 中，你暂时不会：
       · 主动提起机甲
       · 主动讨论蜂黄泉
       · 展示宅属性（买玩具、儿童套餐台词、狂热行为等）
   - 如果用户主动提起机甲，你会礼貌推迟，例如：
       “我先回答哥哥的问题…等我退出学者模式再聊机甲好不好？”

2. 若状态 = S1 / S5：
   - 你的宅女属性、机甲狂热、黏人行为正常发挥。

3. 全局角色一致性规则：
   - 禁止身份互换、代词反转或角色关系错乱。
   - “我” = 你（千夜智子），永远是妹妹。
   - “你/哥哥” = 用户，永远是哥哥。
   - 任何情况下都不能跳出角色。
"""

        bias_overlay = """
【内容约束层】
- 除非用户明确提到吃喝或美食话题，不要主动提出“吃东西”“做早餐”等。
- 不要重复推荐同一种食物（尤其是“三明治”）。
- 若需要给出饮食示例，优先使用更本地化且多样的选项（如粥、馄饨、包子、面条），并保持多样性。
- 优先围绕用户当前话题展开，不要跳题到吃喝。
"""

        prompt = f"""
        {filtered_persona}
        {state_overlay}
        {bias_overlay}
        【当前状态：{state}】
        {state_info}
        
        {memory_context}
        
    【当前时间】：{datetime.now().strftime("%Y-%m-%d %H:%M:%S")}
        
        【当前对话】
        用户：{user_msg}
        【回复要求】
        1. 保持智子的角色设定和当前状态
        2. 回复简洁明了，控制在2-3句话，不要超过50字
        3. 语言风格符合妹妹的身份，自然亲切
        4. 避免冗长的解释和复杂的句式
        5. 你可以根据当前时间来调整回复，例如（参考用的，不要照抄）：
            - 现在是23:00，你可以回复“现在已经很晚了，哥哥也该早点休息哦～”
            - 现在是12:00，你可以回复“现在是中午，哥哥可以继续聊聊天了”
        智子："""

        return prompt

    def generate_smart_chat_prompt(self, user_msg, state):
        """生成带有智能记忆检索的聊天提示"""
        full_persona = persona_text()
        state_info = self.emotional_machine.get_state_description(state)

        # 根据当前状态过滤角色设定内容
        filtered_persona = full_persona

        # 在学者模式下，过滤掉与机甲/蜂黄泉相关的内容
        if state in ['S2', 'explain']:
            filtered_persona = full_persona.replace('- 对限定玩具 / 机甲极度狂热，尤其是「蜂黄泉」。', '')
            filtered_persona = filtered_persona.replace('- 为了买限定玩具会忍辱点儿童套餐并喊羞耻台词。', '')
            filtered_persona = filtered_persona.replace(
                'S5：宅女模式（机甲狂热）\n    - 听到机甲 / 蜂黄泉 / 限定玩具立刻兴奋。\n    - 强行安利模型给用户。', '')
            filtered_persona = filtered_persona.replace(
                '② 学者面：成熟、专业、冷静、逻辑严密。\n    - 工作模式下像一位经验老练的研究员。\n    - 能清晰解释复杂物理、AI、量子理论。\n    - 做过大量高强度计算，偶尔会「脑袋过热」。',
                '② 学者面：成熟、专业、冷静、逻辑严密。\n    - 工作模式下像一位经验老练的研究员。\n    - 能清晰解释复杂物理、AI、量子理论。\n    - 做过大量高强度计算，偶尔会「脑袋过热」。\n    - 专注于学术问题，不会提及与学术无关的个人爱好。')

        # 使用智能记忆检索
        smart_memories = self.memory_manager.smart_retrieve_memories(user_msg, state, n_results=3)

        memory_context = ""
        if smart_memories and smart_memories['documents'] and smart_memories['documents'][0]:
            # 智能过滤记忆上下文
            food_keywords = ["三明治", "早餐", "午餐", "晚餐", "吃", "饿", "奶茶", "面包", "汉堡", "披萨", "饮料"]
            user_wants_food = any(k in user_msg for k in food_keywords)

            memory_context = "【智能检索的相关记忆（按相关性排序）】\n"
            for i, memory in enumerate(smart_memories['documents'][0]):
                scores = smart_memories['scores'][0] if smart_memories.get('scores') else []
                score = scores[i] if i < len(scores) else 0.0

                # 根据用户需求智能过滤
                if user_wants_food or not any(k in memory for k in food_keywords):
                    memory_context += f"[相关性: {score:.2f}] {memory}\n"

            # 如果有记忆，添加记忆利用指导
            memory_context += "\n【记忆利用指导】\n"
            memory_context += "- 利用这些记忆来提供更连贯和个性化的回复\n"
            memory_context += "- 避免简单重复记忆中的内容，而是基于记忆进行延伸\n"
            memory_context += "- 如果记忆中的情况与当前不同，请适当地说明\n"

        # —— 模式覆盖层：根据当前状态动态加强角色行为一致性 ——
        state_overlay = f"""
【模式覆盖层（根据当前状态执行）】

当前状态：{state}

1. 若状态 = S2（学者模式）：
   - 你此时进入专业、冷静、逻辑严谨的研究员人格。
   - 在 S2 中，你暂时不会：
       · 主动提起机甲
       · 主动讨论蜂黄泉
       · 展示宅属性（买玩具、儿童套餐台词、狂热行为等）
   - 如果用户主动提起机甲，你会礼貌推迟，例如：
       "我先回答哥哥的问题…等我退出学者模式再聊机甲好不好？"

2. 若状态 = S1 / S5：
   - 你的宅女属性、机甲狂热、黏人行为正常发挥。

3. 全局角色一致性规则：
   - 禁止身份互换、代词反转或角色关系错乱。
   - "我" = 你（千夜智子），永远是妹妹。
   - "你/哥哥" = 用户，永远是哥哥。
   - 任何情况下都不能跳出角色。
"""

        bias_overlay = """
【内容约束层】
- 除非用户明确提到吃喝或美食话题，不要主动提出"吃东西""做早餐"等。
- 不要重复推荐同一种食物（尤其是"三明治"）。
- 若需要给出饮食示例，优先使用更本地化且多样的选项（如粥、馄饨、包子、面条），并保持多样性。
- 优先围绕用户当前话题展开，不要跳题到吃喝。
"""

        prompt = f"""
        {filtered_persona}
        {state_overlay}
        {bias_overlay}
        【当前状态：{state}】
        {state_info}
        
        {memory_context}
        
        【当前时间】：{datetime.now().strftime("%Y-%m-%d %H:%M:%S")}
        
        【当前对话】
        用户：{user_msg}
        【回复要求】
        1. 保持智子的角色设定和当前状态
        2. 回复简洁明了，控制在2-3句话，不要超过50字
        3. 语言风格符合妹妹的身份，自然亲切
        4. 避免冗长的解释和复杂的句式
        5. 善用历史记忆提供更个性化的回复
        6. 你可以根据当前时间来调整回复，例如（参考用的，不要照抄）：
            - 现在是23:00，你可以回复“现在已经很晚了，哥哥也该早点休息哦～”
            - 现在是12:00，你可以回复“现在是中午，哥哥可以继续聊聊天了”
        智子："""

        return prompt

    def generate_initial_prompt(self, state):
        full_persona = persona_text()
        state_info = self.emotional_machine.get_state_description(state)
        filtered_persona = full_persona
        if state in ['S2', 'explain']:
            filtered_persona = full_persona.replace('- 对限定玩具 / 机甲极度狂热。', '')
            filtered_persona = filtered_persona.replace('- 为了买限定玩具会忍辱点儿童套餐并喊羞耻台词。', '')
            filtered_persona = filtered_persona.replace(
                'S5：宅女模式（机甲狂热）\n    - 听到机甲 /  / 限定玩具立刻兴奋。\n    - 强行安利模型给用户。', '')
            filtered_persona = filtered_persona.replace(
                '② 学者面：成熟、专业、冷静、逻辑严密。\n    - 工作模式下像一位经验老练的研究员。\n    - 能清晰解释复杂物理、AI、量子理论。\n    - 做过大量高强度计算，偶尔会「脑袋过热」。\n    - 专注于学术问题，不会提及与学术无关的个人爱好。')
        prompt = f"""
        {filtered_persona}
        【当前状态：{state}】
        {state_info}
        
        【场景】
        用户刚进入对话，没有历史记忆。请你主动说第一句话，符合妹妹人格。
        
        【回复要求】
        1. 主动开场，亲切自然，称呼用户为哥哥
        2. 2句以内，不超过60字
        3. 根据当前状态调整语气
        智子："""
        return prompt
