import time
import datetime
import os
import threading
import traceback
from config import Config
os.environ["ANONYMIZED_TELEMETRY"]="False"
class Memory:
    """记忆类"""
    def __init__(self, memory_id, content, timestamp, state, memory_type="conversation", category="general", tags=None, sentiment="neutral", priority="medium", importance=0.5, access_count=0, last_accessed=None):
        self.memory_id = memory_id
        self.content = content
        self.timestamp = timestamp
        self.state = state
        self.memory_type = memory_type  # 记忆类型：conversation, fact, preference, context, user_profile, system_setting
        self.category = category  # 记忆分类：general, personal, professional, emotional等
        self.tags = tags if tags else []  # 记忆标签：支持多个标签
        self.sentiment = sentiment  # 情感分析结果：positive, negative, neutral
        self.priority = priority  # 优先级：high, medium, low
        self.importance = importance  # 重要性：0-1之间的数值
        self.access_count = access_count  # 访问次数
        self.last_accessed = last_accessed if last_accessed else timestamp  # 最后访问时间

    def is_expired(self):
        """检查记忆是否过期"""
        current_time = time.time()
        time_since_created = current_time - self.timestamp
        time_since_accessed = current_time - self.last_accessed
        
        # 基于记忆类型的过期基础时间
        type_expiry_base = Config.MEMORY_TYPE_CONFIG.get(
            self.memory_type, 
            {"expiry_time": Config.MEMORY_EXPIRY_TIME}
        )["expiry_time"]
        
        # 基于多因素的过期逻辑
        # 1. 优先级越高，过期时间越长
        priority_multiplier = {
            "high": 3,
            "medium": 1,
            "low": 0.3
        }[self.priority]
        
        # 2. 重要性越高，过期时间越长
        importance_multiplier = 0.5 + self.importance * 1.5
        
        # 3. 访问频率越高，过期时间越长
        access_multiplier = 0.5 + min(self.access_count / 10, 1.5)
        
        # 4. 最后访问时间越近，过期时间越长
        recency_multiplier = max(0.5, 2 - time_since_accessed / (type_expiry_base / 2))
        
        # 计算动态过期时间
        dynamic_expiry_time = type_expiry_base * priority_multiplier * importance_multiplier * access_multiplier * recency_multiplier
        
        return time_since_created > dynamic_expiry_time
        
    def update_access(self):
        """更新记忆的访问信息"""
        self.access_count += 1
        self.last_accessed = time.time()
        
    def to_dict(self):
        """转换为字典格式，用于存储"""
        return {
            "memory_id": self.memory_id,
            "content": self.content,
            "timestamp": self.timestamp,
            "state": self.state,
            "memory_type": self.memory_type,
            "category": self.category,
            "tags": self.tags,
            "sentiment": self.sentiment,
            "priority": self.priority,
            "importance": self.importance,
            "access_count": self.access_count,
            "last_accessed": self.last_accessed
        }

