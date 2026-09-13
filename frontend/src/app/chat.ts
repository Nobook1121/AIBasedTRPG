interface ChatRoleConfig {
    id: string;
    name: string;
    wake_words?: string[];
    avatar?: string;
}

interface PendingAIMessage {
    sender: string;
    content: string;
    role: ChatRoleConfig;
    time: string;
}

interface CommandDefinition {
    name: string;
    usage: string;
    description: string;
}

interface ChatApiResponse {
    content?: string;
    error?: string;
    message?: string;
    token_count?: number;
    direct_message?: ChatMessage;
    direct_messages?: ChatMessage[];
    tool_messages?: ChatMessage[];
    prompt_tokens?: number;
    completion_tokens?: number;
    cached_tokens?: number;
    cache_hit_rate?: number;
    elapsed_ms?: number;
    cache_key?: string;
}

interface IncomingSocketMessage {
    room_id?: string;
    message?: ChatMessage;
    type?: "ai_thinking_start" | "ai_thinking_end" | string;
    content?: string;
    aiRequestId?: string;
    roleName?: string;
    startedAt?: number;
}

let isAIThinking = false;
let chatReadOnly = false;
let messageTimestamps: number[] = [];
let pendingMessages: PendingAIMessage[] = [];
let aiName = "KP";
let aiAvatar = "/assets/avatars/default_kp.jpg";
let aiRoles: ChatRoleConfig[] = [{ id: "kp", name: "KP", wake_words: ["@KP"] }];
let socket: SocketLike | null = null;
const thinkingTimers = new Map<string, number>();
const THINKING_STORAGE_KEY = "trpg_ai_thinking";

const COMMAND_DEFINITIONS: CommandDefinition[] = [
    { name: "/dice", usage: "/dice {dice}", description: "掷骰" },
    { name: "/check", usage: "/check {*玩家名} {*技能/属性名} {困难/极难} {调整值}", description: "属性或技能鉴定" },
    { name: "/sc", usage: "/sc {玩家名} {成功变化/失败变化}", description: "理智检定并结算 SAN" },
    { name: "/record", usage: "/record {damage/san} {username} {int} {reason?}", description: "管理员记录房间角色伤害或 San 损失" },
    { name: "/trigger", usage: "/trigger {触发器编号}", description: "触发场景触发器" },
];

function getCurrentUsername(): string {
    const username = document.getElementById("userName")?.textContent?.trim();
    if (username && username !== "未登录") {
        return username;
    }
    return window.currentUser?.username || "用户";
}

function getCurrentUserId(): string | number | null {
    return window.currentUser?.user_id || null;
}

function getCurrentRoom(): Room | null {
    return window.currentRoom || null;
}

function initChat(): void {
    const chatInput = document.getElementById("chatInput") as HTMLInputElement | null;
    const sendButton = document.getElementById("sendButton") as HTMLButtonElement | null;
    if (!chatInput || !sendButton) return;
    const activeChatInput = chatInput;
    const activeSendButton = sendButton;

    updateAIHint();
    updateInputState(activeChatInput, activeSendButton);
    void loadAIRoles();
    initWebSocket();
    initCommandPalette(activeChatInput);
    restoreThinkingState();

    async function sendMessage(): Promise<void> {
        const rawMessage = activeChatInput.value.trim();
        if (!rawMessage) return;
        if (chatReadOnly) {
            showNotification("隐身查看时不能发送消息", "error");
            return;
        }
        if (!window.currentUser) {
            showNotification("请先登录后再发送消息", "error");
            showAuthModal?.();
            return;
        }
        if (!getCurrentRoom()) {
            showNotification("请先加入房间后再发送消息", "error");
            return;
        }

        const lockInput = document.getElementById("enableAIResponseLock") as HTMLInputElement | null;
        if (isAIThinking && lockInput?.checked) {
            showNotification("请等待 AI 回复完成后再发送消息", "error");
            return;
        }

        const rateLimitInput = document.getElementById("messageRateLimit") as HTMLInputElement | null;
        const rateLimit = Number.parseInt(rateLimitInput?.value || "0", 10) || 0;
        if (rateLimit > 0 && isRateLimited(rateLimit)) {
            showNotification(`消息发送过于频繁，请稍后再试（限制 ${rateLimit} 条/分钟）`, "error");
            return;
        }

        const matchedRole = findRoleForMessage(rawMessage);
        const isAIMessage = Boolean(matchedRole);
        const message = rawMessage;
        if (!message) {
            showNotification("请输入消息内容", "error");
            return;
        }

        if (message.toLowerCase().startsWith("/record")) {
            activeChatInput.value = "";
            await sendVisibleMessage("player", message);
            const recordResult = await handleRecordCommand(message);
            await sendVisibleMessage("system", recordResult);
            return;
        }

        if (message.toLowerCase().startsWith("/trigger")) {
            activeChatInput.value = "";
            await sendVisibleMessage("player", message);
            const triggerResult = await handleTriggerCommand(message);
            if (triggerResult) {
                renderRoomMessage(triggerResult);
                broadcastMessage(triggerResult);
            }
            return;
        }

        const commandResult = window.toolManager?.handleCommand(message) || null;
        activeChatInput.value = "";

        if (commandResult) {
            await sendVisibleMessage("player", message);
            const lowerMessage = message.toLowerCase();
            const commandType = lowerMessage.startsWith("/dice") || lowerMessage.startsWith("/check") || lowerMessage.startsWith("/sc") ? "dice" : "system";
            window.setTimeout(() => {
                void sendVisibleMessage(commandType, commandResult);
            }, 300);
            return;
        }

        await sendVisibleMessage("player", message);
        if (!isAIMessage || !matchedRole) return;

        pendingMessages.push({
            sender: getCurrentUsername(),
            content: message,
            role: matchedRole,
            time: new Date().toLocaleTimeString(),
        });

        if (isAIThinking) {
            showNotification("消息已加入队列，请等待 AI 回复完成后发送", "info");
            return;
        }

        await sendToAI(activeChatInput, activeSendButton);
    }

    activeSendButton.addEventListener("click", () => {
        void sendMessage();
    });
    activeChatInput.addEventListener("keydown", (event) => {
        if (event.key === "Enter" && !event.shiftKey) {
            event.preventDefault();
            void sendMessage();
        }
    });
}

