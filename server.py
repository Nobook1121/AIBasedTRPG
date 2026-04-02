#!/usr/bin/env python3
"""
AI TRPG 系统服务器端
负责读取和管理scenarios文件夹内的剧本JSON文件
"""

import os
import json
import time
from flask import Flask, jsonify, request, send_from_directory, session, redirect, url_for
from flask_cors import CORS
from user_manager import user_manager

# 权限检查装饰器
def require_permission(required_role):
    def decorator(f):
        def decorated_function(*args, **kwargs):
            if 'user_id' not in session:
                return jsonify({
                    'success': False,
                    'error': '未登录',
                    'message': '请先登录'
                }), 401
            
            user_id = session['user_id']
            if not user_manager.check_permission(user_id, required_role):
                return jsonify({
                    'success': False,
                    'error': '权限不足',
                    'message': '您没有足够的权限执行此操作'
                }), 403
            return f(*args, **kwargs)
        # 确保装饰后的函数有唯一的名称
        decorated_function.__name__ = f"{f.__name__}_decorated"
        return decorated_function
    return decorator

# 日志功能实现
# 服务器启动时创建固定的日志文件名
SERVER_START_TIME = time.strftime('%Y%m%d_%H%M%S')
CURRENT_LOG_FILE = f'logs/ai_trpg_{SERVER_START_TIME}.log'

def get_log_file():
    """获取服务器启动时创建的固定日志文件名"""
    return CURRENT_LOG_FILE

def log_info(message):
    timestamp = time.strftime('%Y-%m-%d %H:%M:%S')
    log_message = f'[{timestamp}][MainProcess][INFO] {message}'
    print(log_message, flush=True)
    # 确保logs目录存在
    if not os.path.exists('logs'):
        os.makedirs('logs')
    # 写入日志文件
    try:
        log_file = get_log_file()
        with open(log_file, 'a', encoding='utf-8') as f:
            f.write(log_message + '\n')
            f.flush()
    except Exception as e:
        print(f"写入日志文件失败: {e}", flush=True)

def log_warning(message):
    timestamp = time.strftime('%Y-%m-%d %H:%M:%S')
    log_message = f'[{timestamp}][MainProcess][WARNING] {message}'
    print(log_message, flush=True)
    # 确保logs目录存在
    if not os.path.exists('logs'):
        os.makedirs('logs')
    # 写入日志文件
    try:
        log_file = get_log_file()
        with open(log_file, 'a', encoding='utf-8') as f:
            f.write(log_message + '\n')
            f.flush()
    except Exception as e:
        print(f"写入日志文件失败: {e}", flush=True)

def log_error(message):
    timestamp = time.strftime('%Y-%m-%d %H:%M:%S')
    log_message = f'[{timestamp}][MainProcess][ERROR] {message}'
    print(log_message, flush=True)
    # 确保logs目录存在
    if not os.path.exists('logs'):
        os.makedirs('logs')
    # 写入日志文件
    try:
        log_file = get_log_file()
        with open(log_file, 'a', encoding='utf-8') as f:
            f.write(log_message + '\n')
            f.flush()
    except Exception as e:
        print(f"写入日志文件失败: {e}", flush=True)

app = Flask(__name__)
CORS(app)  # 允许跨域请求

# 设置静态文件服务
app.static_folder = 'assets'
app.static_url_path = '/assets'

# 设置secret_key用于session管理
app.secret_key = 'your-secret-key-here'

# 禁用Flask默认的访问日志
import logging
log = logging.getLogger('werkzeug')
log.setLevel(logging.ERROR)

# 配置
SCENARIOS_DIR = 'scenarios'
SCENARIO_COVERS_DIR = 'assets/scenario_covers'
AVATARS_DIR = 'assets/avatars'

# 确保scenarios目录存在
if not os.path.exists(SCENARIOS_DIR):
    os.makedirs(SCENARIOS_DIR)
    log_info(f"创建scenarios目录: {SCENARIOS_DIR}")

# 确保assets目录存在
if not os.path.exists('assets'):
    os.makedirs('assets')
    log_info(f"创建assets目录: assets")

# 确保scenario_covers目录存在
if not os.path.exists(SCENARIO_COVERS_DIR):
    os.makedirs(SCENARIO_COVERS_DIR)

# 确保avatars目录存在
if not os.path.exists(AVATARS_DIR):
    os.makedirs(AVATARS_DIR)
    log_info(f"创建scenario_covers目录: {SCENARIO_COVERS_DIR}")

# 缓存机制
scenarios_cache = {}
cache_timestamp = 0
CACHE_DURATION = 60  # 缓存有效期（秒）


