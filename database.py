from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Boolean, create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, relationship
from datetime import datetime, timedelta
from config.settings import Config
import secrets
import re

# 创建SQLAlchemy引擎
engine = create_engine(Config.DATABASE_URL, echo=False)  # 设置echo=True可以看到SQL语句

# 创建会话工厂
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# 创建基类
Base = declarative_base()

class User(Base):
    """用户模型"""
    __tablename__ = "users"
    
    id = Column(Integer, primary_key=True, index=True)
    email = Column(String, unique=True, index=True, nullable=False)
    is_verified = Column(Boolean, default=False, nullable=False)  # 是否已验证
    verification_code = Column(String, nullable=True)  # 验证码
    verification_code_expires = Column(DateTime, nullable=True)  # 验证码过期时间
    failed_attempts = Column(Integer, default=0, nullable=False)  # 失败尝试次数
    last_attempt_time = Column(DateTime, nullable=True)  # 最后尝试时间
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # 关联用户的记忆集合
    memory_collections = relationship("MemoryCollection", back_populates="user")

class MemoryCollection(Base):
    """记忆集合模型，关联用户和Chroma集合"""
    __tablename__ = "memory_collections"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    collection_name = Column(String, unique=True, index=True, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # 关联用户
    user = relationship("User", back_populates="memory_collections")

class UserEmotionalState(Base):
    """用户情感状态模型，存储每个用户的情感状态"""
    __tablename__ = "user_emotional_states"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), unique=True, nullable=False)
    current_state = Column(String, default="S1", nullable=False)
    affection = Column(Integer, default=50, nullable=False)  # 亲密度 0-100
    heat = Column(Integer, default=0, nullable=False)  # 过热度 0-100
    sleepy = Column(Integer, default=20, nullable=False)  # 困倦度 0-100
    envy = Column(Integer, default=0, nullable=False)  # 吃醋程度 0-100
    stress = Column(Integer, default=10, nullable=False)  # 压力值 0-100
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # 关联用户
    user = relationship("User", backref="emotional_state")

class ChatHistory(Base):
    """聊天记录模型，存储用户的聊天记录"""
    __tablename__ = "chat_histories"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    user_message = Column(String, nullable=False)  # 用户消息
    assistant_message = Column(String, nullable=False)  # 助手回复
    state = Column(String, default="S1", nullable=False)  # 当时的情感状态
    created_at = Column(DateTime, default=datetime.utcnow)  # 创建时间
    
    # 关联用户
    user = relationship("User", backref="chat_histories")

# 创建数据库表
def init_db():
    """初始化数据库"""
    Base.metadata.create_all(bind=engine)

# 获取数据库会话
def get_db():
    """获取数据库会话"""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# 用户相关操作
def get_user_by_email(db, email):
    """根据邮箱获取用户"""
    return db.query(User).filter(User.email == email).first()

def create_user(db, email):
    """创建新用户"""
    db_user = User(email=email)
    db.add(db_user)
    db.commit()
    db.refresh(db_user)
    return db_user

def get_or_create_user(db, email):
    """获取或创建用户"""
    user = get_user_by_email(db, email)
    if not user:
        user = create_user(db, email)
    return user

# 记忆集合相关操作
def get_memory_collection_by_user(db, user_id):
    """根据用户ID获取记忆集合"""
    return db.query(MemoryCollection).filter(MemoryCollection.user_id == user_id).first()

def create_memory_collection(db, user_id, collection_name):
    """创建记忆集合"""
    db_collection = MemoryCollection(user_id=user_id, collection_name=collection_name)
    db.add(db_collection)
    db.commit()
    db.refresh(db_collection)
    return db_collection

def get_or_create_memory_collection(db, user_id, email):
    """获取或创建用户的记忆集合"""
    # 检查用户是否已有记忆集合
    collection = get_memory_collection_by_user(db, user_id)
    if collection:
        return collection
    
    # 为用户创建新的记忆集合，使用邮箱作为集合名的一部分
    collection_name = f"memory_{email.replace('@', '_').replace('.', '_')}"
    return create_memory_collection(db, user_id, collection_name)

# 用户情感状态相关操作
def get_user_emotional_state(db, user_id):
    """根据用户ID获取情感状态"""
    return db.query(UserEmotionalState).filter(UserEmotionalState.user_id == user_id).first()

def create_user_emotional_state(db, user_id):
    """创建用户情感状态"""
    db_state = UserEmotionalState(user_id=user_id)
    db.add(db_state)
    db.commit()
    db.refresh(db_state)
    return db_state

def get_or_create_user_emotional_state(db, user_id):
    """获取或创建用户情感状态"""
    state = get_user_emotional_state(db, user_id)
    if not state:
        state = create_user_emotional_state(db, user_id)
    return state