function isRateLimited(rateLimit: number): boolean {
    const now = Date.now();
    messageTimestamps = messageTimestamps.filter((timestamp) => now - timestamp < 60000);
    if (messageTimestamps.length >= rateLimit) return true;
    messageTimestamps.push(now);
    return false;
}

async function sendToAI(chatInput: HTMLInputElement, sendButton: HTMLButtonElement): Promise<void> {
    if (pendingMessages.length === 0) return;
    const requestMessages = pendingMessages.slice();

    isAIThinking = true;
    updateInputState(chatInput, sendButton);

    const aiRequestId = `ai-${Date.now()}-${Math.random().toString(36).slice(2, 8)}`;
    const thinkingMessageId = aiRequestId;
    const startTime = Date.now();
    const role = pendingMessages[0]?.role || aiRoles[0] || { id: "kp", name: "KP" };
    addThinkingMessage(thinkingMessageId, role.name || "KP", startTime);
    persistThinkingState({ id: thinkingMessageId, roomId: getCurrentRoom()?.id || null, roleName: role.name || "KP", roleId: role.id || "kp", content: pendingMessages.map((message) => message.content).join("\n"), startedAt: startTime });
    broadcastAIThinkingStart(aiRequestId, role.name || "KP", startTime);

    try {
        const { response, data } = await TrpgApi.requestWithResponse<ChatApiResponse>("/api/chat", {
            method: "POST",
            body: {
                content: requestMessages.map((message) => message.content).join("\n"),
                messages: requestMessages,
                role_id: role.id || "kp",
                user_id: getCurrentUserId(),
                room_id: getCurrentRoom()?.id || null,
            },
        });
        if (!response.ok) {
            throw new Error(data.message || `API 请求失败: ${response.status}`);
        }

        const processingTime = Math.round((Date.now() - startTime) / 1000);
        const tokenCount = data.token_count ?? null;
        const messageContent = data.content || data.error || "AI 回复失败: 未知错误";

        pendingMessages = pendingMessages.slice(requestMessages.length);
        const toolMessages = data.tool_messages || [];
        const directMessages = data.direct_messages
            || (data.direct_message ? [data.direct_message] : []);
        for (const toolMessage of toolMessages) {
            const visibleMessage = await persistDirectRoomMessage(toolMessage);
            if (visibleMessage) {
                renderRoomMessage(visibleMessage);
                broadcastMessage(visibleMessage);
            }
        }
        if (toolMessages.length > 0) {
            moveThinkingMessageToEnd(thinkingMessageId);
        }
        replaceThinkingMessage(thinkingMessageId, messageContent, processingTime, tokenCount, data.cache_hit_rate ?? null);
        broadcastAIThinkingEnd(aiRequestId);
        clearPersistedThinkingState(aiRequestId);

        const persisted = await persistRoomMessage("kp", messageContent, {
            processingTime,
            tokenCount,
            roleId: role.id,
            aiRequestId,
            senderName: role.name || "KP",
            promptTokens: data.prompt_tokens,
            completionTokens: data.completion_tokens,
            cachedTokens: data.cached_tokens,
            cacheHitRate: data.cache_hit_rate,
            cacheKey: data.cache_key,
        });
        if (persisted) {
            persisted.sender_name = role.name || "KP";
            broadcastMessage(persisted);
        }

        for (const directMessage of directMessages) {
            const persistedDirectMessage = await persistDirectRoomMessage(directMessage);
            if (persistedDirectMessage) {
                renderRoomMessage(persistedDirectMessage);
                broadcastMessage(persistedDirectMessage);
            }
        }

    } catch (error) {
        const processingTime = Math.round((Date.now() - startTime) / 1000);
        replaceThinkingMessage(thinkingMessageId, `AI 回复失败: ${chatErrorMessage(error)}`, processingTime, null);
        broadcastAIThinkingEnd(aiRequestId);
        clearPersistedThinkingState(aiRequestId);
        pendingMessages = [];
    } finally {
        isAIThinking = false;
        updateInputState(chatInput, sendButton);
        if (pendingMessages.length > 0) {
            void sendToAI(chatInput, sendButton);
        }
    }
}