def get_scenarios():
    """
    读取所有剧本文件
    实现缓存机制以提高性能
    """
    global scenarios_cache, cache_timestamp
    current_time = time.time()
    
    # 检查缓存是否有效
    if current_time - cache_timestamp < CACHE_DURATION and scenarios_cache:
        log_info(f"使用缓存加载剧本，共 {len(scenarios_cache)} 个")
        return scenarios_cache
    
    scenarios = []
    
    try:
        # 遍历scenarios目录
        for filename in os.listdir(SCENARIOS_DIR):
            if filename.endswith('.json'):
                file_path = os.path.join(SCENARIOS_DIR, filename)
                try:
                    with open(file_path, 'r', encoding='utf-8') as f:
                        scenario = json.load(f)
                        # 确保剧本有必要的字段
                        if 'id' not in scenario:
                            # 从文件名提取ID或生成新ID
                            try:
                                # 尝试从文件名提取ID
                                scenario['id'] = int(filename.split('_')[-1].split('.')[0])
                            except (ValueError, IndexError):
                                # 如果提取失败，生成新ID
                                scenario['id'] = int(time.time() * 1000)
                                log_warning(f"从文件名 {filename} 提取ID失败，生成新ID: {scenario['id']}")
                        scenarios.append(scenario)
                except json.JSONDecodeError as e:
                    log_error(f"解析文件 {filename} 时出错: {e}")
                except Exception as e:
                    log_error(f"读取文件 {filename} 时出错: {e}")
    except Exception as e:
        log_error(f"读取scenarios目录时出错: {e}")
    
    # 更新缓存
    scenarios_cache = scenarios
    cache_timestamp = current_time
    
    log_info(f"加载剧本完成，共 {len(scenarios)} 个")
    return scenarios


@app.route('/api/scenarios', methods=['GET'])
def get_all_scenarios():
    """
    获取所有剧本
    """
    try:
        log_info("接收到获取所有剧本的请求")
        scenarios = get_scenarios()
        log_info(f"获取所有剧本成功，共 {len(scenarios)} 个")
        return jsonify({
            'success': True,
            'data': scenarios,
            'message': f'成功加载 {len(scenarios)} 个剧本'
        })
    except Exception as e:
        log_error(f"获取所有剧本失败: {e}")
        return jsonify({
            'success': False,
            'error': str(e),
            'message': '加载剧本失败'
        }), 500


@app.route('/api/scenarios/<int:scenario_id>', methods=['GET'])
def get_scenario(scenario_id):
    """
    获取单个剧本
    """
    try:
        log_info(f"接收到获取剧本的请求，ID: {scenario_id}")
        scenarios = get_scenarios()
        scenario = next((s for s in scenarios if s.get('id') == scenario_id), None)
        
        if scenario:
            log_info(f"获取剧本成功，ID: {scenario_id}, 标题: {scenario.get('title')}")
            return jsonify({
                'success': True,
                'data': scenario,
                'message': '剧本加载成功'
            })
        else:
            log_warning(f"获取剧本失败，ID: {scenario_id} 不存在")
            return jsonify({
                'success': False,
                'error': '剧本不存在',
                'message': f'ID为 {scenario_id} 的剧本不存在'
            }), 404
    except Exception as e:
        log_error(f"获取剧本失败，ID: {scenario_id}, 错误: {e}")
        return jsonify({
            'success': False,
            'error': str(e),
            'message': '加载剧本失败'
        }), 500


@app.route('/api/scenarios', methods=['POST'])
def create_scenario():
    """
    创建新剧本
    """
    try:
        log_info("接收到创建剧本的请求")
        scenario_data = request.json
        
        if not scenario_data:
            log_warning("创建剧本失败：无数据")
            return jsonify({
                'success': False,
                'error': '无数据',
                'message': '请提供剧本数据'
            }), 400
        
        # 获取用户ID
        user_id = scenario_data.get('user_id', 'unknown')
        
        # 获取剧本标题
        title = scenario_data.get('title', 'unnamed')
        
        # 检查剧本标题是否已存在
        try:
            for filename in os.listdir(SCENARIOS_DIR):
                if filename.endswith('.json'):
                    file_path = os.path.join(SCENARIOS_DIR, filename)
                    try:
                        with open(file_path, 'r', encoding='utf-8') as f:
                            existing_data = json.load(f)
                            if existing_data.get('title') == title:
                                log_warning(f"创建剧本失败：剧本标题 '{title}' 已存在")
                                return jsonify({
                                    'success': False,
                                    'error': '剧本标题已存在',
                                    'message': f'剧本标题 "{title}" 已存在，请使用其他标题'
                                }), 400
                    except Exception as e:
                        log_error(f"检查剧本标题时出错: {e}")
                        continue
        except Exception as e:
            log_error(f"读取scenarios目录时出错: {e}")
            # 继续执行，不阻止剧本创建
        
        # 生成唯一ID（保留ID字段以保持兼容性）
        scenario_id = int(time.time() * 1000)
        scenario_data['id'] = scenario_id
        scenario_data['createdAt'] = time.strftime('%Y-%m-%dT%H:%M:%S') + '.000Z'
        
        # 确保封面路径正确
        if 'cover' not in scenario_data or not scenario_data['cover']:
            scenario_data['cover'] = '/scenario_covers/default_cover.png'
        
        # 生成文件名，使用剧本标题作为唯一标识
        safe_title = title.replace('/', '_').replace('\\', '_')
        filename = f"{safe_title}.json"
        file_path = os.path.join(SCENARIOS_DIR, filename)
        
        # 写入文件
        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump(scenario_data, f, ensure_ascii=False, indent=2)
        
        # 清除缓存
        global scenarios_cache, cache_timestamp
        scenarios_cache = {}
        cache_timestamp = 0
        
        log_info(f"[剧本操作] 用户{user_id}成功创建剧本，ID: {scenario_id}, 标题: {title}")
        return jsonify({
            'success': True,
            'data': scenario_data,
            'message': '剧本创建成功'
        }), 201
    except Exception as e:
        log_error(f"创建剧本时出错: {e}")
        return jsonify({
            'success': False,
            'error': str(e),
            'message': '创建剧本失败'
        }), 500


