// 主脚本文件
import ScenarioController from './controllers/ScenarioController.js';
import ToolManager from '../tools/toolManager.js';

// 全局工具管理器
let toolManager;

// DOM 加载完成后执行
document.addEventListener('DOMContentLoaded', function() {
    // 初始化工具管理器
    toolManager = new ToolManager();
    
    // 初始化选项卡切换
    initTabs();
    
    // 初始化聊天功能
    initChat();
    
    // 初始化剧本管理
    initScenarioManagement();
    
    // 初始化角色卡管理
    initCharacterManagement();
    
    // 初始化骰子工具
    initDiceTool();
    
    // 初始化工具标签页
    initToolTabs();
    
    // 初始化用户认证功能
    initAuth();
});

// 初始化选项卡切换
function initTabs() {
    try {
        const navLinks = document.querySelectorAll('#sidebar .nav-link');
        const tabContents = document.querySelectorAll('.tab-content');
        
        if (navLinks.length === 0 || tabContents.length === 0) {
            console.error('无法找到导航链接或标签内容');
            return;
        }
        
        navLinks.forEach(link => {
            link.addEventListener('click', function(e) {
                e.preventDefault();
                
                // 移除所有活动状态
                navLinks.forEach(l => l.classList.remove('active'));
                tabContents.forEach(tab => tab.classList.remove('active'));
                
                // 添加当前活动状态
                this.classList.add('active');
                const tabId = this.getAttribute('data-tab');
                
                if (!tabId) {
                    console.error('导航链接缺少data-tab属性');
                    return;
                }
                
                const targetTab = document.getElementById(tabId);
                if (!targetTab) {
                    console.error(`找不到id为${tabId}的标签内容`);
                    return;
                }
                
                targetTab.classList.add('active');
                console.log(`切换到标签页: ${tabId}`);
            });
        });
        
        console.log('标签切换初始化成功');
    } catch (error) {
        console.error('初始化标签切换时出错:', error);
    }
}

// 初始化聊天功能
function initChat() {
    const chatInput = document.getElementById('chatInput');
    const sendButton = document.getElementById('sendButton');
    const chatHistory = document.getElementById('chatHistory');
    
    // 发送消息
    function sendMessage() {
        const message = chatInput.value.trim();
        if (message) {
            // 检查是否是命令
            const commandResult = toolManager.handleCommand(message);
            
            if (commandResult) {
                // 处理命令
                addMessage('player', '我', message);
                chatInput.value = '';
                
                // 检查是否是骰子命令
                if (message.toLowerCase().startsWith('/dice')) {
                    // 显示骰娘的回复
                    setTimeout(() => {
                        addMessage('dice', '骰娘', commandResult);
                    }, 500);
                } else {
                    // 显示系统回复
                    setTimeout(() => {
                        addMessage('system', '系统', commandResult);
                    }, 500);
                }
            } else {
                // 添加玩家消息
                addMessage('player', '我', message);
                chatInput.value = '';
                
                // 发送消息到后端API
                fetch('/api/messages', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json'
                    },
                    body: JSON.stringify({
                        content: message,
                        user_id: 'user_' + Date.now()
                    })
                })
                .then(response => response.json())
                .then(data => {
                    console.log('消息发送成功:', data);
                    // 模拟 AI 回复
                    setTimeout(() => {
                        addMessage('kp', 'KP', '这是 AI 的回复...');
                    }, 1000);
                })
                .catch(error => {
                    console.error('消息发送失败:', error);
                    // 即使发送失败，也显示模拟回复
                    setTimeout(() => {
                        addMessage('kp', 'KP', '这是 AI 的回复...');
                    }, 1000);
                });
            }
        }
    }
    
    // 添加消息到聊天历史
    function addMessage(type, sender, content) {
        const messageDiv = document.createElement('div');
        
        // 根据消息类型设置不同的样式类
        let messageClass = '';
        let avatarSrc = '';
        
        switch (type) {
            case 'player':
                messageClass = 'player-message';
                // 使用当前用户的头像，如果没有则使用默认头像
                const userAvatar = document.querySelector('.user-avatar img')?.src || 'https://via.placeholder.com/40';
                avatarSrc = userAvatar;
                break;
            case 'kp':
                messageClass = 'kp-message';
                // 使用KP的专属默认头像
                avatarSrc = '/assets/avatars/default_kp.jpg';
                break;
            case 'dice':
                messageClass = 'dice-message';
                // 使用骰娘的专属头像
                avatarSrc = '/assets/avatars/default_dice.jpg';
                // 强制设置发送者为骰娘
                sender = '骰娘';
                break;
            case 'system':
                messageClass = 'other-message';
                // 使用系统的专属默认头像
                avatarSrc = '/assets/avatars/default_system.jpg';
                break;
            case 'other':
                messageClass = 'other-message';
                avatarSrc = 'https://via.placeholder.com/40';
                break;
            default:
                messageClass = 'other-message';
                avatarSrc = 'https://via.placeholder.com/40';
        }
        
        messageDiv.className = `message ${messageClass}`;
        
        const now = new Date();
        const time = `${now.getHours().toString().padStart(2, '0')}:${now.getMinutes().toString().padStart(2, '0')}`;
        
        // 构建消息HTML，包含头像、发送者、时间和内容
        messageDiv.innerHTML = `
            <div class="message-avatar">
                <img src="${avatarSrc}" alt="${sender}">
            </div>
            <div class="message-content-container">
                <div class="message-header">
                    <span class="message-sender">${sender}</span>
                    <span class="message-time">${time}</span>
                </div>
                <div class="message-content">${content}</div>
            </div>
        `;
        
        chatHistory.appendChild(messageDiv);
        
        // 自动滚动到最新消息
        setTimeout(() => {
            chatHistory.scrollTop = chatHistory.scrollHeight;
        }, 100);
    }
    
    // 绑定事件
    sendButton.addEventListener('click', sendMessage);
    chatInput.addEventListener('keypress', function(e) {
        if (e.key === 'Enter') {
            sendMessage();
        }
    });
}