function updateInputState(chatInput: HTMLInputElement, sendButton: HTMLButtonElement): void {
    const lockInput = document.getElementById("enableAIResponseLock") as HTMLInputElement | null;
    const locked = isAIThinking && Boolean(lockInput?.checked);
    chatInput.disabled = chatReadOnly || locked;
    sendButton.disabled = chatReadOnly || locked;
}

function setChatReadOnly(readOnly: boolean): void {
    chatReadOnly = readOnly;
    const chatInput = document.getElementById("chatInput") as HTMLInputElement | null;
    const sendButton = document.getElementById("sendButton") as HTMLButtonElement | null;
    if (chatInput && sendButton) updateInputState(chatInput, sendButton);
}

function isCurrentUserAdmin(): boolean {
    return ["ADMIN", "OWNER"].includes(window.currentUser?.role || "");
}

function canManageCurrentRoom(): boolean {
    if (isCurrentUserAdmin()) return true;
    const room = getCurrentRoom();
    if (!room) return false;
    if (String(room.creator_id ?? room.owner_id ?? "") === String(getCurrentUserId() ?? "")) return true;
    const member = room.members?.find((item) => String(item.user_id) === String(getCurrentUserId() ?? ""));
    return member?.room_role === "owner" || member?.room_role === "admin";
}

async function handleTriggerCommand(command: string): Promise<ChatMessage | null> {
    if (!canManageCurrentRoom()) {
        showNotification("只有房主或房间管理员可以触发场景内容", "error");
        return null;
    }

    const room = getCurrentRoom();
    if (!room?.id) {
        showNotification("请先进入房间", "error");
        return null;
    }

    const parts = command.trim().split(/\s+/);
    const triggerId = Number.parseInt(parts[1] || "", 10);
    if (!Number.isInteger(triggerId) || triggerId < 1 || parts[1] !== String(triggerId)) {
        showNotification("用法：/trigger {正整数触发器编号}", "error");
        return null;
    }

    try {
        const response = await TrpgApi.post<ApiResponse<ChatMessage>>(`/api/rooms/${encodeURIComponent(room.id)}/triggers`, {
            trigger_id: triggerId,
        });
        if (!response.success || !response.data) {
            showNotification(response.error || response.message || "触发器执行失败", "error");
            return null;
        }
        return response.data;
    } catch (error) {
        showNotification(`触发器执行失败：${chatErrorMessage(error)}`, "error");
        return null;
    }
}

async function handleRecordCommand(command: string): Promise<string> {
    if (!isCurrentUserAdmin()) {
        return "只有管理员可以使用 /record 命令";
    }
    const currentRoom = getCurrentRoom();
    if (!currentRoom?.name) {
        return "请先进入房间后再使用 /record 命令";
    }
    const parts = command.trim().split(/\s+/);
    const type = (parts[1] || "").toLowerCase();
    const username = parts[2] || "";
    const valueText = parts[3] || "";
    const validationError = validateRecordCommandParts(type, username, valueText);
    if (validationError) return validationError;
    const value = Number.parseInt(valueText, 10);
    const reason = parts.slice(4).join(" ") || "未知";

    const result = await window.recordCharacterChange?.({
        roomName: currentRoom.name,
        username,
        type,
        value,
        reason,
    });
    if (!result) return "记录失败";
    return `已记录 ${username} ${type} ${value}，原因：${reason}`;
}

function validateRecordCommandParts(type: string, username: string, valueText: string): string | null {
    if (type !== "damage" && type !== "san") {
        return "第 1 个参数必须是 {damage/san}";
    }
    if (!username) {
        return "第 2 个参数必须是 {username}";
    }
    if (!/^[1-9]\d*$/.test(valueText)) {
        return "第 3 个参数必须是正整数 {int}";
    }
    return null;
}