@app.route('/api/scenarios/<int:scenario_id>', methods=['PUT'])
def update_scenario(scenario_id):
    """
    更新剧本
    """
    try:
        log_info(f"接收到更新剧本的请求，ID: {scenario_id}")
        scenario_data = request.json
        
        if not scenario_data:
            log_warning(f"更新剧本失败，ID: {scenario_id}：无数据")
            return jsonify({
                'success': False,
                'error': '无数据',
                'message': '请提供剧本数据'
            }), 400
        
        # 获取用户ID
        user_id = scenario_data.get('user_id', 'unknown')
        
        # 查找剧本文件
        scenarios = get_scenarios()
        scenario = next((s for s in scenarios if s.get('id') == scenario_id), None)
        
        if not scenario:
            log_warning(f"更新剧本失败，ID: {scenario_id} 不存在")
            return jsonify({
                'success': False,
                'error': '剧本不存在',
                'message': f'ID为 {scenario_id} 的剧本不存在'
            }), 404
        
        # 查找对应的文件
        file_found = False
        for filename in os.listdir(SCENARIOS_DIR):
            if filename.endswith('.json'):
                file_path = os.path.join(SCENARIOS_DIR, filename)
                try:
                    with open(file_path, 'r', encoding='utf-8') as f:
                        file_data = json.load(f)
                        if file_data.get('id') == scenario_id:
                            # 更新文件
                            scenario_data['id'] = scenario_id
                            scenario_data['updatedAt'] = time.strftime('%Y-%m-%dT%H:%M:%S') + '.000Z'
                            if 'createdAt' not in scenario_data:
                                scenario_data['createdAt'] = scenario.get('createdAt', time.strftime('%Y-%m-%dT%H:%M:%S') + '.000Z')
                            
                            with open(file_path, 'w', encoding='utf-8') as f:
                                json.dump(scenario_data, f, ensure_ascii=False, indent=2)
                            
                            file_found = True
                            break
                except Exception as e:
                    log_error(f"处理文件 {filename} 时出错: {e}")
                    continue
        
        if not file_found:
            log_warning(f"更新剧本失败，ID: {scenario_id} 对应的文件不存在")
            return jsonify({
                'success': False,
                'error': '文件不存在',
                'message': '找不到对应的剧本文件'
            }), 404
        
        # 清除缓存
        global scenarios_cache, cache_timestamp
        scenarios_cache = {}
        cache_timestamp = 0
        
        log_info(f"[剧本操作] 用户{user_id}成功更新剧本，ID: {scenario_id}, 标题: {scenario_data.get('title', '未知')}")
        return jsonify({
            'success': True,
            'data': scenario_data,
            'message': '剧本更新成功'
        })
    except Exception as e:
        log_error(f"更新剧本时出错，ID: {scenario_id}, 错误: {e}")
        return jsonify({
            'success': False,
            'error': str(e),
            'message': '更新剧本失败'
        }), 500


