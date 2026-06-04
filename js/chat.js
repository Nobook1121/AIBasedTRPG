// 聊天功能模块

let isAIThinking = false;
let messageTimestamps = [];
let pendingMessages = [];
let aiName = 'KP';
let socket = null;

function initChat() {
    const chatInput = document.getElementById('chatInput');
    const sendButton = document.getElementById('sendButton');
    const chatHistory = document.getElementById('chatHistory');

    updateAIHint();

    initWebSocket();

    function sendMessage() {
        const rawMessage = chatInput.value.trim();
        if (!rawMessage) return;

        if (isAIThinking) {
            const enableLock = document.getElementById('enableAIResponseLock')?.checked;
            if (enableLock) {
                showNotification('请等待AI回复完成后再发送消息', 'error');
                return;
            }
        }

        const rateLimit = parseInt(document.getElementById('messageRateLimit')?.value) || 0;
        if (rateLimit > 0) {
            const now = Date.now();
            messageTimestamps = messageTimestamps.filter(ts => now - ts < 60000);

            if (messageTimestamps.length >= rateLimit) {
                showNotification(`消息发送过于频繁，请稍后再试（限制${rateLimit}条/分钟）`, 'error');
                return;
            }
            messageTimestamps.push(now);
        }

        const isAIMessage = rawMessage.startsWith(`@${aiName}`);
        const message = isAIMessage ? rawMessage.substring(aiName.length + 1).trim() : rawMessage;

        if (!message) {
            showNotification('请输入消息内容', 'error');
            return;
        }

        const commandResult = toolManager.handleCommand(message);

        if (commandResult) {
            addMessage('player', '我', message);
            chatInput.value = '';

            broadcastMessage('player', '我', message);

            if (message.toLowerCase().startsWith('/dice')) {
                setTimeout(() => {
                    addMessage('dice', '骰娘', commandResult);
                    broadcastMessage('dice', '骰娘', commandResult);
                }, 500);
            } else {
                setTimeout(() => {
                    addMessage('system', '系统', commandResult);
                    broadcastMessage('system', '系统', commandResult);
                }, 500);
            }
            return;
        }

        if (!isAIMessage) {
            addMessage('player', '我', message);
            chatInput.value = '';
            broadcastMessage('player', '我', message);
            return;
        }

        pendingMessages.push({ sender: 'player', content: message, time: new Date().toLocaleTimeString() });

        addMessage('player', '我', message);
        broadcastMessage('player', '我', message);
        chatInput.value = '';

        if (isAIThinking) {
            showNotification('消息已添加到队列，请等待AI回复完成后发送', 'info');
            return;
        }

        sendToAI();
    }

    function sendToAI() {
        if (pendingMessages.length === 0) return;

        isAIThinking = true;
        updateInputState();

        const thinkingMessageId = Date.now();
        const startTime = Date.now();
        addThinkingMessage(thinkingMessageId);

        fetch('/api/chat', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                content: pendingMessages.map(m => m.content).join('\n'),
                messages: pendingMessages,
                user_id: 'user_' + Date.now()
            })
        })
        .then(response => {
            console.log('API响应状态:', response.status);
            if (!response.ok) {
                throw new Error('API请求失败: ' + response.status);
            }
            return response.json();
        })
        .then(data => {
            console.log('消息发送成功:', data);
            const endTime = Date.now();
            const processingTime = Math.round((endTime - startTime) / 1000);
            const tokenCount = data.token_count || null;

            let messageContent = '';
            if (data.content) {
                messageContent = data.content;
            } else if (data.error) {
                messageContent = 'AI 回复失败: ' + data.error;
            } else {
                messageContent = 'AI 回复失败: 未知错误';
            }

            pendingMessages = [];
            replaceThinkingMessage(thinkingMessageId, messageContent, processingTime, tokenCount);

            broadcastMessage('kp', 'KP', messageContent);

            isAIThinking = false;
            updateInputState();
        })
        .catch(error => {
            console.error('消息发送失败:', error);
            const endTime = Date.now();
            const processingTime = Math.round((endTime - startTime) / 1000);

            replaceThinkingMessage(thinkingMessageId, 'AI 回复失败: ' + error.message, processingTime, null);

            pendingMessages = [];
            isAIThinking = false;
            updateInputState();
        });
    }

    function updateInputState() {
        const chatInput = document.getElementById('chatInput');
        const sendButton = document.getElementById('sendButton');

        if (isAIThinking) {
            chatInput.disabled = true;
            sendButton.disabled = true;
        } else {
            chatInput.disabled = false;
            sendButton.disabled = false;
        }
    }

    sendButton.addEventListener('click', sendMessage);
    chatInput.addEventListener('keypress', function(e) {
        if (e.key === 'Enter') {
            sendMessage();
        }
    });
}

function updateAIHint() {
    const aiHint = document.getElementById('aiHint');
    if (aiHint) {
        aiHint.textContent = `@${aiName}`;
    }
}