function getRecordCommandDraftHint(value: string): string {
    const parts = value.trim().split(/\s+/);
    const type = (parts[1] || "").toLowerCase();
    const username = parts[2] || "";
    const valueText = parts[3] || "";
    if (!parts[1]) return "下一项：{damage/san}";
    if (type !== "damage" && type !== "san") return "第 1 个参数必须是 {damage/san}";
    if (!parts[2]) return "下一项：{username}";
    if (!username) return "第 2 个参数必须是 {username}";
    if (!parts[3]) return "下一项：{int}";
    if (!/^[1-9]\d*$/.test(valueText)) return "第 3 个参数必须是正整数 {int}";
    return "可选：{reason?}";
}

function initCommandPalette(chatInput: HTMLInputElement): void {
    if (document.getElementById("commandPalette")) return;
    const palette = document.createElement("div");
    palette.id = "commandPalette";
    palette.className = "command-palette list-group shadow-sm";
    palette.style.display = "none";
    chatInput.parentElement?.appendChild(palette);

    chatInput.addEventListener("input", () => showCommandPalette(chatInput, palette));
    chatInput.addEventListener("blur", () => window.setTimeout(() => {
        palette.style.display = "none";
    }, 120));
}

function showCommandPalette(chatInput: HTMLInputElement, palette: HTMLElement): void {
    const value = chatInput.value.trimStart();
    if (!value.startsWith("/")) {
        palette.style.display = "none";
        return;
    }
    const commandName = value.split(/\s+/)[0]?.toLowerCase() || "";
    const matches = COMMAND_DEFINITIONS.filter((command) => command.name.startsWith(commandName));
    if (matches.length === 0) {
        palette.style.display = "none";
        return;
    }
    palette.innerHTML = matches.map((command) => {
        const hint = command.name === "/record" ? getRecordCommandDraftHint(value) : "";
        const hintHtml = hint ? window.TrpgTemplates.render("chat-command-palette-hint", { hint }) : "";
        return window.TrpgTemplates.render("chat-command-palette-item", {
            commandName: command.name,
            usage: command.usage,
            description: command.description,
            hintHtml,
        });
    }).join("");
    palette.querySelectorAll<HTMLButtonElement>("[data-command]").forEach((button) => {
        button.addEventListener("mousedown", (event) => {
            event.preventDefault();
            chatInput.value = `${button.dataset.command || ""} `;
            palette.style.display = "none";
            chatInput.focus();
        });
    });
    palette.style.display = "block";
}

async function sendVisibleMessage(
    type: string,
    content: string,
    metadata: Record<string, unknown> = {},
): Promise<ChatMessage | null> {
    const room = getCurrentRoom();
    if (room) {
        if (room.invisible_view) return null;
        const message = await persistRoomMessage(type, content, metadata);
        if (message) {
            renderRoomMessage(message);
            broadcastMessage(message);
        }
        return message;
    }

    const sender = type === "player" ? getCurrentUsername() : defaultSenderName(type);
    addMessage(type, sender, content);
    broadcastMessage({
        type,
        sender_name: sender,
        content,
        avatar: getAvatarSrc(type),
    });
    return null;
}

async function persistDirectRoomMessage(message: ChatMessage): Promise<ChatMessage | null> {
    if (!message.content) return null;
    const room = getCurrentRoom();
    if (!room) return message;
    if (room.invisible_view) return null;
    const response = await TrpgApi.post<ApiResponse<ChatMessage>>(`/api/rooms/${room.id}/messages`, {
        type: message.type || "trigger",
        content: message.content,
        sender_name: message.sender_name || message.sender || "触发器",
        avatar: message.avatar,
        metadata: message.metadata || {},
    });
    if (!response.success) throw new Error(response.message || "保存直接消息失败");
    return response.data || null;
}

async function persistRoomMessage(type: string, content: string, metadata: Record<string, unknown> = {}): Promise<ChatMessage | null> {
    const room = getCurrentRoom();
    if (!room || room.invisible_view) return null;

    const payload: ChatMessage = {
        type,
        content,
        metadata,
    };
    const senderName = typeof metadata.senderName === "string" ? metadata.senderName : null;
    if (senderName) payload.sender_name = senderName;

    const data = await TrpgApi.post<ApiResponse<ChatMessage>>(`/api/rooms/${room.id}/messages`, payload);
    if (!data.success) throw new Error(data.message || "保存房间消息失败");
    return data.data || null;
}

function updateAIHint(): void {
    const aiHint = document.getElementById("aiHint");
    if (aiHint) aiHint.textContent = `@${aiName}`;
}

async function loadAIRoles(): Promise<void> {
    try {
        const response = await TrpgApi.get<ApiResponse<{ roles: ChatRoleConfig[] }>>("/api/config/roles");
        if (response.success && response.data?.roles?.length) {
            aiRoles = response.data.roles;
            aiName = aiRoles[0]?.name || "KP";
            aiAvatar = aiRoles[0]?.avatar || "/assets/avatars/default_kp.jpg";
            updateAIHint();
        }
    } catch (error) {
        console.warn("加载 AI 角色配置失败，使用默认 KP 角色:", error);
    }
}