@app.route('/api/scenarios/<int:scenario_id>', methods=['DELETE'])
def delete_scenario(scenario_id):
    """
    删除剧本
    """
    try:
        log_info(f"接收到删除剧本的请求，ID: {scenario_id}")
        
        # 获取用户ID
        user_id = 'unknown'
        try:
            if request.json:
                user_id = request.json.get('user_id', 'unknown')
        except Exception:
            pass
        
        # 查找剧本文件
        file_deleted = False
        target_file = None
        scenario_title = ""
        
        # 遍历所有JSON文件
        for filename in os.listdir(SCENARIOS_DIR):
            if filename.endswith('.json'):
                file_path = os.path.join(SCENARIOS_DIR, filename)
                try:
                    with open(file_path, 'r', encoding='utf-8') as f:
                        data = json.load(f)
                        # 尝试不同类型的ID比较
                        if data.get('id') == scenario_id or str(data.get('id')) == str(scenario_id):
                            target_file = file_path
                            scenario_title = data.get('title', '未知')
                            break
                except Exception as e:
                    log_error(f"处理文件 {filename} 时出错: {e}")
                    continue
        
        # 如果找到文件，删除它
        if target_file:
            os.remove(target_file)
            file_deleted = True
            
            # 删除对应的封面文件
            cover_filename = f"{scenario_id}.png"
            cover_path = os.path.join(SCENARIO_COVERS_DIR, cover_filename)
            if os.path.exists(cover_path):
                try:
                    os.remove(cover_path)
                    log_info(f"[剧本操作] 成功删除剧本封面: {cover_path}")
                except Exception as e:
                    log_error(f"删除封面文件时出错: {e}")
        
        if not file_deleted:
            log_warning(f"删除剧本失败，ID: {scenario_id} 不存在")
            return jsonify({
                'success': False,
                'error': '剧本不存在',
                'message': f'ID为 {scenario_id} 的剧本不存在'
            }), 404
        
        # 清除缓存
        global scenarios_cache, cache_timestamp
        scenarios_cache = {}
        cache_timestamp = 0
        
        log_info(f"[剧本操作] 用户{user_id}成功删除剧本，ID: {scenario_id}, 标题: {scenario_title}")
        return jsonify({
            'success': True,
            'message': '剧本删除成功'
        })
    except Exception as e:
        log_error(f"删除剧本时出错，ID: {scenario_id}, 错误: {e}")
        return jsonify({
            'success': False,
            'error': str(e),
            'message': '删除剧本失败'
        }), 500


@app.route('/api/scenarios/cover', methods=['POST'])
def upload_scenario_cover():
    """
    上传剧本封面图片
    """
    try:
        log_info("接收到上传剧本封面的请求")
        
        # 获取用户ID
        user_id = 'unknown'
        if 'user_id' in session:
            user_id = session['user_id']
        elif request.form.get('user_id'):
            user_id = request.form.get('user_id')
        
        # 检查是否有文件
        if 'cover' not in request.files:
            log_warning("上传封面失败：无文件")
            return jsonify({
                'success': False,
                'error': '无文件',
                'message': '请选择要上传的封面图片'
            }), 400
        
        cover = request.files['cover']
        
        # 检查文件类型
        if not cover.filename.endswith(('.png', '.jpg', '.jpeg', '.gif')):
            log_warning("上传封面失败：文件类型错误")
            return jsonify({
                'success': False,
                'error': '文件类型错误',
                'message': '请上传图片文件（PNG、JPG、JPEG、GIF）'
            }), 400
        
        # 检查文件大小（限制为5MB）
        if cover.content_length > 5 * 1024 * 1024:
            log_warning("上传封面失败：文件过大")
            return jsonify({
                'success': False,
                'error': '文件过大',
                'message': '封面文件大小不能超过5MB'
            }), 400
        
        # 使用剧本标题作为唯一标识命名封面图片
        # 从表单中获取剧本标题，或使用时间戳作为临时标题
        scenario_title = request.form.get('scenario_title', str(int(time.time() * 1000)))
        safe_title = scenario_title.replace('/', '_').replace('\\', '_')
        filename = f"{safe_title}.png"
        file_path = os.path.join(SCENARIO_COVERS_DIR, filename)
        
        # 如果文件已存在，删除旧文件
        if os.path.exists(file_path):
            os.remove(file_path)
            log_info(f"删除旧封面文件: {file_path}")
        
        # 保存文件
        cover.save(file_path)
        log_info(f"[剧本操作] 封面文件保存成功: {file_path}")
        
        # 返回文件路径
        cover_url = f"/assets/scenario_covers/{filename}"
        
        log_info(f"用户{user_id}成功上传剧本封面")
        return jsonify({
            'success': True,
            'data': {
                'cover_url': cover_url
            },
            'message': '封面上传成功'
        })
    except Exception as e:
        log_error(f"上传封面时出错: {e}")
        return jsonify({
            'success': False,
            'error': str(e),
            'message': '上传封面失败'
        }), 500

@app.route('/api/scenarios/cover', methods=['DELETE'])
def delete_scenario_cover():
    """
    删除剧本封面图片
    """
    try:
        log_info("接收到删除剧本封面的请求")
        
        # 获取用户ID
        user_id = 'unknown'
        if 'user_id' in session:
            user_id = session['user_id']
        
        # 获取封面路径
        data = request.get_json()
        if not data or 'cover_path' not in data:
            log_warning("删除封面失败：无数据")
            return jsonify({
                'success': False,
                'error': '无数据',
                'message': '请提供封面路径'
            }), 400
        
        cover_path = data['cover_path']
        # 提取文件名
        filename = os.path.basename(cover_path)
        file_path = os.path.join(SCENARIO_COVERS_DIR, filename)
        
        # 检查文件是否存在
        if os.path.exists(file_path):
            # 确保不是默认封面
            if filename != 'default_cover.png':
                os.remove(file_path)
                log_info(f"[剧本操作] 封面文件删除成功: {file_path}")
                log_info(f"用户{user_id}成功删除剧本封面")
                return jsonify({
                    'success': True,
                    'message': '封面删除成功'
                })
            else:
                log_warning("删除封面失败：默认封面不能删除")
                return jsonify({
                    'success': False,
                    'error': '默认封面不能删除',
                    'message': '默认封面不能删除'
                }), 400
        else:
            log_warning(f"删除封面失败：文件不存在，路径: {file_path}")
            return jsonify({
                'success': False,
                'error': '文件不存在',
                'message': '封面文件不存在'
            }), 404
    except Exception as e:
        log_error(f"删除封面时出错: {e}")
        return jsonify({
            'success': False,
            'error': str(e),
            'message': '删除封面失败'
        }), 500