// 初始化剧本管理
function initScenarioManagement() {
    // 创建剧本控制器实例
    new ScenarioController();
    
    // 绑定封面上传事件 - 使用事件委托，确保动态添加的元素也能响应
    document.addEventListener('change', function(e) {
        if (e.target.id === 'coverUpload') {
            handleCoverUpload(e);
        }
    });
}

// 全局变量，用于存储当前编辑的剧本ID
let currentEditingScenarioId = null;

// 设置当前编辑的剧本ID
function setCurrentEditingScenarioId(id) {
    currentEditingScenarioId = id;
}

// 处理封面上传
function handleCoverUpload(e) {
    const file = e.target.files[0];
    if (file) {
        // 检查文件大小（限制为5MB）
        if (file.size > 5 * 1024 * 1024) {
            showNotification('封面文件大小不能超过5MB', 'error');
            return;
        }
        
        // 检查文件类型
        if (!file.type.startsWith('image/')) {
            showNotification('请上传图片文件', 'error');
            return;
        }
        
        // 预览封面
        const reader = new FileReader();
        reader.onload = function(e) {
            document.getElementById('coverPreview').src = e.target.result;
        };
        reader.readAsDataURL(file);
        
        // 保存文件到隐藏字段，以便在保存剧本时使用
        window.uploadedCoverFile = file;
        
        // 上传封面到服务器
        const formData = new FormData();
        formData.append('cover', file);
        // 传递剧本标题到服务器
        const scenarioTitle = document.getElementById('scenarioTitle').value.trim() || 'unknown_scenario';
        formData.append('scenario_title', scenarioTitle);
        
        fetch('/api/scenarios/cover', {
            method: 'POST',
            body: formData
        })
        .then(response => {
            if (!response.ok) {
                return response.json().then(err => {
                    throw new Error(err.message || '上传失败');
                });
            }
            return response.json();
        })
        .then(data => {
            if (data.success) {
                showNotification('封面上传成功', 'success');
                // 保存封面URL到隐藏字段，以便在保存剧本时使用
                document.getElementById('scenarioCoverUrl').value = data.data.cover_url;
            } else {
                showNotification(data.message, 'error');
            }
        })
        .catch(error => {
            console.error('上传封面失败:', error);
            showNotification('上传封面失败: ' + error.message, 'error');
        });
    }
}

