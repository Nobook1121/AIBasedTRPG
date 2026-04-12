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

# IP配置文件目录
USER_IP_CONFIG_DIR = 'users/ip_configs'

# 确保users目录存在
if not os.path.exists('users'):
    os.makedirs('users')

# 确保IP配置目录存在
if not os.path.exists(USER_IP_CONFIG_DIR):
    os.makedirs(USER_IP_CONFIG_DIR)

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
    
    def register(self, username, password, email, ip_address=None):
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
    
    def login(self, username, password, ip_address=None):
        """用户登录"""
        # 查找用户
        for user in self.users:
            if user['username'] == username and user['status'] == "active":
                # 验证密码
                if self._verify_password(password, user['password']):
                    # 更新最后登录时间
                    user['last_login'] = time.strftime('%Y-%m-%dT%H:%M:%S') + '.000Z'
                    
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
    

    
    def create_ip_config(self, ip_address):
        """为IP地址创建配置文件"""
        config_file = os.path.join(USER_IP_CONFIG_DIR, f'{ip_address.replace(".", "_")}.json')
        config = {
            "ip_address": ip_address,
            "created_at": time.strftime('%Y-%m-%dT%H:%M:%S') + '.000Z',
            "last_accessed": time.strftime('%Y-%m-%dT%H:%M:%S') + '.000Z',
            "settings": {},
            "preferences": {}
        }
        
        try:
            with open(config_file, 'w', encoding='utf-8') as f:
                json.dump(config, f, ensure_ascii=False, indent=2)
            return True
        except Exception as e:
            print(f"创建IP配置文件失败: {e}")
            return False
    
    def get_ip_config(self, ip_address):
        """获取IP地址的配置文件"""
        config_file = os.path.join(USER_IP_CONFIG_DIR, f'{ip_address.replace(".", "_")}.json')
        try:
            if os.path.exists(config_file):
                with open(config_file, 'r', encoding='utf-8') as f:
                    config = json.load(f)
                    # 更新最后访问时间
                    config['last_accessed'] = time.strftime('%Y-%m-%dT%H:%M:%S') + '.000Z'
                    # 保存更新
                    with open(config_file, 'w', encoding='utf-8') as f:
                        json.dump(config, f, ensure_ascii=False, indent=2)
                    return config
            return None
        except Exception as e:
            print(f"获取IP配置文件失败: {e}")
            return None
    
    def update_ip_config(self, ip_address, config_data):
        """更新IP地址的配置文件"""
        config_file = os.path.join(USER_IP_CONFIG_DIR, f'{ip_address.replace(".", "_")}.json')
        try:
            if os.path.exists(config_file):
                with open(config_file, 'r', encoding='utf-8') as f:
                    config = json.load(f)
                
                # 更新配置
                config.update(config_data)
                config['last_accessed'] = time.strftime('%Y-%m-%dT%H:%M:%S') + '.000Z'
                
                with open(config_file, 'w', encoding='utf-8') as f:
                    json.dump(config, f, ensure_ascii=False, indent=2)
                return True
            return False
        except Exception as e:
            print(f"更新IP配置文件失败: {e}")
            return False
    
    def delete_ip_config(self, ip_address):
        """删除IP地址的配置文件"""
        config_file = os.path.join(USER_IP_CONFIG_DIR, f'{ip_address.replace(".", "_")}.json')
        try:
            if os.path.exists(config_file):
                os.remove(config_file)
                return True
            return False
        except Exception as e:
            print(f"删除IP配置文件失败: {e}")
            return False
    
    def get_all_ip_configs(self):
        """获取所有IP配置文件"""
        configs = []
        try:
            for filename in os.listdir(USER_IP_CONFIG_DIR):
                if filename.endswith('.json'):
                    file_path = os.path.join(USER_IP_CONFIG_DIR, filename)
                    try:
                        with open(file_path, 'r', encoding='utf-8') as f:
                            config = json.load(f)
                            configs.append(config)
                    except Exception as e:
                        print(f"读取IP配置文件失败: {e}")
                        continue
            return configs
        except Exception as e:
            print(f"获取所有IP配置文件失败: {e}")
            return []

# 初始化用户管理器
user_manager = UserManager()