function findRoleForMessage(message: string): ChatRoleConfig | undefined {
    const trimmedMessage = message.trim();
    return aiRoles.find((role) => (role.wake_words || []).some((wakeWord) => trimmedMessage.startsWith(wakeWord)));
}

function setAIName(name: string): void {
    aiName = name;
    updateAIHint();
}

function renderMarkdown(content: string): string {
    try {
        const parser = window.marked;
        if (parser) {
            parser.setOptions({ breaks: true, gfm: true, headerIds: false, mangle: false });
            return parser.parse(content);
        }
        return chatEscapeHtml(content);
    } catch (error) {
        console.error("Markdown 渲染失败:", error);
        return chatEscapeHtml(content);
    }
}

function getAvatarSrc(type: string, message: ChatMessage | null = null): string {
    if (message?.avatar) return message.avatar;
    switch (type) {
        case "player":
            return document.querySelector<HTMLImageElement>(".user-avatar img")?.src || "/assets/avatars/default.jpg";
        case "kp":
            return "/assets/avatars/default_kp.jpg";
        case "dice":
            return "/assets/avatars/default_dice.jpg";
        case "system":
            return "/assets/avatars/default_system.jpg";
        default:
            return "/assets/avatars/default.jpg";
    }
}

function defaultSenderName(type: string): string {
    switch (type) {
        case "kp": return "KP";
        case "dice": return "骰娘";
        case "system": return "系统";
        default: return getCurrentUsername();
    }
}

function getMessageClass(type: string): string {
    switch (type) {
        case "player": return "player-message";
        case "kp": return "kp-message";
        case "dice": return "dice-message";
        case "system": return "other-message";
        case "other": return "other-message";
        default: return "other-message";
    }
}

function addMessage(
    type: string,
    sender: string,
    content: string,
    messageId: string | number | null = null,
    isThinking = false,
    processingTime: number | null = null,
    tokenCount: number | null = null,
    cacheHitRate: number | null = null,
    message: ChatMessage | null = null,
): string | number {
    const resolvedMessageId = messageId || Date.now();
    const chatHistory = document.getElementById("chatHistory");
    if (!chatHistory) return resolvedMessageId;

    hideWelcomeText();
    let messageClass = getMessageClass(type);
    if (isThinking) messageClass += " thinking";

    const messageDiv = document.createElement("div");
    messageDiv.className = `message ${messageClass}`;
    messageDiv.setAttribute("data-id", String(resolvedMessageId));
    if (message?.sender_id !== undefined && message.sender_id !== null) {
        messageDiv.setAttribute("data-sender-id", String(message.sender_id));
    }
    if (message?.avatar) messageDiv.setAttribute("data-avatar", message.avatar);

    const displayTime = message?.time || message?.timestamp || new Date().toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" });
    const renderedContent = isThinking ? chatEscapeHtml(content) : renderMarkdown(content);
    const avatarSrc = getAvatarSrc(type, message);

    messageDiv.innerHTML = window.TrpgTemplates.render("chat-message", {
        avatarSrc,
        sender,
        displayTime,
        contentHtml: renderedContent,
        processingHtml: renderProcessingTime(type, processingTime, tokenCount, cacheHitRate),
    });
    chatHistory.appendChild(messageDiv);
    chatHistory.scrollTop = chatHistory.scrollHeight;
    return resolvedMessageId;
}

function renderProcessingTime(type: string, processingTime: number | null, tokenCount: number | null, cacheHitRate: number | null = null): string {
    if (processingTime === null || type !== "kp") return "";
    return window.TrpgTemplates.render("chat-processing-time", { text: processingTimeText(processingTime, tokenCount, cacheHitRate) });
}

function addThinkingMessage(messageId: string | number, roleName = "KP", startedAt = Date.now()): void {
    addMessage("kp", roleName, "AI 正在思考中...", messageId, true, 0);
    const messageElement = document.querySelector<HTMLElement>(`.message[data-id="${String(messageId)}"]`);
    if (messageElement) {
        messageElement.setAttribute("data-ai-request-id", String(messageId));
        messageElement.setAttribute("data-started-at", String(startedAt));
    }
    startThinkingElapsedTimer(String(messageId), startedAt);
}

