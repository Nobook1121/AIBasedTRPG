// 用户认证管理模块

let currentEditingScenarioId = null;

function setCurrentEditingScenarioId(id) {
    currentEditingScenarioId = id;
}
window.setCurrentEditingScenarioId = setCurrentEditingScenarioId;

function initAuth() {
    console.log('开始初始化用户认证功能');

    checkAuthStatus();

    const authTabs = document.querySelectorAll('.auth-tab');
    console.log('找到的认证标签数量:', authTabs.length);
    authTabs.forEach(tab => {
        tab.addEventListener('click', function() {
            const tabName = this.getAttribute('data-tab');
            switchAuthTab(tabName);
        });
    });

    document.addEventListener('click', function(e) {
        if (e.target.id === 'loginButton') {
            console.log('登录按钮被点击');
            login();
        }
    });

    document.addEventListener('click', function(e) {
        if (e.target.id === 'registerButton') {
            register();
        }
    });

    const logoutButton = document.getElementById('logoutButton');
    console.log('登出按钮元素:', logoutButton);
    if (logoutButton) {
        logoutButton.addEventListener('click', logout);
    }

    const closeAuthModal = document.getElementById('close-auth-modal');
    console.log('关闭认证弹窗按钮元素:', closeAuthModal);
    if (closeAuthModal) {
        closeAuthModal.addEventListener('click', closeAuthModalFunc);
    }

    const userInfo = document.getElementById('userInfo');
    console.log('用户信息元素:', userInfo);
    if (userInfo) {
        userInfo.addEventListener('click', toggleUserSettings);
        userInfo.addEventListener('keydown', function(event) {
            if (event.key === 'Enter' || event.key === ' ') {
                event.preventDefault();
                toggleUserSettings();
            }
        });
    }

    const closeSettingsPanel = document.getElementById('close-settings-panel');
    console.log('关闭设置面板按钮元素:', closeSettingsPanel);
    if (closeSettingsPanel) {
        closeSettingsPanel.addEventListener('click', closeSettingsPanelFunc);
    }

    const saveUserSettings = document.getElementById('saveUserSettings');
    console.log('保存用户设置按钮元素:', saveUserSettings);
    if (saveUserSettings) {
        saveUserSettings.addEventListener('click', saveUserSettingsFunc);
    }

    const avatarUpload = document.getElementById('avatarUpload');
    console.log('头像上传元素:', avatarUpload);
    if (avatarUpload) {
        avatarUpload.addEventListener('change', handleAvatarUpload);
    }

    console.log('用户认证功能初始化完成');
}

function handleAvatarUpload(e) {
    const file = e.target.files[0];
    if (file) {
        if (file.size > 2 * 1024 * 1024) {
            showNotification('头像文件大小不能超过2MB', 'error');
            return;
        }

        if (!file.type.startsWith('image/')) {
            showNotification('请上传图片文件', 'error');
            return;
        }

        const reader = new FileReader();
        reader.onload = function(e) {
            document.getElementById('avatarPreview').src = e.target.result;
        };
        reader.readAsDataURL(file);
    }
}

function switchAuthTab(tabName) {
    document.querySelectorAll('.auth-tab').forEach(tab => {
        tab.classList.remove('active');
    });
    const targetTab = document.querySelector(`.auth-tab[data-tab="${tabName}"]`);
    if (targetTab) targetTab.classList.add('active');

    document.querySelectorAll('.auth-form').forEach(form => {
        form.classList.remove('active');
    });
    const targetForm = document.getElementById(`${tabName}-form`);
    if (targetForm) targetForm.classList.add('active');
}

function checkAuthStatus() {
    TrpgApi.get('/api/auth/status')
        .then(data => {
            if (data.success) {
                showLoggedInState(data.data);
                closeAuthModalFunc();
            } else {
                showAuthModal();
            }
        })
        .catch(error => {
            console.error('检查认证状态失败:', error);
            showAuthModal();
        });
}

function showAuthModal() {
    document.getElementById('auth-modal').style.display = 'flex';
}

function closeAuthModalFunc() {
    document.getElementById('auth-modal').style.display = 'none';
}

function showLoggedInState(userData) {
    document.getElementById('userName').textContent = userData.username;
    if (userData.avatar) {
        document.querySelector('.user-avatar img').src = userData.avatar;
    }
    closeAuthModalFunc();
    closeSettingsPanelFunc();
}

function toggleUserSettings() {
    const settingsPanel = document.getElementById('user-settings-panel');
    if (settingsPanel.style.display === 'block') {
        closeSettingsPanelFunc();
    } else {
        openSettingsPanel();
    }
}

function openSettingsPanel() {
    document.getElementById('user-settings-panel').style.display = 'block';

    TrpgApi.get('/api/auth/status')
        .then(data => {
            if (data.success) {
                document.getElementById('editUsername').value = data.data.username;
                document.getElementById('editEmail').value = data.data.email;
                if (data.data.avatar) {
                    document.getElementById('avatarPreview').src = data.data.avatar;
                }
            }
        })
        .catch(error => {
            console.error('获取用户信息失败:', error);
        });
}

function closeSettingsPanelFunc() {
    document.getElementById('user-settings-panel').style.display = 'none';
}

function login() {
    const username = document.getElementById('loginUsername').value;
    const password = document.getElementById('loginPassword').value;
    const rememberMe = document.getElementById('rememberMe').checked;
    const stayLoggedIn = document.getElementById('stayLoggedIn').checked;
    const autoLogin = document.getElementById('autoLogin').checked;
    const messageElement = document.getElementById('loginMessage');

    if (!username || !password) {
        messageElement.textContent = '请输入用户名和密码';
        messageElement.style.color = 'red';
        return;
    }

    TrpgApi.post('/api/auth/login', {
        username,
        password,
        remember_me: rememberMe,
        stay_logged_in: stayLoggedIn,
        auto_login: autoLogin
    })
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

    TrpgApi.post('/api/auth/register', { username, password, email })
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

function logout() {
    TrpgApi.post('/api/auth/logout')
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

    const formData = new FormData();
    formData.append('username', username);
    formData.append('nickname', nickname);
    formData.append('email', email);
    if (password) {
        formData.append('password', password);
    }

    if (avatarInput.files && avatarInput.files[0]) {
        formData.append('avatar', avatarInput.files[0]);
    }

    TrpgApi.post('/api/auth/update', formData)
    .then(data => {
        if (data.success) {
            messageElement.textContent = '设置保存成功';
            messageElement.style.color = 'green';

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

    setTimeout(() => {
        messageElement.textContent = '';
    }, 3000);
}