function setAIName(name) {
    aiName = name;
    updateAIHint();
}

function renderMarkdown(content) {
    try {
        if (typeof marked === 'function') {
            marked.setOptions({
                breaks: true,
                gfm: true,
                headerIds: false,
                mangle: false
            });
            return marked(content);
        } else if (marked && typeof marked.parse === 'function') {
            return marked.parse(content, {
                breaks: true,
                gfm: true,
                headerIds: false,
                mangle: false
            });
        } else {
            console.warn('marked库不可用，返回原始内容');
            return content;
        }
    } catch (error) {
        console.error('Markdown渲染失败:', error);
        return content;
    }
}

function getAvatarSrc(type) {
    switch (type) {
        case 'player':
            return document.querySelector('.user-avatar img')?.src || 'https://via.placeholder.com/40';
        case 'kp':
            return '/assets/avatars/default_kp.jpg';
        case 'dice':
            return `/assets/avatars/default_dice.jpg?t=${Date.now()}`;
        case 'system':
            return '/assets/avatars/default_system.jpg';
        default:
            return 'https://via.placeholder.com/40';
    }
}

function getMessageClass(type) {
    switch (type) {
        case 'player': return 'player-message';
        case 'kp': return 'kp-message';
        case 'dice': return 'dice-message';
        case 'system': return 'other-message';
        case 'other': return 'other-message';
        default: return 'other-message';
    }
}

function addMessage(type, sender, content, messageId, isThinking, processingTime, tokenCount) {
    messageId = messageId || Date.now();
    const chatHistory = document.getElementById('chatHistory');

    hideWelcomeText();

    let messageClass = getMessageClass(type);
    let avatarSrc = getAvatarSrc(type);

    if (type === 'dice') {
        sender = '骰娘';
    }

    if (isThinking) {
        messageClass += ' thinking';
    }

    const messageDiv = document.createElement('div');
    messageDiv.className = `message ${messageClass}`;
    messageDiv.setAttribute('data-id', messageId);

    const now = new Date();
    const time = `${now.getHours().toString().padStart(2, '0')}:${now.getMinutes().toString().padStart(2, '0')}`;

    const renderedContent = isThinking ? content : renderMarkdown(content);

    let messageHTML = `
        <div class="message-avatar">
            <img src="${avatarSrc}" alt="${sender}">
        </div>
        <div class="message-content-container">
            <div class="message-header">
                <span class="message-sender">${sender}</span>
                <span class="message-time">${time}</span>
            </div>
            <div class="message-content markdown-body">${renderedContent}</div>
    `;

    if (processingTime !== null && type !== 'player') {
        let displayText = `已耗时: ${processingTime}秒`;
        if (tokenCount !== null) {
            displayText += ` 消耗Token：${tokenCount}`;
        }
        messageHTML += `<div class="processing-time">${displayText}</div>`;
    }

    messageHTML += '</div>';
    messageDiv.innerHTML = messageHTML;
    chatHistory.appendChild(messageDiv);

    setTimeout(() => {
        chatHistory.scrollTop = chatHistory.scrollHeight;
    }, 100);

    return messageId;
}

function removeMessage(messageId) {
    const messageDiv = document.querySelector(`.message[data-id="${messageId}"]`);
    if (messageDiv) {
        messageDiv.remove();
    }
}

function addThinkingMessage(messageId) {
    hideWelcomeText();

    const chatHistory = document.getElementById('chatHistory');
    const messageDiv = document.createElement('div');
    messageDiv.className = 'message kp-message thinking';
    messageDiv.setAttribute('data-id', messageId);

    const avatarSrc = getAvatarSrc('kp');
    const now = new Date();
    const time = `${now.getHours().toString().padStart(2, '0')}:${now.getMinutes().toString().padStart(2, '0')}`;

    messageDiv.innerHTML = `
        <div class="message-avatar">
            <img src="${avatarSrc}" alt="KP">
        </div>
        <div class="message-content-container">
            <div class="message-header">
                <span class="message-sender">KP</span>
                <span class="message-time">${time}</span>
            </div>
            <div class="message-content thinking-content">
                <div class="thinking-animation">
                    <span class="thinking-dot"></span>
                    <span class="thinking-dot"></span>
                    <span class="thinking-dot"></span>
                </div>
                <span class="thinking-text">AI正在思考中...</span>
            </div>
        </div>
    `;

    chatHistory.appendChild(messageDiv);
    chatHistory.scrollTop = chatHistory.scrollHeight;
}

