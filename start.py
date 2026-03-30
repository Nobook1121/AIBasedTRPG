#!/usr/bin/env python3
"""
AI TRPG 系统启动脚本
安装依赖并启动服务器
"""

import os
import sys
import subprocess
import platform


def install_dependencies():
    """
    安装项目依赖
    """
    print("正在安装依赖...")
    try:
        # 检查是否安装了pip
        subprocess.run([sys.executable, "-m", "pip", "--version"], check=True, capture_output=True)
        
        # 安装依赖
        subprocess.run([sys.executable, "-m", "pip", "install", "-r", "requirements.txt"], 
                      check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        print("依赖安装成功！")
        return True
    except subprocess.CalledProcessError as e:
        print(f"依赖安装失败: {e.stderr.decode('utf-8')}")
        return False
    except Exception as e:
        print(f"安装依赖时出错: {e}")
        return False


def start_server():
    """
    启动服务器
    """
    print("正在启动服务器...")
    try:
        # 启动Flask服务器
        server_process = subprocess.Popen([sys.executable, "server.py"])
        print("服务器启动成功！")
        print("访问地址: http://localhost:8080")
        print("按 Ctrl+C 停止服务器")
        
        # 等待服务器进程
        server_process.wait()
    except KeyboardInterrupt:
        print("\n正在停止服务器...")
        server_process.terminate()
        server_process.wait()
        print("服务器已停止")
    except Exception as e:
        print(f"启动服务器时出错: {e}")


def main():
    """
    主函数
    """
    print("=== AI TRPG 系统 ===")
    print("正在准备启动...")
    
    # 检查requirements.txt文件
    if not os.path.exists("requirements.txt"):
        print("错误: requirements.txt 文件不存在")
        return
    
    # 检查server.py文件
    if not os.path.exists("server.py"):
        print("错误: server.py 文件不存在")
        return
    
    # 安装依赖
    if not install_dependencies():
        print("依赖安装失败，无法启动服务器")
        return
    
    # 启动服务器
    start_server()


if __name__ == "__main__":
    main()
