// @ts-nocheck
// Chat module. Room-aware messages are persisted by the backend.
let isAIThinking = false;
let messageTimestamps = [];
let pendingMessages = [];
let aiName = 'KP';
let socket = null;
function getCurrentUsername() {
    const username = document.getElementById('userName')?.textContent?.trim();
    if (username && username !== '未登录') {
        return username;
    }
    return window.currentUser?.username || '用户';
}
function getCurrentUserId() {
    return window.currentUser?.user_id || null;
}
function getCurrentRoom() {
    return window.currentRoom || null;
}
function initChat() {
    const chatInput = document.getElementById('chatInput');
    const sendButton = document.getElementById('sendButton');
    updateAIHint();
    initWebSocket();
    async function sendMessage() {
        const rawMessage = chatInput.value.trim();
        if (!rawMessage)
            return;
        if (isAIThinking && document.getElementById('enableAIResponseLock')?.checked) {
            showNotification('请等待 AI 回复完成后再发送消息', 'error');
            return;
        }
        const rateLimit = parseInt(document.getElementById('messageRateLimit')?.value) || 0;
        if (rateLimit > 0) {
            const now = Date.now();
            messageTimestamps = messageTimestamps.filter(ts => now - ts < 60000);
            if (messageTimestamps.length >= rateLimit) {
                showNotification(`消息发送过于频繁，请稍后再试（限制 ${rateLimit} 条/分钟）`, 'error');
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
        chatInput.value = '';
        if (commandResult) {
            await sendVisibleMessage('player', message);
            const commandType = message.toLowerCase().startsWith('/dice') ? 'dice' : 'system';
            setTimeout(() => {
                sendVisibleMessage(commandType, commandResult);
            }, 300);
            return;
        }
        await sendVisibleMessage('player', message);
        if (!isAIMessage) {
            return;
        }
        pendingMessages.push({
            sender: getCurrentUsername(),
            content: message,
            time: new Date().toLocaleTimeString(),
        });
        if (isAIThinking) {
            showNotification('消息已加入队列，请等待 AI 回复完成后发送', 'info');
            return;
        }
        sendToAI();
    }
    async function sendToAI() {
        if (pendingMessages.length === 0)
            return;
        isAIThinking = true;
        updateInputState();
        const thinkingMessageId = Date.now();
        const startTime = Date.now();
        addThinkingMessage(thinkingMessageId);
        try {
            const { response, data } = await TrpgApi.requestWithResponse('/api/chat', {
                method: 'POST',
                body: {
                    content: pendingMessages.map(m => m.content).join('\n'),
                    messages: pendingMessages,
                    user_id: getCurrentUserId(),
                    room_id: getCurrentRoom()?.id || null,
                },
            });
            if (!response.ok) {
                throw new Error(data?.message || `API 请求失败: ${response.status}`);
            }
            const processingTime = Math.round((Date.now() - startTime) / 1000);
            const tokenCount = data.token_count || null;
            const messageContent = data.content || data.error || 'AI 回复失败: 未知错误';
            pendingMessages = [];
            replaceThinkingMessage(thinkingMessageId, messageContent, processingTime, tokenCount);
            const room = getCurrentRoom();
            if (room) {
                const persisted = await persistRoomMessage('kp', messageContent, {
                    processingTime,
                    tokenCount,
                });
                broadcastMessage(persisted);
            }
            else {
                broadcastMessage({
                    type: 'kp',
                    sender_name: 'KP',
                    content: messageContent,
                    metadata: { processingTime, tokenCount },
                });
            }
        }
        catch (error) {
            const processingTime = Math.round((Date.now() - startTime) / 1000);
            replaceThinkingMessage(thinkingMessageId, 'AI 回复失败: ' + error.message, processingTime, null);
            pendingMessages = [];
        }
        finally {
            isAIThinking = false;
            updateInputState();
        }
    }
    function updateInputState() {
        chatInput.disabled = isAIThinking;
        sendButton.disabled = isAIThinking;
    }
    sendButton.addEventListener('click', sendMessage);
    chatInput.addEventListener('keypress', function (e) {
        if (e.key === 'Enter') {
            sendMessage();
        }
    });
}
async function sendVisibleMessage(type, content) {
    const room = getCurrentRoom();
    if (room) {
        const message = await persistRoomMessage(type, content);
        renderRoomMessage(message);
        broadcastMessage(message);
        return message;
    }
    const sender = type === 'player' ? getCurrentUsername() : defaultSenderName(type);
    addMessage(type, sender, content);
    broadcastMessage({
        type,
        sender_name: sender,
        content,
        avatar: getAvatarSrc(type),
    });
    return null;
}
async function persistRoomMessage(type, content, metadata = {}) {
    const room = getCurrentRoom();
    if (!room)
        return null;
    const data = await TrpgApi.post(`/api/rooms/${room.id}/messages`, {
        type,
        content,
        metadata,
    });
    if (!data.success) {
        throw new Error(data.message || '保存房间消息失败');
    }
    return data.data;
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
            marked.setOptions({ breaks: true, gfm: true, headerIds: false, mangle: false });
            return marked(content);
        }
        if (marked && typeof marked.parse === 'function') {
            return marked.parse(content, { breaks: true, gfm: true, headerIds: false, mangle: false });
        }
        return content;
    }
    catch (error) {
        console.error('Markdown 渲染失败:', error);
        return content;
    }
}
function getAvatarSrc(type, message = null) {
    if (message?.avatar) {
        return message.avatar;
    }
    switch (type) {
        case 'player':
            return document.querySelector('.user-avatar img')?.src || '/assets/avatars/default.jpg';
        case 'kp':
            return '/assets/avatars/default_kp.jpg';
        case 'dice':
            return '/assets/avatars/default_dice.jpg';
        case 'system':
            return '/assets/avatars/default_system.jpg';
        default:
            return '/assets/avatars/default.jpg';
    }
}
function defaultSenderName(type) {
    switch (type) {
        case 'kp': return 'KP';
        case 'dice': return '骰娘';
        case 'system': return '系统';
        default: return getCurrentUsername();
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
function addMessage(type, sender, content, messageId = null, isThinking = false, processingTime = null, tokenCount = null, message = null) {
    messageId = messageId || Date.now();
    const chatHistory = document.getElementById('chatHistory');
    if (!chatHistory)
        return messageId;
    hideWelcomeText();
    let messageClass = getMessageClass(type);
    if (isThinking) {
        messageClass += ' thinking';
    }
    const messageDiv = document.createElement('div');
    messageDiv.className = `message ${messageClass}`;
    messageDiv.setAttribute('data-id', messageId);
    if (message?.sender_id) {
        messageDiv.setAttribute('data-sender-id', String(message.sender_id));
    }
    if (message?.avatar) {
        messageDiv.setAttribute('data-avatar', message.avatar);
    }
    const displayTime = message?.time || new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
    const renderedContent = isThinking ? content : renderMarkdown(content);
    const avatarSrc = getAvatarSrc(type, message);
    let messageHTML = `
        <div class="message-avatar">
            <img src="${avatarSrc}" alt="${sender}">
        </div>
        <div class="message-content-container">
            <div class="message-header">
                <span class="message-sender">${sender}</span>
                <span class="message-time">${displayTime}</span>
            </div>
            <div class="message-content markdown-body">${renderedContent}</div>
    `;
    if (processingTime !== null && type === 'kp') {
        let displayText = `已耗时: ${processingTime}秒`;
        if (tokenCount !== null) {
            displayText += ` 消耗Token：${tokenCount}`;
        }
        messageHTML += `<div class="processing-time">${displayText}</div>`;
    }
    messageHTML += '</div>';
    messageDiv.innerHTML = messageHTML;
    chatHistory.appendChild(messageDiv);
    chatHistory.scrollTop = chatHistory.scrollHeight;
    return messageId;
}
function addThinkingMessage(messageId) {
    addMessage('kp', 'KP', 'AI 正在思考中...', messageId, true);
}
function replaceThinkingMessage(messageId, newContent, processingTime, tokenCount) {
    const targetMessage = document.querySelector('.message.thinking.kp-message')
        || document.querySelector(`.message[data-id="${messageId}"]`);
    if (!targetMessage) {
        addMessage('kp', 'KP', newContent, null, false, processingTime, tokenCount);
        return;
    }
    const contentDiv = targetMessage.querySelector('.message-content');
    if (contentDiv) {
        contentDiv.innerHTML = renderMarkdown(newContent);
        contentDiv.className = 'message-content markdown-body';
    }
    targetMessage.classList.remove('thinking');
    let processingTimeDiv = targetMessage.querySelector('.processing-time');
    if (!processingTimeDiv) {
        processingTimeDiv = document.createElement('div');
        processingTimeDiv.className = 'processing-time';
        targetMessage.querySelector('.message-content-container')?.appendChild(processingTimeDiv);
    }
    let displayText = `已耗时: ${processingTime}秒`;
    if (tokenCount !== null) {
        displayText += ` 消耗Token：${tokenCount}`;
    }
    processingTimeDiv.textContent = displayText;
    const chatHistory = document.getElementById('chatHistory');
    if (chatHistory) {
        chatHistory.scrollTop = chatHistory.scrollHeight;
    }
}
function getCurrentChatMessages() {
    const chatHistory = document.getElementById('chatHistory');
    if (!chatHistory)
        return [];
    return Array.from(chatHistory.querySelectorAll('.message')).map(msgEl => {
        const sender = msgEl.querySelector('.message-sender')?.textContent || '未知';
        const content = msgEl.querySelector('.message-content')?.innerHTML || '';
        const time = msgEl.querySelector('.message-time')?.textContent || '';
        let role = 'user';
        if (msgEl.classList.contains('kp-message'))
            role = 'assistant';
        if (msgEl.classList.contains('dice-message'))
            role = 'system';
        return {
            role,
            sender,
            sender_id: msgEl.getAttribute('data-sender-id'),
            avatar: msgEl.getAttribute('data-avatar'),
            content,
            time,
        };
    });
}
function renderChatMessages(messages) {
    const chatHistory = document.getElementById('chatHistory');
    if (!chatHistory)
        return;
    chatHistory.innerHTML = '';
    hideWelcomeText();
    messages.forEach(message => renderRoomMessage(message));
    chatHistory.scrollTop = chatHistory.scrollHeight;
}
function renderRoomMessage(message) {
    if (!message)
        return;
    const isOwnPlayerMessage = message.type === 'player' && message.sender_id === getCurrentUserId();
    const type = message.type === 'player' && !isOwnPlayerMessage ? 'other' : message.type;
    const metadata = message.metadata || {};
    addMessage(type, message.sender_name || message.sender || defaultSenderName(type), message.content, message.id, false, metadata.processingTime ?? metadata.processing_time ?? null, metadata.tokenCount ?? metadata.token_count ?? null, message);
}
function clearChatMessages() {
    const chatHistory = document.getElementById('chatHistory');
    if (!chatHistory)
        return;
    chatHistory.innerHTML = '<div class="welcome-text">请选择或创建一个房间开始游戏。</div>';
}
function hideWelcomeText() {
    const welcomeText = document.querySelector('.welcome-text');
    if (welcomeText) {
        welcomeText.style.display = 'none';
    }
}
function initWebSocket() {
    if (!window.currentUser) {
        return;
    }
    if (socket && socket.connected) {
        return;
    }
    try {
        socket = io();
        socket.on('connect', function () {
            const room = getCurrentRoom();
            if (room) {
                socket.emit('join_room', { room_id: room.id });
            }
        });
        socket.on('session_expired', function () {
            showNotification('当前账号已在其他会话登录，请重新登录。', 'error');
            disconnectSocket();
            window.clearCurrentRoom?.();
            window.clearChatMessages?.();
            window.currentUser = null;
            showAuthModal();
        });
        socket.on('new_message', function (data) {
            handleIncomingMessage(data);
        });
    }
    catch (error) {
        console.warn('WebSocket 连接失败，消息同步不可用:', error);
    }
}
function reconnectSocket() {
    disconnectSocket();
    initWebSocket();
}
function disconnectSocket() {
    if (socket) {
        socket.disconnect();
        socket = null;
    }
}
function joinSocketRoom(roomId) {
    if (socket && socket.connected && roomId) {
        socket.emit('join_room', { room_id: roomId });
    }
}
function leaveSocketRoom(roomId) {
    if (socket && socket.connected && roomId) {
        socket.emit('leave_room', { room_id: roomId });
    }
}
function broadcastMessage(message) {
    if (!socket || !socket.connected || !message)
        return;
    socket.emit('send_message', {
        room_id: getCurrentRoom()?.id || null,
        message,
    });
}
function handleIncomingMessage(data) {
    const room = getCurrentRoom();
    if (data?.room_id && room?.id !== data.room_id) {
        return;
    }
    if (data?.message) {
        renderRoomMessage(data.message);
        return;
    }
    if (data?.type) {
        renderRoomMessage(data);
    }
}
window.renderChatMessages = renderChatMessages;
window.getCurrentChatMessages = getCurrentChatMessages;
window.clearChatMessages = clearChatMessages;
window.joinSocketRoom = joinSocketRoom;
window.leaveSocketRoom = leaveSocketRoom;
window.reconnectSocket = reconnectSocket;
window.disconnectSocket = disconnectSocket;