@app.route('/api/scenarios/cover/rename', methods=['POST'])
def rename_scenario_cover():
    """
    重命名剧本封面图片
    """
    try:
        log_info("接收到重命名剧本封面的请求")
        
        # 获取用户ID
        user_id = 'unknown'
        if 'user_id' in session:
            user_id = session['user_id']
        
        # 获取重命名信息
        data = request.get_json()
        if not data or 'old_filename' not in data or 'new_filename' not in data:
            log_warning("重命名封面失败：无数据")
            return jsonify({
                'success': False,
                'error': '无数据',
                'message': '请提供旧文件名和新文件名'
            }), 400
        
        old_filename = data['old_filename']
        new_filename = data['new_filename']
        
        # 构建文件路径
        old_file_path = os.path.join(SCENARIO_COVERS_DIR, old_filename)
        new_file_path = os.path.join(SCENARIO_COVERS_DIR, new_filename)
        
        # 检查旧文件是否存在
        if os.path.exists(old_file_path):
            # 确保不是默认封面
            if old_filename != 'default_cover.png':
                # 如果新文件已存在，删除它
                if os.path.exists(new_file_path):
                    os.remove(new_file_path)
                    log_info(f"删除已存在的新封面文件: {new_file_path}")
                
                # 重命名文件
                os.rename(old_file_path, new_file_path)
                log_info(f"[剧本操作] 封面文件重命名成功: {old_filename} -> {new_filename}")
                log_info(f"用户{user_id}成功重命名剧本封面")
                return jsonify({
                    'success': True,
                    'message': '封面重命名成功'
                })
            else:
                log_warning("重命名封面失败：默认封面不能重命名")
                return jsonify({
                    'success': False,
                    'error': '默认封面不能重命名',
                    'message': '默认封面不能重命名'
                }), 400
        else:
            log_warning(f"重命名封面失败：文件不存在，路径: {old_file_path}")
            return jsonify({
                'success': False,
                'error': '文件不存在',
                'message': '封面文件不存在'
            }), 404
    except Exception as e:
        log_error(f"重命名封面时出错: {e}")
        return jsonify({
            'success': False,
            'error': str(e),
            'message': '重命名封面失败'
        }), 500


@app.route('/api/scenarios/list', methods=['GET'])
def get_scenario_list():
    """
    获取剧本文件列表
    """
    try:
        files = []
        for filename in os.listdir(SCENARIOS_DIR):
            if filename.endswith('.json'):
                file_path = os.path.join(SCENARIOS_DIR, filename)
                try:
                    file_stats = os.stat(file_path)
                    files.append({
                        'filename': filename,
                        'size': file_stats.st_size,
                        'mtime': time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(file_stats.st_mtime))
                    })
                except Exception as e:
                    log_error(f"获取文件信息时出错: {e}")
        
        log_info(f"获取剧本列表成功，共 {len(files)} 个文件")
        return jsonify({
            'success': True,
            'data': {
                'files': files,
                'total': len(files)
            },
            'message': '获取剧本列表成功'
        })
    except Exception as e:
        log_error(f"获取剧本列表时出错: {e}")
        return jsonify({
            'success': False,
            'error': str(e),
            'message': '获取剧本列表失败'
        }), 500


@app.route('/api/auth/register', methods=['POST'])
def register():
    """
    用户注册
    """
    try:
        # 获取用户IP地址
        ip_address = request.remote_addr
        log_info(f"接收到注册请求，IP地址: {ip_address}")
        
        user_data = request.json
        
        if not user_data:
            log_warning("注册失败：无数据")
            return jsonify({
                'success': False,
                'error': '无数据',
                'message': '请提供注册数据'
            }), 400
        
        # 获取注册信息
        username = user_data.get('username')
        password = user_data.get('password')
        email = user_data.get('email')
        
        if not username or not password or not email:
            log_warning("注册失败：信息不完整")
            return jsonify({
                'success': False,
                'error': '信息不完整',
                'message': '请提供用户名、密码和邮箱'
            }), 400
        
        # 注册用户
        success, message = user_manager.register(username, password, email, ip_address)
        
        if success:
            log_info(f"[用户操作] 新用户注册成功: 用户名={username}, 邮箱={email}, IP={ip_address}")
            return jsonify({
                'success': True,
                'message': message
            }), 201
        else:
            log_warning(f"[用户操作] 注册失败: 用户名={username}, 原因={message}")
            return jsonify({
                'success': False,
                'error': message,
                'message': message
            }), 400
    except Exception as e:
        log_error(f"注册时出错: {e}")
        return jsonify({
            'success': False,
            'error': str(e),
            'message': '注册失败'
        }), 500