def update_user_emotional_state(db, user_id, current_state=None, affection=None, heat=None, sleepy=None, envy=None, stress=None):
    """更新用户情感状态"""
    state = get_user_emotional_state(db, user_id)
    if not state:
        state = create_user_emotional_state(db, user_id)
    
    # 更新各个状态变量
    if current_state is not None:
        state.current_state = current_state
    if affection is not None:
        state.affection = max(0, min(100, affection))  # 确保值在0-100之间
    if heat is not None:
        state.heat = max(0, min(100, heat))  # 确保值在0-100之间
    if sleepy is not None:
        state.sleepy = max(0, min(100, sleepy))  # 确保值在0-100之间
    if envy is not None:
        state.envy = max(0, min(100, envy))  # 确保值在0-100之间
    if stress is not None:
        state.stress = max(0, min(100, stress))  # 确保值在0-100之间
    
    db.commit()
    db.refresh(state)
    return state

# 聊天记录相关操作

def create_chat_history(db, user_id, user_message, assistant_message, state):
    """创建聊天记录"""
    chat_history = ChatHistory(
        user_id=user_id,
        user_message=user_message,
        assistant_message=assistant_message,
        state=state
    )
    db.add(chat_history)
    db.commit()
    db.refresh(chat_history)
    return chat_history

def get_chat_histories_by_user(db, user_id, limit=None, offset=None):
    """根据用户ID获取聊天记录"""
    query = db.query(ChatHistory).filter(ChatHistory.user_id == user_id).order_by(ChatHistory.created_at.asc())
    if limit:
        query = query.limit(limit)
    if offset:
        query = query.offset(offset)
    return query.all()

def clear_chat_histories_by_user(db, user_id):
    """清空特定用户的所有聊天记录"""
    result = db.query(ChatHistory).filter(ChatHistory.user_id == user_id).delete()
    db.commit()
    return result

# 邮箱验证相关操作
def validate_email(email):
    """验证邮箱格式"""
    pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    return re.match(pattern, email) is not None

def generate_verification_code():
    """生成6位数字验证码"""
    return ''.join(secrets.choice('0123456789') for _ in range(6))

def create_verification_code(db, email):
    """创建验证码"""
    # 检查邮箱格式
    if not validate_email(email):
        return None, "邮箱格式不正确"
    
    # 检查是否有未过期的验证码
    user = get_user_by_email(db, email)
    if user and user.verification_code and user.verification_code_expires:
        if user.verification_code_expires > datetime.utcnow():
            remaining_time = (user.verification_code_expires - datetime.utcnow()).seconds
            if remaining_time > 30:  # 30秒内不能重复发送
                return None, f"请等待{remaining_time}秒后再重新发送验证码"
    
    # 生成新验证码
    verification_code = generate_verification_code()
    expires_at = datetime.utcnow() + timedelta(minutes=5)  # 5分钟后过期
    
    if user:
        # 更新现有用户的验证码
        user.verification_code = verification_code
        user.verification_code_expires = expires_at
        user.failed_attempts = 0
        user.last_attempt_time = None
    else:
        # 创建新用户（未验证状态）
        user = User(
            email=email,
            is_verified=False,
            verification_code=verification_code,
            verification_code_expires=expires_at
        )
        db.add(user)
    
    db.commit()
    db.refresh(user)
    
    return user, None

def verify_email_code(db, email, code):
    """验证邮箱验证码"""
    user = get_user_by_email(db, email)
    
    if not user:
        return False, "用户不存在"
    
    if user.is_verified:
        return True, "邮箱已验证"
    
    # 检查验证码是否过期
    if not user.verification_code or not user.verification_code_expires:
        return False, "验证码不存在，请重新发送"
    
    if user.verification_code_expires < datetime.utcnow():
        return False, "验证码已过期，请重新发送"
    
    # 检查尝试次数限制
    if user.failed_attempts >= 5:
        if user.last_attempt_time and (datetime.utcnow() - user.last_attempt_time).minutes < 30:
            return False, "尝试次数过多，请30分钟后再试"
        else:
            user.failed_attempts = 0
    
    # 验证码错误处理
    if user.verification_code != code:
        user.failed_attempts += 1
        user.last_attempt_time = datetime.utcnow()
        db.commit()
        
        remaining_attempts = 5 - user.failed_attempts
        return False, f"验证码错误，还剩{remaining_attempts}次尝试机会"
    
    # 验证成功
    user.is_verified = True
    user.verification_code = None
    user.verification_code_expires = None
    user.failed_attempts = 0
    user.last_attempt_time = None
    
    db.commit()
    
    return True, "验证成功"

def check_user_verified(db, email):
    """检查用户是否已验证"""
    user = get_user_by_email(db, email)
    return user and user.is_verified
