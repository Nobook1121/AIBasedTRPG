#!/usr/bin/env python3
"""
用户管理模块
负责用户的注册、登录、权限管理等功能
"""

import os
import json
import time
import hashlib
import bcrypt

# 用户数据文件路径
USERS_FILE = 'users/users.json'

# 确保users目录存在
if not os.path.exists('users'):
    os.makedirs('users')

# 确保用户数据文件存在
if not os.path.exists(USERS_FILE):
    with open(USERS_FILE, 'w', encoding='utf-8') as f:
        json.dump({"users": []}, f, ensure_ascii=False, indent=2)

class UserManager:
    """用户管理类"""
    
    def __init__(self):
        """初始化用户管理器"""
        self.users = self._load_users()
    
    def _load_users(self):
        """加载用户数据"""
        try:
            with open(USERS_FILE, 'r', encoding='utf-8') as f:
                data = json.load(f)
                return data.get('users', [])
        except Exception as e:
            print(f"加载用户数据失败: {e}")
            return []
    
    def _save_users(self):
        """保存用户数据"""
        try:
            with open(USERS_FILE, 'w', encoding='utf-8') as f:
                json.dump({"users": self.users}, f, ensure_ascii=False, indent=2)
            return True
        except Exception as e:
            print(f"保存用户数据失败: {e}")
            return False
    
    def _hash_password(self, password):
        """加密密码"""
        salt = bcrypt.gensalt()
        hashed = bcrypt.hashpw(password.encode('utf-8'), salt)
        return hashed.decode('utf-8')
    
    def _verify_password(self, password, hashed_password):
        """验证密码"""
        return bcrypt.checkpw(password.encode('utf-8'), hashed_password.encode('utf-8'))
    
    def register(self, username, password, email, ip_address):
        """注册新用户"""
        # 检查用户名是否已存在
        for user in self.users:
            if user['username'] == username:
                return False, "用户名已存在"
        
        # 生成新用户ID
        user_id = max([user['id'] for user in self.users], default=0) + 1
        
        # 创建新用户
        new_user = {
            "id": user_id,
            "username": username,
            "password": self._hash_password(password),
            "email": email,
            "ip_addresses": [ip_address],
            "role": "USER",  # 默认角色为USER
            "created_at": time.strftime('%Y-%m-%dT%H:%M:%S') + '.000Z',
            "last_login": time.strftime('%Y-%m-%dT%H:%M:%S') + '.000Z',
            "character_cards": [],
            "status": "active",
            "avatar": "https://via.placeholder.com/40"
        }
        
        # 添加新用户
        self.users.append(new_user)
        
        # 保存用户数据
        if self._save_users():
            return True, "注册成功"
        else:
            return False, "注册失败"
    
    def login(self, username, password, ip_address):
        """用户登录"""
        # 查找用户
        for user in self.users:
            if user['username'] == username and user['status'] == "active":
                # 验证密码
                if self._verify_password(password, user['password']):
                    # 更新最后登录时间
                    user['last_login'] = time.strftime('%Y-%m-%dT%H:%M:%S') + '.000Z'
                    
                    # 添加IP地址到用户记录
                    if ip_address not in user['ip_addresses']:
                        user['ip_addresses'].append(ip_address)
                    
                    # 保存用户数据
                    self._save_users()
                    
                    return True, "登录成功", user
                else:
                    return False, "密码错误", None
        
        return False, "用户不存在", None
    
    def get_user_by_id(self, user_id):
        """根据ID获取用户"""
        for user in self.users:
            if user['id'] == user_id:
                return user
        return None
    
    def get_user_by_username(self, username):
        """根据用户名获取用户"""
        for user in self.users:
            if user['username'] == username:
                return user
        return None
    
    def update_user_role(self, user_id, role):
        """更新用户角色"""
        for user in self.users:
            if user['id'] == user_id:
                user['role'] = role
                self._save_users()
                return True, "角色更新成功"
        return False, "用户不存在"
    
    def update_user_status(self, user_id, status):
        """更新用户状态"""
        for user in self.users:
            if user['id'] == user_id:
                user['status'] = status
                self._save_users()
                return True, "状态更新成功"
        return False, "用户不存在"
    
    def get_all_users(self):
        """获取所有用户"""
        return self.users
    
    def check_permission(self, user_id, required_role):
        """检查用户权限"""
        user = self.get_user_by_id(user_id)
        if not user:
            return False
        
        # 权限等级：OWNER > ADMIN > USER
        role_levels = {
            "OWNER": 3,
            "ADMIN": 2,
            "USER": 1
        }
        
        user_level = role_levels.get(user['role'], 0)
        required_level = role_levels.get(required_role, 0)
        
        return user_level >= required_level

# 初始化用户管理器
user_manager = UserManager()