// 初始化角色卡管理
function initCharacterManagement() {
    const createCharacterBtn = document.getElementById('createCharacter');
    const saveCharacterBtn = document.getElementById('saveCharacter');
    const characterModal = new bootstrap.Modal(document.getElementById('characterModal'));
    const characterList = document.getElementById('characterList');
    
    // 角色卡数据
    let characters = [];
    
    // 打开创建角色卡模态框
    createCharacterBtn.addEventListener('click', function() {
        document.getElementById('characterName').value = '';
        document.getElementById('playerId').value = '';
        document.getElementById('characterBio').value = '';
        document.getElementById('strength').value = '';
        document.getElementById('constitution').value = '';
        document.getElementById('dexterity').value = '';
        document.getElementById('intelligence').value = '';
        document.getElementById('willpower').value = '';
        document.getElementById('luck').value = '';
        document.getElementById('characterSkills').value = '';
        characterModal.show();
    });
    
    // 保存角色卡
    saveCharacterBtn.addEventListener('click', function() {
        const character = {
            id: Date.now(),
            name: document.getElementById('characterName').value,
            playerId: document.getElementById('playerId').value,
            bio: document.getElementById('characterBio').value,
            attributes: {
                strength: document.getElementById('strength').value,
                constitution: document.getElementById('constitution').value,
                dexterity: document.getElementById('dexterity').value,
                intelligence: document.getElementById('intelligence').value,
                willpower: document.getElementById('willpower').value,
                luck: document.getElementById('luck').value
            },
            skills: document.getElementById('characterSkills').value
        };
        
        characters.push(character);
        updateCharacterList();
        characterModal.hide();
    });
    
    // 更新角色卡列表
    function updateCharacterList() {
        characterList.innerHTML = '';
        
        characters.forEach(character => {
            const card = document.createElement('div');
            card.className = 'character-card';
            card.innerHTML = `
                <h5>${character.name}</h5>
                <p>玩家ID: ${character.playerId}</p>
                <p>简介: ${character.bio.substring(0, 50)}${character.bio.length > 50 ? '...' : ''}</p>
                <div class="character-card-actions">
                    <button class="btn btn-sm btn-primary">查看</button>
                    <button class="btn btn-sm btn-secondary">编辑</button>
                    <button class="btn btn-sm btn-danger">删除</button>
                </div>
            `;
            characterList.appendChild(card);
        });
    }
    
    // 加载模拟角色卡数据
    loadMockCharacters();
    
    function loadMockCharacters() {
        characters = [
            {
                id: 1,
                name: '侦探',
                playerId: '玩家1',
                bio: '一名经验丰富的侦探，擅长调查和推理。',
                attributes: {
                    strength: 40,
                    constitution: 50,
                    dexterity: 60,
                    intelligence: 80,
                    willpower: 70,
                    luck: 50
                },
                skills: '侦查:70,推理:80,格斗:40'
            },
            {
                id: 2,
                name: '医生',
                playerId: '玩家2',
                bio: '一名专业的医生，擅长治疗和解剖。',
                attributes: {
                    strength: 30,
                    constitution: 60,
                    dexterity: 50,
                    intelligence: 70,
                    willpower: 60,
                    luck: 40
                },
                skills: '医学:80,急救:70,说服:50'
            }
        ];
        updateCharacterList();
    }
}

// 初始化骰子工具
function initDiceTool() {
    const rollDiceBtn = document.getElementById('rollDice');
    const diceType = document.getElementById('diceType');
    const diceResult = document.getElementById('diceResult');
    
    rollDiceBtn.addEventListener('click', function() {
        const type = diceType.value;
        const sides = parseInt(type.replace('d', ''));
        const result = Math.floor(Math.random() * sides) + 1;
        
        diceResult.textContent = `结果: ${result}`;
    });
}

// 初始化工具标签页
function initToolTabs() {
    const toolTabs = document.querySelectorAll('.tool-tab');
    const toolContents = document.querySelectorAll('.tool-content');
    
    if (toolTabs.length === 0 || toolContents.length === 0) {
        console.error('无法找到工具标签或工具内容');
        return;
    }
    
    toolTabs.forEach(tab => {
        tab.addEventListener('click', function() {
            const toolName = this.getAttribute('data-tool');
            
            // 移除所有活动状态
            toolTabs.forEach(t => t.classList.remove('active'));
            toolContents.forEach(content => content.classList.remove('active'));
            
            // 添加当前活动状态
            this.classList.add('active');
            const targetContent = document.getElementById(`${toolName}-tool-content`);
            if (targetContent) {
                targetContent.classList.add('active');
            }
        });
    });
    
    console.log('工具标签页初始化成功');
}