function replaceThinkingMessage(messageId: string | number, newContent: string, processingTime: number, tokenCount: number | null, cacheHitRate: number | null = null): void {
    stopThinkingElapsedTimer(String(messageId));
    const targetMessage = document.querySelector<HTMLElement>(`.message.thinking.kp-message[data-ai-request-id="${String(messageId)}"]`)
        || document.querySelector<HTMLElement>(`.message[data-id="${messageId}"]`);

    if (!targetMessage) {
        addMessage("kp", "KP", newContent, null, false, processingTime, tokenCount, cacheHitRate);
        return;
    }

    const contentDiv = targetMessage.querySelector<HTMLElement>(".message-content");
    if (contentDiv) {
        contentDiv.innerHTML = renderMarkdown(newContent);
        contentDiv.className = "message-content markdown-body";
    }
    targetMessage.classList.remove("thinking");

    let processingTimeDiv = targetMessage.querySelector<HTMLElement>(".processing-time");
    if (!processingTimeDiv) {
        processingTimeDiv = document.createElement("div");
        processingTimeDiv.className = "processing-time";
        targetMessage.querySelector(".message-content-container")?.appendChild(processingTimeDiv);
    }

    processingTimeDiv.textContent = processingTimeText(processingTime, tokenCount, cacheHitRate);

    const chatHistory = document.getElementById("chatHistory");
    if (chatHistory) chatHistory.scrollTop = chatHistory.scrollHeight;
}

function processingTimeText(processingTime: number, tokenCount: number | null = null, cacheHitRate: number | null = null): string {
    let displayText = `已耗时: ${processingTime}秒`;
    if (tokenCount !== null) displayText += ` 消耗Token：${tokenCount}`;
    if (cacheHitRate !== null) displayText += ` 缓存命中率：${cacheHitRate}%`;
    return displayText;
}

function startThinkingElapsedTimer(aiRequestId: string, startedAt: number): void {
    stopThinkingElapsedTimer(aiRequestId);
    updateThinkingElapsed(aiRequestId, startedAt);
    const timerId = window.setInterval(() => updateThinkingElapsed(aiRequestId, startedAt), 1000);
    thinkingTimers.set(aiRequestId, timerId);
}

function stopThinkingElapsedTimer(aiRequestId: string): void {
    const timerId = thinkingTimers.get(aiRequestId);
    if (timerId !== undefined) window.clearInterval(timerId);
    thinkingTimers.delete(aiRequestId);
}

function updateThinkingElapsed(aiRequestId: string, startedAt: number): void {
    const messageElement = document.querySelector<HTMLElement>(`.message.thinking.kp-message[data-ai-request-id="${aiRequestId}"]`);
    if (!messageElement) {
        stopThinkingElapsedTimer(aiRequestId);
        return;
    }
    const elapsedSeconds = Math.max(0, Math.floor((Date.now() - startedAt) / 1000));
    let processingTimeDiv = messageElement.querySelector<HTMLElement>(".processing-time");
    if (!processingTimeDiv) {
        const wrapper = document.createElement("div");
        wrapper.innerHTML = renderProcessingTime("kp", elapsedSeconds, null);
        processingTimeDiv = wrapper.firstElementChild as HTMLElement | null;
        if (processingTimeDiv) messageElement.querySelector(".message-content-container")?.appendChild(processingTimeDiv);
    } else {
        processingTimeDiv.textContent = processingTimeText(elapsedSeconds);
    }
}

function clearThinkingMessage(aiRequestId: string): void {
    stopThinkingElapsedTimer(aiRequestId);
    document.querySelector<HTMLElement>(`.message.thinking.kp-message[data-ai-request-id="${aiRequestId}"]`)?.remove();
    clearPersistedThinkingState(aiRequestId);
}

function persistThinkingState(state: { id: string; roomId: string | null; roleName: string; roleId?: string; content?: string; startedAt: number }): void {
    try { localStorage.setItem(THINKING_STORAGE_KEY, JSON.stringify(state)); } catch { /* storage may be unavailable */ }
}

function clearPersistedThinkingState(id?: string): void {
    try {
        const raw = localStorage.getItem(THINKING_STORAGE_KEY);
        if (!id || !raw || JSON.parse(raw)?.id === id) localStorage.removeItem(THINKING_STORAGE_KEY);
    } catch { localStorage.removeItem(THINKING_STORAGE_KEY); }
}

function restoreThinkingState(): void {
    try {
        const state = JSON.parse(localStorage.getItem(THINKING_STORAGE_KEY) || "null");
        const roomId = getCurrentRoom()?.id || null;
        if (!state?.id || state.roomId !== roomId) return;
        if (state.content && pendingMessages.length === 0) {
            const role = aiRoles.find((item) => item.id === state.roleId) || aiRoles[0] || { id: state.roleId || "kp", name: state.roleName || "KP" };
            pendingMessages.push({ sender: getCurrentUsername(), content: String(state.content), role, time: new Date().toLocaleTimeString() });
        }
        addThinkingMessage(state.id, state.roleName || "KP", Number(state.startedAt) || Date.now());
    } catch { /* ignore malformed persisted state */ }
}