class MemoryManager:
    """记忆管理器"""
    def __init__(self, chroma_client, embedding_model, collection_name=None):
        self.chroma_client = chroma_client
        self.embedding_model = embedding_model
        self.collection_name = collection_name
        self.embedding_dim = self._get_embedding_dim()
        self.collection = self._get_or_create_collection()
        self.memory_lock = threading.Lock()  # 添加线程锁，确保并发安全
    
    def _get_embedding_dim(self):
        try:
            if self.embedding_model and hasattr(self.embedding_model, 'get_sentence_embedding_dimension'):
                return int(self.embedding_model.get_sentence_embedding_dimension())
            if self.embedding_model:
                return len(self.embedding_model.encode('test'))
        except Exception:
            pass
        return 256

    def _get_or_create_collection(self):
        """获取或创建Chroma集合"""
        if self.collection_name:
            actual_name = f"{self.collection_name}__d{self.embedding_dim}"
            return self.chroma_client.get_or_create_collection(name=actual_name)
        return None
    
    def set_collection_by_name(self, collection_name):
        """根据名称设置当前集合"""
        with self.memory_lock:
            self.collection_name = collection_name
            self.embedding_dim = self._get_embedding_dim()
            self.collection = self._get_or_create_collection()

    def _encode_text(self, text):
        """将文本编码为向量；当嵌入模型不可用时使用哈希降级方案"""
        if self.embedding_model:
            return self.embedding_model.encode(text).tolist()
        import mmh3
        import math
        dim = 256
        vec = [0.0] * dim
        tokens = [t for t in text.split() if t]
        for tok in tokens:
            h = mmh3.hash(tok, signed=False) % dim
            vec[h] += 1.0
        norm = math.sqrt(sum(v*v for v in vec)) or 1.0
        return [v / norm for v in vec]
    
    def _generate_tags_from_content(self, user_msg, assistant_msg, state):
        """从对话内容中生成标签"""
        tags = []
        
        # 基础标签：情感状态
        if state:
            tags.append(f"state_{state}")
        
        # 从用户消息中提取关键词
        if user_msg:
            # 简单的关键词提取（可以根据需求扩展）
            keywords = ["时间", "睡觉", "购买", "限定", "哥哥", "妹妹", "晚安", "早上", "晚上"]
            for keyword in keywords:
                if keyword in user_msg:
                    tags.append(keyword)
        
        # 从助手回复中提取关键词
        if assistant_msg:
            keywords = ["蜂黄泉", "限定", "购买", "一起", "玩"]
            for keyword in keywords:
                if keyword in assistant_msg:
                    tags.append(keyword)
        
        # 去重
        return list(set(tags))
    
    def add_memory(self, user_msg, assistant_msg, state, memory_type="conversation", category="general", tags=None, sentiment="neutral", priority="medium", importance=0.5):
        """添加聊天记忆到向量数据库"""
        if not self.collection:
            print("未设置记忆集合，无法添加记忆")
            return
        
        with self.memory_lock:  # 加锁保护，确保并发安全
            # 确保所有参数都是正确的类型，特别是会存储在元数据中的参数
            user_msg_str = str(user_msg) if user_msg is not None else ""
            assistant_msg_str = str(assistant_msg) if assistant_msg is not None else ""
            state_str = str(state) if state is not None else "idle"
            memory_type_str = str(memory_type) if memory_type is not None else "conversation"
            category_str = str(category) if category is not None else "general"
            sentiment_str = str(sentiment) if sentiment is not None else "neutral"
            priority_str = str(priority) if priority is not None else "medium"
            
            memory_content = f"用户: {user_msg_str}\n智子: {assistant_msg_str}\n状态: {state_str}"
            embedding = self._encode_text(memory_content)
            memory_id = f"memory_{datetime.datetime.now().timestamp()}"
            current_time = time.time()
            
            # 如果未提供标签，则自动从对话内容生成
            if tags is None:
                tags = self._generate_tags_from_content(user_msg_str, assistant_msg_str, state_str)
            
            # 确保tags是列表类型
            if tags is None:
                tags = []
            elif not isinstance(tags, list):
                tags = [str(tag) for tag in tags if tag is not None]
            else:
                tags = [str(tag) for tag in tags if tag is not None]
            
            self.collection.add(
                ids=[memory_id],
                documents=[memory_content],
                embeddings=[embedding],
                metadatas=[{
                    "timestamp": datetime.datetime.now().isoformat(),
                    "user_msg": user_msg_str,
                    "assistant_msg": assistant_msg_str,
                    "state": state_str,
                    "memory_type": memory_type_str,
                    "category": category_str,
                    "tags": ",".join(tags),
                    "sentiment": sentiment_str,
                    "priority": priority_str,
                    "importance": importance if isinstance(importance, (int, float)) else 0.5,
                    "access_count": 0,
                    "last_accessed": datetime.datetime.fromtimestamp(current_time).isoformat()
                }]
            )
            print(f"已存储记忆: {user_msg_str} -> {assistant_msg_str}...")

    def retrieve_relevant_memories(self, query, n_results=Config.RELEVANT_MEMORIES_COUNT):
        """检索与当前查询相关的记忆"""
        if not self.collection:
            return {"documents": [[]], "metadatas": [[]]}
        
        with self.memory_lock:  # 加锁保护，确保并发安全
            query_embedding = self._encode_text(query)
            results = self.collection.query(query_embeddings=[query_embedding], n_results=n_results)
            
            # 处理检索结果，更新访问计数并优化记忆拼接
            if results and results.get('ids') and results['ids']:
                updated_memories = []
                for i, memory_id in enumerate(results['ids'][0]):
                    metadata = results['metadatas'][0][i] if results.get('metadatas') and results['metadatas'] else {}
                    content = results['documents'][0][i] if results.get('documents') and results['documents'] else ""
                    
                    # 创建记忆对象并更新访问信息
                    memory = Memory(
                        memory_id=memory_id,
                        content=content,
                        timestamp=datetime.datetime.fromisoformat(metadata.get('timestamp', datetime.datetime.now().isoformat())).timestamp() if metadata.get('timestamp') else time.time(),
                        state=metadata.get('state', 'idle'),
                        memory_type=metadata.get('memory_type', 'conversation'),
                        category=metadata.get('category', 'general'),
                        tags=metadata.get('tags', "").split(",") if metadata.get('tags') else [],
                        sentiment=metadata.get('sentiment', 'neutral'),
                        priority=metadata.get('priority', 'medium'),
                        importance=metadata.get('importance', 0.5),
                        access_count=metadata.get('access_count', 0),
                        last_accessed=datetime.datetime.fromisoformat(metadata.get('last_accessed', datetime.datetime.now().isoformat())).timestamp() if metadata.get('last_accessed') else time.time()
                    )
                    
                    # 更新访问信息
                    memory.update_access()
                    
                    # 更新到数据库
                    self.collection.update(
                        ids=[memory_id],
                        metadatas=[{
                            "access_count": memory.access_count,
                            "last_accessed": datetime.datetime.fromtimestamp(memory.last_accessed).isoformat()
                        }]
                    )
                    
                    updated_memories.append((memory, results['distances'][0][i] if results.get('distances') and results['distances'] else 0))
                
                # 基于相关性、优先级和重要性重新排序记忆
                updated_memories.sort(key=lambda x: (x[1], -{
                    "high": 3,
                    "medium": 2,
                    "low": 1
                }[x[0].priority], -x[0].importance))
                
                # 重新组织结果，确保上下文连贯
                sorted_results = {
                    "ids": [[memory[0].memory_id for memory in updated_memories]],
                    "documents": [[memory[0].content for memory in updated_memories]],
                    "metadatas": [[{
                        "timestamp": datetime.datetime.fromtimestamp(memory[0].timestamp).isoformat(),
                        "user_msg": memory[0].content.split("\n")[0].replace("用户: ", ""),
                        "assistant_msg": memory[0].content.split("\n")[1].replace("智子: ", ""),
                        "state": memory[0].state,
                        "memory_type": memory[0].memory_type,
                        "category": memory[0].category,
                        "tags": memory[0].tags,
                        "sentiment": memory[0].sentiment,
                        "priority": memory[0].priority,
                        "importance": memory[0].importance,
                        "access_count": memory[0].access_count,
                        "last_accessed": datetime.datetime.fromtimestamp(memory[0].last_accessed).isoformat()
                    } for memory in updated_memories]],
                    "distances": [[memory[1] for memory in updated_memories]]
                }
                
                return sorted_results
            
            return results
    
    def check_memory_relevance(self, memory, current_state):
        """检查记忆是否仍然相关"""
        # 1. 检查记忆是否过期
        if memory.is_expired():
            return False  # 记忆已过期

        # 2. 基于优先级的保留策略：高优先级记忆更容易保留
        priority_weight = Config.PRIORITY_WEIGHTS[memory.priority]
        
        # 3. 基于重要性的保留策略：重要性越高越容易保留
        importance_weight = memory.importance
        
        # 4. 基于访问频率的保留策略：访问频率越高越容易保留
        access_weight = min(memory.access_count / 20, 1.0)
        
        # 5. 基于状态相关性的判断：允许状态不完全匹配
        # 状态相关性：如果状态相同，相关性为1.0；否则根据具体情况调整
        state_relevance = 1.0 if memory.state == current_state else 0.5
        
        # 6. 基于情感标签的过滤：根据情感调整相关性
        sentiment_adjustment = Config.SENTIMENT_ADJUSTMENT.get(
            memory.sentiment, 
            1.0  # 默认不调整
        )
        
        # 7. 基于记忆类型的权重调整
        type_weight = Config.MEMORY_TYPE_CONFIG.get(
            memory.memory_type, 
            {"weight": 1.0}  # 默认权重
        )["weight"]
        
        # 8. 综合得分计算
        base_score = (priority_weight * 0.3 + 
                     importance_weight * Config.IMPORTANCE_WEIGHT + 
                     access_weight * Config.ACCESS_COUNT_WEIGHT + 
                     state_relevance * Config.STATE_RELEVANCE_WEIGHT)
        
        # 应用情感和类型调整
        relevance_score = base_score * sentiment_adjustment * type_weight
        
        # 9. 基于阈值的判断
        return relevance_score > Config.MEMORY_RELEVANCE_THRESHOLD  # 相关性得分超过阈值则保留记忆
    
    def clean_up_memory(self, current_state=Config.DEFAULT_CLEANUP_STATE):
        """定期清理不相关或过期的记忆"""
        if not self.collection:
            return
            
        with self.memory_lock:  # 加锁保护，确保并发安全
            try:
                all_memories = self.collection.get()
                if all_memories and all_memories.get('ids'):
                    for i, memory_id in enumerate(all_memories['ids']):
                        metadata = all_memories['metadatas'][i] if all_memories.get('metadatas') else {}
                        # 创建临时内存对象用于检查
                        temp_memory = Memory(
                            memory_id=memory_id,
                            content=all_memories['documents'][i] if all_memories.get('documents') else "",
                            timestamp=datetime.datetime.fromisoformat(metadata.get('timestamp', datetime.datetime.now().isoformat())).timestamp() if metadata.get('timestamp') else time.time(),
                            state=metadata.get('state', 'idle'),
                            memory_type=metadata.get('memory_type', 'conversation'),
                            category=metadata.get('category', 'general'),
                            tags=metadata.get('tags', "").split(",") if metadata.get('tags') else [],
                            sentiment=metadata.get('sentiment', 'neutral'),
                            priority=metadata.get('priority', 'medium'),
                            importance=metadata.get('importance', 0.5),
                            access_count=metadata.get('access_count', 0),
                            last_accessed=datetime.datetime.fromisoformat(metadata.get('last_accessed', datetime.datetime.now().isoformat())).timestamp() if metadata.get('last_accessed') else time.time()
                        )
                        
                        if not self.check_memory_relevance(temp_memory, current_state):
                            self.collection.delete(ids=[memory_id])
                            print(f"删除记忆: {memory_id}")
            except Exception as e:
                print(f"清理记忆时出错: {e}")
                print(traceback.format_exc())
    
    def clear_all_memories(self):
        """清空当前集合中的所有记忆"""
        if not self.collection:
            print("未设置记忆集合，无法清空记忆")
            return
            
        with self.memory_lock:  # 加锁保护，确保并发安全
            try:
                # 获取所有记忆的ID
                all_memories = self.collection.get()
                if all_memories and all_memories.get('ids'):
                    # 批量删除所有记忆
                    self.collection.delete(ids=all_memories['ids'])
                    print(f"已清空所有记忆，共删除 {len(all_memories['ids'])} 条记录")
                else:
                    print("记忆集合为空，无需清空")
            except Exception as e:
                print(f"清空记忆时出错: {e}")
                print(traceback.format_exc())

    def has_any_memory(self):
        """检查当前集合是否有任何记忆"""
        if not self.collection:
            return False
        with self.memory_lock:
            all_memories = self.collection.get()
            return bool(all_memories and all_memories.get('ids'))