// 初始化用户认证功能
function initAuth() {
    // 检查认证状态
    checkAuthStatus();
    
    // 绑定登录/注册切换标签
    const authTabs = document.querySelectorAll('.auth-tab');
    authTabs.forEach(tab => {
        tab.addEventListener('click', function() {
            const tabName = this.getAttribute('data-tab');
            switchAuthTab(tabName);
        });
    });
    
    // 绑定登录按钮事件
    const loginButton = document.getElementById('loginButton');
    if (loginButton) {
        loginButton.addEventListener('click', login);
    }
    
    // 绑定注册按钮事件
    const registerButton = document.getElementById('registerButton');
    if (registerButton) {
        registerButton.addEventListener('click', register);
    }
    
    // 绑定登出按钮事件
    const logoutButton = document.getElementById('logoutButton');
    if (logoutButton) {
        logoutButton.addEventListener('click', logout);
    }
    
    // 绑定关闭弹窗按钮事件
    const closeAuthModal = document.getElementById('close-auth-modal');
    if (closeAuthModal) {
        closeAuthModal.addEventListener('click', closeAuthModalFunc);
    }
    
    // 绑定用户信息点击事件
    const userInfo = document.getElementById('userInfo');
    if (userInfo) {
        userInfo.addEventListener('click', toggleUserSettings);
    }
    
    // 绑定关闭设置面板按钮事件
    const closeSettingsPanel = document.getElementById('close-settings-panel');
    if (closeSettingsPanel) {
        closeSettingsPanel.addEventListener('click', closeSettingsPanelFunc);
    }
    
    // 绑定保存用户设置按钮事件
    const saveUserSettings = document.getElementById('saveUserSettings');
    if (saveUserSettings) {
        saveUserSettings.addEventListener('click', saveUserSettingsFunc);
    }
    
    // 绑定头像上传事件
    const avatarUpload = document.getElementById('avatarUpload');
    if (avatarUpload) {
        avatarUpload.addEventListener('change', handleAvatarUpload);
    }
}

// 处理头像上传
function handleAvatarUpload(e) {
    const file = e.target.files[0];
    if (file) {
        // 检查文件大小（限制为2MB）
        if (file.size > 2 * 1024 * 1024) {
            showNotification('头像文件大小不能超过2MB', 'error');
            return;
        }
        
        // 检查文件类型
        if (!file.type.startsWith('image/')) {
            showNotification('请上传图片文件', 'error');
            return;
        }
        
        // 预览头像
        const reader = new FileReader();
        reader.onload = function(e) {
            document.getElementById('avatarPreview').src = e.target.result;
        };
        reader.readAsDataURL(file);
    }
}

// 切换登录/注册标签
function switchAuthTab(tabName) {
    // 更新标签状态
    document.querySelectorAll('.auth-tab').forEach(tab => {
        tab.classList.remove('active');
    });
    document.querySelector(`.auth-tab[data-tab="${tabName}"]`).classList.add('active');
    
    // 更新表单显示
    document.querySelectorAll('.auth-form').forEach(form => {
        form.classList.remove('active');
    });
    document.getElementById(`${tabName}-form`).classList.add('active');
}

// 检查认证状态
function checkAuthStatus() {
    fetch('/api/auth/status')
        .then(response => response.json())
        .then(data => {
            if (data.success) {
                // 已登录
                showLoggedInState(data.data);
                closeAuthModalFunc();
            } else {
                // 未登录
                showAuthModal();
            }
        })
        .catch(error => {
            console.error('检查认证状态失败:', error);
            showAuthModal();
        });
}

// 显示认证弹窗
function showAuthModal() {
    document.getElementById('auth-modal').style.display = 'flex';
}

// 关闭认证弹窗
function closeAuthModalFunc() {
    document.getElementById('auth-modal').style.display = 'none';
}

// 显示已登录状态
function showLoggedInState(userData) {
    // 更新用户信息区域
    document.getElementById('userName').textContent = userData.username;
    // 更新用户头像
    if (userData.avatar) {
        document.querySelector('.user-avatar img').src = userData.avatar;
    }
    
    // 隐藏认证弹窗
    closeAuthModalFunc();
    
    // 隐藏用户设置面板
    closeSettingsPanelFunc();
}

// 切换用户设置面板
function toggleUserSettings() {
    const settingsPanel = document.getElementById('user-settings-panel');
    if (settingsPanel.style.display === 'block') {
        closeSettingsPanelFunc();
    } else {
        openSettingsPanel();
    }
}

// 打开用户设置面板
function openSettingsPanel() {
    document.getElementById('user-settings-panel').style.display = 'block';
    
    // 加载用户信息
    fetch('/api/auth/status')
        .then(response => response.json())
        .then(data => {
            if (data.success) {
                document.getElementById('editUsername').value = data.data.username;
                document.getElementById('editEmail').value = data.data.email;
                // 加载用户头像
                if (data.data.avatar) {
                    document.getElementById('avatarPreview').src = data.data.avatar;
                }
            }
        })
        .catch(error => {
            console.error('获取用户信息失败:', error);
        });
}

