// @ts-nocheck
// User authentication module.

let currentEditingScenarioId = null;

function setCurrentEditingScenarioId(id) {
    currentEditingScenarioId = id;
}
window.setCurrentEditingScenarioId = setCurrentEditingScenarioId;

async function initAuth() {
    bindAuthEvents();
    prefillRememberedUsername();
    return checkAuthStatus();
}

function prefillRememberedUsername() {
    const rememberedUsername = TrpgCookies.get('trpg_last_username');
    if (rememberedUsername) {
        const loginUsername = document.getElementById('loginUsername');
        if (loginUsername) loginUsername.value = rememberedUsername;
    }
}

function bindAuthEvents() {
    document.querySelectorAll('.auth-tab').forEach(tab => {
        tab.addEventListener('click', function() {
            switchAuthTab(this.getAttribute('data-tab'));
        });
    });

    document.addEventListener('click', function(e) {
        if (e.target.id === 'loginButton') {
            login();
        }
        if (e.target.id === 'registerButton') {
            register();
        }
    });

    document.getElementById('logoutButton')?.addEventListener('click', logout);
    document.getElementById('close-auth-modal')?.addEventListener('click', closeAuthModalFunc);
    document.getElementById('close-settings-panel')?.addEventListener('click', closeSettingsPanelFunc);
    document.getElementById('saveUserSettings')?.addEventListener('click', saveUserSettingsFunc);
    document.getElementById('avatarUpload')?.addEventListener('change', handleAvatarUpload);

    const userInfo = document.getElementById('userInfo');
    userInfo?.addEventListener('click', toggleUserSettings);
    userInfo?.addEventListener('keydown', function(event) {
        if (event.key === 'Enter' || event.key === ' ') {
            event.preventDefault();
            toggleUserSettings();
        }
    });
}

function handleAvatarUpload(e) {
    const file = e.target.files[0];
    if (!file) return;

    if (file.size > 2 * 1024 * 1024) {
        showNotification('头像文件大小不能超过 2MB', 'error');
        return;
    }
    if (!file.type.startsWith('image/')) {
        showNotification('请上传图片文件', 'error');
        return;
    }

    const reader = new FileReader();
    reader.onload = function(event) {
        document.getElementById('avatarPreview').src = event.target.result;
    };
    reader.readAsDataURL(file);
}

function switchAuthTab(tabName) {
    document.querySelectorAll('.auth-tab').forEach(tab => tab.classList.remove('active'));
    document.querySelector(`.auth-tab[data-tab="${tabName}"]`)?.classList.add('active');

    document.querySelectorAll('.auth-form').forEach(form => form.classList.remove('active'));
    document.getElementById(`${tabName}-form`)?.classList.add('active');
}

async function checkAuthStatus() {
    try {
        const data = await TrpgApi.get('/api/auth/status');
        if (data.success) {
            showLoggedInState(data.data);
            return true;
        }
    } catch (error) {
        console.debug('未登录或会话已失效:', error);
    }

    window.currentUser = null;
    showAuthModal();
    return false;
}

function showAuthModal() {
    document.getElementById('auth-modal').style.display = 'flex';
}

function closeAuthModalFunc() {
    document.getElementById('auth-modal').style.display = 'none';
}

function showLoggedInState(userData) {
    window.currentUser = userData;
    document.getElementById('userName').textContent = userData.username;
    document.querySelector('.user-avatar img').src = userData.avatar || '/assets/avatars/default.jpg';
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
            if (!data.success) return;
            document.getElementById('editUsername').value = data.data.username;
            document.getElementById('editEmail').value = data.data.email;
            document.getElementById('avatarPreview').src = data.data.avatar || '/assets/avatars/default.jpg';
        })
        .catch(error => console.error('获取用户信息失败:', error));
}

function closeSettingsPanelFunc() {
    document.getElementById('user-settings-panel').style.display = 'none';
}

async function login() {
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

    try {
        const data = await TrpgApi.post('/api/auth/login', {
            username,
            password,
            remember_me: rememberMe,
            stay_logged_in: stayLoggedIn,
            auto_login: autoLogin,
        });

        if (!data.success) {
            messageElement.textContent = data.message;
            messageElement.style.color = 'red';
            return;
        }

        messageElement.textContent = '登录成功';
        messageElement.style.color = 'green';
        showLoggedInState(data.data);
        TrpgCookies.set('trpg_last_username', data.data.username);
        window.reconnectSocket?.();
        window.clearCurrentRoom?.();
        window.clearChatMessages?.();
        await window.autoLoadLastRoom?.();
    } catch (error) {
        console.error('登录失败:', error);
        messageElement.textContent = '登录失败，请稍后重试';
        messageElement.style.color = 'red';
    }
}

async function register() {
    const username = document.getElementById('registerUsername').value;
    const password = document.getElementById('registerPassword').value;
    const email = document.getElementById('registerEmail').value;
    const messageElement = document.getElementById('registerMessage');

    if (!username || !password || !email) {
        messageElement.textContent = '请输入用户名、密码和邮箱';
        messageElement.style.color = 'red';
        return;
    }

    try {
        const data = await TrpgApi.post('/api/auth/register', { username, password, email });
        if (data.success) {
            messageElement.textContent = '注册成功，请登录';
            messageElement.style.color = 'green';
            switchAuthTab('login');
        } else {
            messageElement.textContent = data.message;
            messageElement.style.color = 'red';
        }
    } catch (error) {
        console.error('注册失败:', error);
        messageElement.textContent = '注册失败，请稍后重试';
        messageElement.style.color = 'red';
    }
}

async function logout() {
    try {
        const data = await TrpgApi.post('/api/auth/logout');
        if (!data.success) return;
    } catch (error) {
        console.error('登出失败:', error);
    }

    window.disconnectSocket?.();
    window.clearCurrentRoom?.();
    window.clearChatMessages?.();
    window.currentUser = null;
    document.getElementById('userName').textContent = '未登录';
    document.querySelector('.user-avatar img').src = '/assets/avatars/default.jpg';
    closeSettingsPanelFunc();
    showAuthModal();
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
    if (password) formData.append('password', password);
    if (avatarInput.files && avatarInput.files[0]) {
        formData.append('avatar', avatarInput.files[0]);
    }

    TrpgApi.post('/api/auth/update', formData)
        .then(data => {
            if (data.success) {
                messageElement.textContent = '设置保存成功';
                messageElement.style.color = 'green';
                showLoggedInState({ ...window.currentUser, ...data.data });
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