function replaceThinkingMessage(messageId, newContent, processingTime, tokenCount) {
    const thinkingMessages = document.querySelectorAll('.message.thinking.kp-message');

    let targetMessage = null;
    if (thinkingMessages.length > 0) {
        targetMessage = thinkingMessages[0];
    } else {
        targetMessage = document.querySelector(`.message[data-id="${messageId}"]`);
    }

    if (targetMessage) {
        const contentDiv = targetMessage.querySelector('.message-content');
        if (contentDiv) {
            const renderedContent = renderMarkdown(newContent);
            contentDiv.innerHTML = renderedContent;
            contentDiv.className = 'message-content markdown-body';
        }

        targetMessage.classList.remove('thinking');

        if (processingTime !== null) {
            let processingTimeDiv = targetMessage.querySelector('.processing-time');
            if (!processingTimeDiv) {
                processingTimeDiv = document.createElement('div');
                processingTimeDiv.className = 'processing-time';
                const contentContainer = targetMessage.querySelector('.message-content-container');
                if (contentContainer) {
                    contentContainer.appendChild(processingTimeDiv);
                }
            }
            let displayText = `已耗时: ${processingTime}秒`;
            if (tokenCount !== null) {
                displayText += ` 消耗Token：${tokenCount}`;
            }
            processingTimeDiv.textContent = displayText;
        }

        const chatHistory = document.getElementById('chatHistory');
        chatHistory.scrollTop = chatHistory.scrollHeight;
    } else {
        addMessage('kp', 'KP', newContent, null, false, processingTime, tokenCount);
    }
}

function getCurrentChatMessages() {
    const chatHistory = document.getElementById('chatHistory');
    if (!chatHistory) return [];

    const messages = [];
    const messageElements = chatHistory.querySelectorAll('.message');

    messageElements.forEach(msgEl => {
        const sender = msgEl.querySelector('.message-sender')?.textContent || '未知';
        const content = msgEl.querySelector('.message-content')?.innerHTML || '';
        const time = msgEl.querySelector('.message-time')?.textContent || '';

        let role = 'user';
        if (msgEl.classList.contains('kp-message')) {
            role = 'assistant';
        } else if (msgEl.classList.contains('dice-message')) {
            role = 'system';
        } else if (msgEl.classList.contains('user-message') || msgEl.classList.contains('player-message')) {
            role = 'user';
        }

        messages.push({
            role: role,
            sender: sender,
            content: content,
            time: time
        });
    });

    return messages;
}

function renderChatMessages(messages) {
    const chatHistory = document.getElementById('chatHistory');
    if (!chatHistory) return;

    hideWelcomeText();

    let html = '';
    messages.forEach(msg => {
        let messageClass;
        let avatarSrc;

        if (msg.role === 'assistant' || msg.sender === 'KP') {
            messageClass = 'kp-message';
            avatarSrc = '/assets/avatars/default_kp.jpg';
        } else if (msg.role === 'system' || msg.sender === '骰娘') {
            messageClass = 'dice-message';
            avatarSrc = '/assets/avatars/default_dice.jpg';
        } else {
            messageClass = 'player-message';
            avatarSrc = document.querySelector('.user-avatar img')?.src || 'https://via.placeholder.com/40';
        }

        html += `
            <div class="message ${messageClass}">
                <div class="message-avatar">
                    <img src="${avatarSrc}" alt="${msg.sender}">
                </div>
                <div class="message-content-container">
                    <div class="message-header">
                        <span class="message-sender">${msg.sender || (msg.role === 'assistant' ? 'KP' : '用户')}</span>
                        <span class="message-time">${msg.time || new Date().toLocaleTimeString()}</span>
                    </div>
                    <div class="message-content markdown-body">${msg.content}</div>
                </div>
            </div>
        `;
    });

    chatHistory.innerHTML = html;
    chatHistory.scrollTop = chatHistory.scrollHeight;
}

function hideWelcomeText() {
    const welcomeText = document.querySelector('.welcome-text');
    if (welcomeText) {
        welcomeText.style.display = 'none';
    }
}

function initWebSocket() {
    try {
        socket = io();

        socket.on('connect', function() {
            console.log('WebSocket已连接到服务器，消息同步已启用');
        });

        socket.on('disconnect', function() {
            console.log('WebSocket已断开连接');
        });

        socket.on('new_message', function(data) {
            console.log('收到来自其他设备的消息:', data);
            handleIncomingMessage(data);
        });
    } catch (error) {
        console.warn('WebSocket连接失败，消息同步不可用:', error);
    }
}

function broadcastMessage(type, sender, content) {
    if (socket && socket.connected) {
        socket.emit('send_message', {
            type: type,
            sender: sender,
            content: content,
            time: new Date().toLocaleTimeString()
        });
    }
}

function handleIncomingMessage(data) {
    if (!data || !data.type) return;

    switch (data.type) {
        case 'player':
            addMessage('other', data.sender || '其他用户', data.content);
            break;
        case 'kp':
            addMessage('kp', 'KP', data.content);
            break;
        case 'dice':
            addMessage('dice', data.sender || '骰娘', data.content);
            break;
        case 'system':
            addMessage('system', data.sender || '系统', data.content);
            break;
        default:
            addMessage('other', data.sender || '未知', data.content);
    }
}