@app.route('/api/auth/login', methods=['POST'])
def login():
    """
    用户登录
    """
    try:
        # 获取用户IP地址
        ip_address = request.remote_addr
        log_info(f"接收到登录请求，IP地址: {ip_address}")
        
        login_data = request.json
        
        if not login_data:
            log_warning("登录失败：无数据")
            return jsonify({
                'success': False,
                'error': '无数据',
                'message': '请提供登录数据'
            }), 400
        
        # 获取登录信息
        username = login_data.get('username')
        password = login_data.get('password')
        
        if not username or not password:
            log_warning("登录失败：信息不完整")
            return jsonify({
                'success': False,
                'error': '信息不完整',
                'message': '请提供用户名和密码'
            }), 400
        
        # 登录用户
        success, message, user = user_manager.login(username, password, ip_address)
        
        if success:
            # 设置session
            session['user_id'] = user['id']
            session['username'] = user['username']
            session['role'] = user['role']
            
            log_info(f"[用户操作] 登录成功: 用户名={username}, 用户ID={user['id']}, IP={ip_address}")
            return jsonify({
                'success': True,
                'data': {
                    'user_id': user['id'],
                    'username': user['username'],
                    'role': user['role'],
                    'email': user['email'],
                    'avatar': user.get('avatar', 'https://via.placeholder.com/40')
                },
                'message': message
            })
        else:
            log_warning(f"[用户操作] 登录失败: 用户名={username}, 原因={message}, IP={ip_address}")
            return jsonify({
                'success': False,
                'error': message,
                'message': message
            }), 401
    except Exception as e:
        log_error(f"登录时出错: {e}")
        return jsonify({
            'success': False,
            'error': str(e),
            'message': '登录失败'
        }), 500


@app.route('/api/auth/logout', methods=['POST'])
def logout():
    """
    用户登出
    """
    try:
        if 'user_id' in session:
            username = session.get('username')
            log_info(f"用户{username}登出")
            session.clear()
            return jsonify({
                'success': True,
                'message': '登出成功'
            })
        else:
            return jsonify({
                'success': False,
                'error': '未登录',
                'message': '您尚未登录'
            }), 401
    except Exception as e:
        log_error(f"登出时出错: {e}")
        return jsonify({
            'success': False,
            'error': str(e),
            'message': '登出失败'
        }), 500


@app.route('/api/auth/status', methods=['GET'])
def get_auth_status():
    """
    获取认证状态
    """
    try:
        if 'user_id' in session:
            user = user_manager.get_user_by_id(session['user_id'])
            return jsonify({
                'success': True,
                'data': {
                    'user_id': session['user_id'],
                    'username': session['username'],
                    'role': session['role'],
                    'email': user.get('email', ''),
                    'avatar': user.get('avatar', 'https://via.placeholder.com/40')
                },
                'message': '已登录'
            })
        else:
            return jsonify({
                'success': False,
                'message': '未登录'
            }), 401
    except Exception as e:
        log_error(f"获取认证状态时出错: {e}")
        return jsonify({
            'success': False,
            'error': str(e),
            'message': '获取认证状态失败'
        }), 500