function resumePendingAIRequest(): void {
    if (isAIThinking || pendingMessages.length === 0) return;
    try {
        const state = JSON.parse(localStorage.getItem(THINKING_STORAGE_KEY) || "null");
        if (state?.id) clearThinkingMessage(String(state.id));
    } catch { /* ignore */ }
    const chatInput = document.getElementById("chatInput") as HTMLInputElement | null;
    const sendButton = document.getElementById("sendButton") as HTMLButtonElement | null;
    if (chatInput && sendButton && getCurrentRoom()) void sendToAI(chatInput, sendButton);
}

function moveThinkingMessageToEnd(messageId: string | number): void {
    const chatHistory = document.getElementById("chatHistory");
    const targetMessage = document.querySelector<HTMLElement>(`.message.thinking.kp-message[data-ai-request-id="${String(messageId)}"]`);
    if (!chatHistory || !targetMessage || targetMessage.parentElement !== chatHistory) return;
    chatHistory.appendChild(targetMessage);
    chatHistory.scrollTop = chatHistory.scrollHeight;
}

function getCurrentChatMessages(): ChatMessage[] {
    const chatHistory = document.getElementById("chatHistory");
    if (!chatHistory) return [];

    return Array.from(chatHistory.querySelectorAll<HTMLElement>(".message")).map((messageElement) => {
        const sender = messageElement.querySelector(".message-sender")?.textContent || "未知";
        const content = messageElement.querySelector(".message-content")?.innerHTML || "";
        const time = messageElement.querySelector(".message-time")?.textContent || "";
        const avatar = messageElement.getAttribute("data-avatar");
        let role = "user";
        if (messageElement.classList.contains("kp-message")) role = "assistant";
        if (messageElement.classList.contains("dice-message")) role = "system";
        const message: ChatMessage = {
            role,
            sender,
            sender_id: messageElement.getAttribute("data-sender-id"),
            content,
            time,
        };
        if (avatar) message.avatar = avatar;
        return message;
    });
}

function renderChatMessages(messages: ChatMessage[]): void {
    const chatHistory = document.getElementById("chatHistory");
    if (!chatHistory) return;

    chatHistory.innerHTML = "";
    hideWelcomeText();
    messages.forEach((message) => renderRoomMessage(message));
    chatHistory.scrollTop = chatHistory.scrollHeight;
}

function renderRoomMessage(message: ChatMessage | null): void {
    if (!message) return;
    if (message.id) {
        const duplicate = Array.from(document.querySelectorAll<HTMLElement>("#chatHistory .message[data-id]"))
            .some((element) => element.dataset.id === String(message.id));
        if (duplicate) return;
    }
    const aiRequestId = typeof message.metadata?.aiRequestId === "string" ? message.metadata.aiRequestId : null;
    if (aiRequestId) clearThinkingMessage(aiRequestId);
    const isOwnPlayerMessage = message.type === "player" && message.sender_id === getCurrentUserId();
    const type = message.type === "player" && !isOwnPlayerMessage ? "other" : message.type || "other";
    const metadata = message.metadata || {};
    if (metadata.check_type === "sanity" && metadata.player_name && window.currentRoom?.members) {
        const member = window.currentRoom.members.find((item) => String(item.username || "").toLocaleLowerCase() === String(metadata.player_name).toLocaleLowerCase());
        if (member) {
            member.character_state = { ...(member.character_state || {}), current_san: Number(metadata.current_san), max_san: Number(metadata.max_san) };
            if (member.character_card) {
                member.character_card.currentSan = Number(metadata.current_san);
                (member.character_card as Partial<COC7CharacterCard> & { current_san?: number }).current_san = Number(metadata.current_san);
            }
        }
    }
    const displayMessage = message.type === "trigger" && metadata.asset_url && message.content && !message.content.includes(String(metadata.asset_url))
        ? { ...message, content: `${message.content}\n\n[${metadata.asset_name || "附件"}](${metadata.asset_url})` }
        : message;
    addMessage(
        type,
        displayMessage.sender_name || displayMessage.sender || defaultSenderName(type),
        displayMessage.content,
        displayMessage.id || null,
        false,
        numericMetadata(metadata, "processingTime") ?? numericMetadata(metadata, "processing_time"),
        numericMetadata(metadata, "tokenCount") ?? numericMetadata(metadata, "token_count"),
        numericMetadata(metadata, "cacheHitRate") ?? numericMetadata(metadata, "cache_hit_rate"),
        displayMessage,
    );
}

function clearChatMessages(): void {
    const chatHistory = document.getElementById("chatHistory");
    if (!chatHistory) return;
    chatHistory.innerHTML = window.TrpgTemplates.render("chat-welcome");
}

function hideWelcomeText(): void {
    const welcomeText = document.querySelector<HTMLElement>(".welcome-text");
    if (welcomeText) welcomeText.style.display = "none";
}