// 关闭用户设置面板
function closeSettingsPanelFunc() {
    document.getElementById('user-settings-panel').style.display = 'none';
}

// 登录
function login() {
    const username = document.getElementById('loginUsername').value;
    const password = document.getElementById('loginPassword').value;
    const rememberMe = document.getElementById('rememberMe').checked;
    const stayLoggedIn = document.getElementById('stayLoggedIn').checked;
    const messageElement = document.getElementById('loginMessage');
    
    if (!username || !password) {
        messageElement.textContent = '请输入用户名和密码';
        messageElement.style.color = 'red';
        return;
    }
    
    fetch('/api/auth/login', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json'
        },
        body: JSON.stringify({ 
            username, 
            password,
            remember_me: rememberMe,
            stay_logged_in: stayLoggedIn
        })
    })
    .then(response => response.json())
    .then(data => {
        if (data.success) {
            messageElement.textContent = '登录成功';
            messageElement.style.color = 'green';
            showLoggedInState(data.data);
        } else {
            messageElement.textContent = data.message;
            messageElement.style.color = 'red';
        }
    })
    .catch(error => {
        console.error('登录失败:', error);
        messageElement.textContent = '登录失败，请稍后重试';
        messageElement.style.color = 'red';
    });
}

// 注册
function register() {
    const username = document.getElementById('registerUsername').value;
    const password = document.getElementById('registerPassword').value;
    const email = document.getElementById('registerEmail').value;
    const messageElement = document.getElementById('registerMessage');
    
    if (!username || !password || !email) {
        messageElement.textContent = '请输入用户名、密码和邮箱';
        messageElement.style.color = 'red';
        return;
    }
    
    fetch('/api/auth/register', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json'
        },
        body: JSON.stringify({ username, password, email })
    })
    .then(response => response.json())
    .then(data => {
        if (data.success) {
            messageElement.textContent = '注册成功，请登录';
            messageElement.style.color = 'green';
            switchAuthTab('login');
        } else {
            messageElement.textContent = data.message;
            messageElement.style.color = 'red';
        }
    })
    .catch(error => {
        console.error('注册失败:', error);
        messageElement.textContent = '注册失败，请稍后重试';
        messageElement.style.color = 'red';
    });
}

// 登出
function logout() {
    fetch('/api/auth/logout', {
        method: 'POST'
    })
    .then(response => response.json())
    .then(data => {
        if (data.success) {
            document.getElementById('userName').textContent = '未登录';
            closeSettingsPanelFunc();
            showAuthModal();
        }
    })
    .catch(error => {
        console.error('登出失败:', error);
    });
}

// 保存用户设置
function saveUserSettingsFunc() {
    const username = document.getElementById('editUsername').value;
    const nickname = document.getElementById('editNickname').value;
    const email = document.getElementById('editEmail').value;
    const password = document.getElementById('editPassword').value;
    const confirmPassword = document.getElementById('confirmPassword').value;
    const messageElement = document.getElementById('settingsMessage');
    const avatarInput = document.getElementById('avatarUpload');
    
    if (!username || !email) {
        messageElement.textContent = '请输入用户名和邮箱';
        messageElement.style.color = 'red';
        return;
    }
    
    if (password && password !== confirmPassword) {
        messageElement.textContent = '两次输入的密码不一致';
        messageElement.style.color = 'red';
        return;
    }
    
    // 创建FormData对象
    const formData = new FormData();
    formData.append('username', username);
    formData.append('nickname', nickname);
    formData.append('email', email);
    if (password) {
        formData.append('password', password);
    }
    
    // 添加头像文件（如果有）
    if (avatarInput.files && avatarInput.files[0]) {
        formData.append('avatar', avatarInput.files[0]);
    }
    
    // 发送更新请求
    fetch('/api/auth/update', {
        method: 'POST',
        body: formData
    })
    .then(response => response.json())
    .then(data => {
        if (data.success) {
            messageElement.textContent = '设置保存成功';
            messageElement.style.color = 'green';
            
            // 更新用户头像
            if (data.data && data.data.avatar) {
                document.querySelector('.user-avatar img').src = data.data.avatar;
            }
        } else {
            messageElement.textContent = data.message;
            messageElement.style.color = 'red';
        }
    })
    .catch(error => {
        console.error('更新用户设置失败:', error);
        messageElement.textContent = '更新失败，请稍后重试';
        messageElement.style.color = 'red';
    });
    
    // 3秒后关闭消息
    setTimeout(() => {
        messageElement.textContent = '';
    }, 3000);
}