@app.route('/api/auth/update', methods=['POST'])
def update_user():
    """
    更新用户信息，包括头像上传
    """
    try:
        if 'user_id' not in session:
            return jsonify({
                'success': False,
                'error': '未登录',
                'message': '请先登录'
            }), 401
        
        user_id = session['user_id']
        user = user_manager.get_user_by_id(user_id)
        
        if not user:
            return jsonify({
                'success': False,
                'error': '用户不存在',
                'message': '用户不存在'
            }), 404
        
        # 处理表单数据
        username = request.form.get('username')
        nickname = request.form.get('nickname')
        email = request.form.get('email')
        password = request.form.get('password')
        
        # 验证必填字段
        if not username:
            return jsonify({
                'success': False,
                'error': '信息不完整',
                'message': '请提供用户名'
            }), 400
        
        # 如果邮箱为空，设置为默认值
        if not email:
            email = user.get('email', '')
        
        # 处理头像上传
        avatar_path = user.get('avatar', 'https://via.placeholder.com/40')
        if 'avatar' in request.files:
            try:
                avatar = request.files['avatar']
                
                # 检查文件类型
                if not avatar.filename.endswith(('.png', '.jpg', '.jpeg', '.gif')):
                    return jsonify({
                        'success': False,
                        'error': '文件类型错误',
                        'message': '请上传图片文件（PNG、JPG、JPEG、GIF）'
                    }), 400
                
                # 检查文件大小（限制为2MB）
                if avatar.content_length > 2 * 1024 * 1024:
                    return jsonify({
                        'success': False,
                        'error': '文件过大',
                        'message': '头像文件大小不能超过2MB'
                    }), 400
                
                # 确保avatars目录存在
                avatars_dir = AVATARS_DIR
                if not os.path.exists(avatars_dir):
                    os.makedirs(avatars_dir)
                
                # 生成唯一的文件名
                filename = f"{user_id}_{int(time.time())}_{avatar.filename}"
                file_path = os.path.join(avatars_dir, filename)
                
                # 保存文件
                avatar.save(file_path)
                log_info(f"[用户操作] 头像文件保存成功: {file_path}")
                # 更新头像路径
                avatar_path = f"/assets/avatars/{filename}"
            except Exception as e:
                log_error(f"保存头像文件失败: {e}")
                return jsonify({
                    'success': False,
                    'error': '保存文件失败',
                    'message': '保存头像文件失败，请稍后重试'
                }), 500
        
        # 记录更新前的状态
        old_username = user['username']
        old_avatar = user.get('avatar', '')
        
        # 更新用户信息
        user['username'] = username
        user['nickname'] = nickname
        user['email'] = email
        user['avatar'] = avatar_path
        
        changes = []
        if old_username != username:
            changes.append(f"用户名从 '{old_username}' 更改为 '{username}'")
        if nickname:
            changes.append(f"昵称设置为 '{nickname}'")
        if email:
            changes.append(f"邮箱设置为 '{email}'")
        if password:
            changes.append("密码已更改")
        if old_avatar != avatar_path:
            changes.append("头像已更改")
        
        if password:
            user['password'] = user_manager._hash_password(password)
        
        # 保存更新
        if not user_manager._save_users():
            log_error(f"保存用户数据失败")
            return jsonify({
                'success': False,
                'error': '保存数据失败',
                'message': '保存用户数据失败，请稍后重试'
            }), 500
        
        # 更新session
        session['username'] = username
        
        # 记录更新操作
        if changes:
            log_info(f"[用户操作] 用户更新成功: 用户ID={user_id}, 更改: {', '.join(changes)}")
        else:
            log_info(f"[用户操作] 用户更新成功: 用户ID={user_id}, 无变更")
        return jsonify({
            'success': True,
            'data': {
                'user_id': user_id,
                'username': username,
                'nickname': nickname,
                'email': email,
                'avatar': avatar_path
            },
            'message': '更新成功'
        })
    except Exception as e:
        log_error(f"更新用户信息时出错: {e}")
        import traceback
        log_error(f"错误堆栈: {traceback.format_exc()}")
        return jsonify({
            'success': False,
            'error': str(e),
            'message': f'更新失败: {str(e)}'
        }), 500


@app.route('/assets/avatars/<path:filename>')
def serve_avatar(filename):
    """
    提供头像文件服务
    """
    try:
        log_info(f"提供头像文件: {filename}")
        return send_from_directory('assets/avatars', filename)
    except Exception as e:
        log_error(f"提供头像文件时出错: {e}")
        return "File not found", 404


@app.route('/assets/scenario_covers/<path:filename>')
def serve_scenario_cover(filename):
    """
    提供剧本封面文件服务
    """
    return send_from_directory('assets/scenario_covers', filename)


@app.route('/api/users', methods=['GET'])
@require_permission('ADMIN')
def get_users():
    """
    获取用户列表
    """
    try:
        log_info(f"用户{session['username']}获取用户列表")
        users = user_manager.get_all_users()
        
        # 过滤敏感信息
        filtered_users = []
        for user in users:
            filtered_user = {
                'id': user['id'],
                'username': user['username'],
                'email': user['email'],
                'role': user['role'],
                'ip_addresses': user['ip_addresses'],
                'created_at': user['created_at'],
                'last_login': user['last_login'],
                'status': user['status']
            }
            filtered_users.append(filtered_user)
        
        return jsonify({
            'success': True,
            'data': filtered_users,
            'message': '获取用户列表成功'
        })
    except Exception as e:
        log_error(f"获取用户列表时出错: {e}")
        return jsonify({
            'success': False,
            'error': str(e),
            'message': '获取用户列表失败'
        }), 500


@app.route('/api/users/<int:user_id>/role', methods=['PUT'])
@require_permission('ADMIN')
def update_user_role(user_id):
    """
    更新用户角色
    """
    try:
        log_info(f"用户{session['username']}更新用户{user_id}的角色")
        role_data = request.json
        
        if not role_data or 'role' not in role_data:
            log_warning("更新角色失败：无数据")
            return jsonify({
                'success': False,
                'error': '无数据',
                'message': '请提供角色数据'
            }), 400
        
        role = role_data['role']
        if role not in ['OWNER', 'ADMIN', 'USER']:
            log_warning(f"更新角色失败：无效角色{role}")
            return jsonify({
                'success': False,
                'error': '无效角色',
                'message': '角色必须是OWNER、ADMIN或USER'
            }), 400
        
        success, message = user_manager.update_user_role(user_id, role)
        
        if success:
            log_info(f"用户{user_id}角色更新成功为{role}")
            return jsonify({
                'success': True,
                'message': message
            })
        else:
            log_warning(f"用户{user_id}角色更新失败: {message}")
            return jsonify({
                'success': False,
                'error': message,
                'message': message
            }), 404
    except Exception as e:
        log_error(f"更新用户角色时出错: {e}")
        return jsonify({
            'success': False,
            'error': str(e),
            'message': '更新用户角色失败'
        }), 500