function initWebSocket(): void {
    if (!window.currentUser) return;
    if (socket?.connected) return;
    try {
        socket = io();
        socket.on("connect", () => {
            const room = getCurrentRoom();
            if (room && !room.invisible_view) socket?.emit("join_room", { room_id: room.id });
        });
        socket.on("session_expired", () => {
            showNotification("当前账号已在其他会话登录，请重新登录。", "error");
            disconnectSocket();
            window.clearCurrentRoom?.();
            window.clearChatMessages?.();
            window.currentUser = null;
            showAuthModal();
        });
        socket.on("new_message", (data) => handleIncomingMessage(data));
    } catch (error) {
        console.warn("WebSocket 连接失败，消息同步不可用:", error);
    }
}

function reconnectSocket(): void {
    disconnectSocket();
    initWebSocket();
}

function disconnectSocket(): void {
    if (socket) {
        socket.disconnect();
        socket = null;
    }
}

function joinSocketRoom(roomId: string): void {
    if (socket?.connected && roomId && !getCurrentRoom()?.invisible_view) socket.emit("join_room", { room_id: roomId });
}

function leaveSocketRoom(roomId: string): void {
    if (socket?.connected && roomId) socket.emit("leave_room", { room_id: roomId });
}

function broadcastMessage(message: ChatMessage | null): void {
    if (!socket?.connected || !message) return;
    socket.emit("send_message", {
        room_id: getCurrentRoom()?.id || null,
        message,
    });
}

function broadcastAIThinkingStart(aiRequestId: string, roleName: string, startedAt: number): void {
    if (!socket?.connected) return;
    socket.emit("send_message", {
        room_id: getCurrentRoom()?.id || null,
        type: "ai_thinking_start",
        aiRequestId,
        roleName,
        startedAt,
    });
}

function broadcastAIThinkingEnd(aiRequestId: string): void {
    if (!socket?.connected) return;
    socket.emit("send_message", {
        room_id: getCurrentRoom()?.id || null,
        type: "ai_thinking_end",
        aiRequestId,
    });
}

function handleIncomingMessage(data: unknown): void {
    const incoming = normalizeIncomingMessage(data);
    if (!incoming) return;
    const room = getCurrentRoom();
    if (incoming.room_id && room?.id !== incoming.room_id) return;
    if (incoming.type === "ai_thinking_start" || incoming.type === "ai_thinking_end") {
        handleAIThinkingEvent(incoming);
        return;
    }
    if (incoming.message) {
        const aiRequestId = typeof incoming.message.metadata?.aiRequestId === "string" ? incoming.message.metadata.aiRequestId : null;
        if (aiRequestId) clearThinkingMessage(aiRequestId);
        renderRoomMessage(incoming.message);
        return;
    }
    if (incoming.type && incoming.content) renderRoomMessage(incoming as ChatMessage);
}

function handleAIThinkingEvent(incoming: IncomingSocketMessage): void {
    const aiRequestId = incoming.aiRequestId;
    if (!aiRequestId) return;
    if (incoming.type === "ai_thinking_end") {
        clearThinkingMessage(aiRequestId);
        return;
    }
    const selector = `.message.thinking.kp-message[data-ai-request-id="${aiRequestId}"]`;
    if (document.querySelector(selector)) return;
    // Use the receiving browser's clock. Sender clocks can differ and produce
    // negative or wildly inflated elapsed times for other players.
    addThinkingMessage(aiRequestId, incoming.roleName || "KP", Date.now());
}

function normalizeIncomingMessage(data: unknown): IncomingSocketMessage | null {
    if (typeof data !== "object" || data === null) return null;
    return data as IncomingSocketMessage;
}

function numericMetadata(metadata: Record<string, unknown>, key: string): number | null {
    const value = metadata[key];
    return typeof value === "number" ? value : null;
}

function chatEscapeHtml(value: unknown): string {
    return String(value ?? "")
        .replace(/&/g, "&amp;")
        .replace(/</g, "&lt;")
        .replace(/>/g, "&gt;")
        .replace(/"/g, "&quot;")
        .replace(/'/g, "&#039;");
}

function chatErrorMessage(error: unknown): string {
    return error instanceof Error ? error.message : String(error);
}

window.renderChatMessages = renderChatMessages;
window.getCurrentChatMessages = getCurrentChatMessages;
window.clearChatMessages = clearChatMessages;
window.setChatReadOnly = setChatReadOnly;
window.joinSocketRoom = joinSocketRoom;
window.leaveSocketRoom = leaveSocketRoom;
window.reconnectSocket = reconnectSocket;
window.disconnectSocket = disconnectSocket;
window.loadAIRoles = loadAIRoles;
window.restoreThinkingState = restoreThinkingState;
window.resumePendingAIRequest = resumePendingAIRequest;