@app.route('/api/users/<int:user_id>/status', methods=['PUT'])
@require_permission('ADMIN')
def update_user_status(user_id):
    """
    更新用户状态
    """
    try:
        log_info(f"用户{session['username']}更新用户{user_id}的状态")
        status_data = request.json
        
        if not status_data or 'status' not in status_data:
            log_warning("更新状态失败：无数据")
            return jsonify({
                'success': False,
                'error': '无数据',
                'message': '请提供状态数据'
            }), 400
        
        status = status_data['status']
        if status not in ['active', 'inactive', 'banned']:
            log_warning(f"更新状态失败：无效状态{status}")
            return jsonify({
                'success': False,
                'error': '无效状态',
                'message': '状态必须是active、inactive或banned'
            }), 400
        
        success, message = user_manager.update_user_status(user_id, status)
        
        if success:
            log_info(f"用户{user_id}状态更新成功为{status}")
            return jsonify({
                'success': True,
                'message': message
            })
        else:
            log_warning(f"用户{user_id}状态更新失败: {message}")
            return jsonify({
                'success': False,
                'error': message,
                'message': message
            }), 404
    except Exception as e:
        log_error(f"更新用户状态时出错: {e}")
        return jsonify({
            'success': False,
            'error': str(e),
            'message': '更新用户状态失败'
        }), 500


@app.route('/api/messages', methods=['POST'])
def send_home_message():
    """
    主页用户发送消息
    """
    try:
        message_data = request.json
        
        if not message_data:
            log_warning("发送消息失败：无数据")
            return jsonify({
                'success': False,
                'error': '无数据',
                'message': '请提供消息数据'
            }), 400
        
        # 获取用户ID和消息内容
        user_id = message_data.get('user_id', 'unknown')
        message_content = message_data.get('content', '')
        
        if not message_content:
            log_warning("发送消息失败：无消息内容")
            return jsonify({
                'success': False,
                'error': '无消息内容',
                'message': '请提供消息内容'
            }), 400
        
        # 记录对话日志
        log_info(f"用户{user_id}在主页发送消息：{message_content}")
        
        # 这里可以添加对话处理逻辑
        # 例如保存对话到数据库或文件
        
        return jsonify({
            'success': True,
            'data': {
                'user_id': user_id,
                'content': message_content,
                'timestamp': time.strftime('%Y-%m-%d %H:%M:%S')
            },
            'message': '消息发送成功'
        })
    except Exception as e:
        log_error(f"发送消息时出错: {e}")
        return jsonify({
            'success': False,
            'error': str(e),
            'message': '发送消息失败'
        }), 500


@app.route('/api/scenarios/<int:script_id>/messages', methods=['POST'])
def send_message(script_id):
    """
    用户发送对话
    """
    try:
        log_info(f"接收到用户发送对话的请求，剧本ID: {script_id}")
        message_data = request.json
        
        if not message_data:
            log_warning("发送对话失败：无数据")
            return jsonify({
                'success': False,
                'error': '无数据',
                'message': '请提供对话数据'
            }), 400
        
        # 获取用户ID和消息内容
        user_id = message_data.get('user_id', 'unknown')
        message_content = message_data.get('content', '')
        
        if not message_content:
            log_warning("发送对话失败：无消息内容")
            return jsonify({
                'success': False,
                'error': '无消息内容',
                'message': '请提供对话内容'
            }), 400
        
        # 记录对话日志
        log_info(f"用户{user_id}向剧本{script_id}发送对话：{message_content}")
        
        # 这里可以添加对话处理逻辑
        # 例如保存对话到剧本文件或数据库
        
        return jsonify({
            'success': True,
            'data': {
                'script_id': script_id,
                'user_id': user_id,
                'content': message_content,
                'timestamp': time.strftime('%Y-%m-%d %H:%M:%S')
            },
            'message': '对话发送成功'
        })
    except Exception as e:
        log_error(f"发送对话时出错，剧本ID: {script_id}, 错误: {e}")
        return jsonify({
            'success': False,
            'error': str(e),
            'message': '发送对话失败'
        }), 500


# 静态文件服务
@app.route('/')
def serve_index():
    return send_from_directory('.', 'index.html')


@app.route('/<path:path>')
def serve_static(path):
    return send_from_directory('.', path)


if __name__ == '__main__':
    port = 8086
    print(f"启动服务器，监听端口：{port}")
    print("服务器启动中...")
    try:
        app.run(debug=True, host='127.0.0.1', port=port)
    except Exception as e:
        print(f"服务器启动失败: {e}")
