interface RoomNode {
    filename: string;
    created_at?: string;
    message_count?: number;
}

interface RoomNodeList {
    nodes: RoomNode[];
}

interface RoomRecordResponse {
    room?: Room;
    record?: CharacterRuntimeRecord;
}

let currentRoom: Room | null = null;
let autosaveTimer: number | null = null;
let previewNodeFilename: string | null = null;

function initRoomManagement(): void {
    window.currentRoom = currentRoom;

    document.getElementById("createSave")?.addEventListener("click", () => {
        void openCreateRoomModal();
    });
    document.getElementById("confirmCreateSave")?.addEventListener("click", () => {
        void createRoom();
    });
    document.getElementById("joinRoom")?.addEventListener("click", () => {
        void joinRoomByCode();
    });
    document.getElementById("submitCharacterRecord")?.addEventListener("click", () => {
        void submitCharacterRecord();
    });
    document.getElementById("backToSaveList")?.addEventListener("click", showRoomListView);
    document.getElementById("deleteSave")?.addEventListener("click", () => {
        void deleteCurrentRoom();
    });
    document.getElementById("createSaveNode")?.addEventListener("click", () => {
        void createRoomNode();
    });
    document.getElementById("loadNodeFromPreviewBtn")?.addEventListener("click", () => {
        if (!previewNodeFilename) return;
        bootstrap.Modal.getInstance(document.getElementById("saveNodePreviewModal"))?.hide();
        void restoreRoomNode(previewNodeFilename);
    });
    document.getElementById("confirmRoomCharacterBind")?.addEventListener("click", () => {
        void confirmRoomCharacterBinding();
    });

    populateCharacterSelectors();
    void loadRoomsList();
}

function getLastRoomStorageKey(): string {
    return `trpg_last_room_${window.currentUser?.user_id}`;
}

function isElevatedUser(): boolean {
    return ["ADMIN", "OWNER"].includes(window.currentUser?.role || "");
}

function getCharacterCards(): COC7CharacterCard[] {
    return window.COC7CharacterSheet?.listCharacterCards?.() || [];
}

function isActiveRoomMember(member: RoomMember): boolean {
    return member.is_active !== false && member.status !== "removed";
}

function activeRoomMembers(room: Room): RoomMember[] {
    return (room.members || []).filter(isActiveRoomMember);
}

function populateCharacterSelect(selectId: string): void {
    const select = document.getElementById(selectId) as HTMLSelectElement | null;
    if (!select) return;
    const currentValue = select.value;
    const cards = getCharacterCards();
    select.innerHTML = window.TrpgTemplates.render("select-placeholder-option", { label: "请选择角色卡" });
    cards.forEach((card) => {
        const option = document.createElement("option");
        option.value = card.id;
        option.textContent = card.name;
        select.appendChild(option);
    });
    if (cards.some((card) => card.id === currentValue)) select.value = currentValue;
}

function populateCharacterSelectors(): void {
    populateCharacterSelect("roomBindCharacterSelect");
}

function getSelectedCharacterCardSnapshot(selectId: string): Partial<COC7CharacterCard> | null {
    const cardId = (document.getElementById(selectId) as HTMLSelectElement | null)?.value;
    if (!cardId) return null;
    return window.COC7CharacterSheet?.getCharacterCardSnapshot?.(cardId) || null;
}

async function openCreateRoomModal(): Promise<void> {
    populateCharacterSelectors();
    const scenarioSelect = document.getElementById("roomScenarioSelect") as HTMLSelectElement | null;
    if (scenarioSelect) {
        scenarioSelect.innerHTML = window.TrpgTemplates.render("select-placeholder-option", { label: "请选择剧本" });
        try {
            const data = await TrpgApi.get<ApiResponse<Scenario[]>>("/api/scenarios");
            if (data.success && data.data) {
                data.data.forEach((scenario) => {
                    const option = document.createElement("option");
                    option.value = String(scenario.id);
                    option.textContent = scenario.title;
                    option.dataset.title = scenario.title;
                    scenarioSelect.appendChild(option);
                });
            }
        } catch (error) {
            console.error("加载剧本列表失败:", error);
        }
    }

    const roomNameInput = document.getElementById("saveName") as HTMLInputElement | null;
    if (roomNameInput) roomNameInput.value = "";
    const modalElement = document.getElementById("createSaveModal");
    if (modalElement) new bootstrap.Modal(modalElement).show();
}

async function createRoom(): Promise<void> {
    const roomName = (document.getElementById("saveName") as HTMLInputElement | null)?.value.trim() || "";
    const scenarioSelect = document.getElementById("roomScenarioSelect") as HTMLSelectElement | null;
    const scenarioId = scenarioSelect?.value || "";
    const selectedOption = scenarioSelect?.options[scenarioSelect.selectedIndex];
    const scenarioTitle = selectedOption?.dataset.title || "";

    if (!roomName) {
        showNotification("???????", "error");
        return;
    }
    if (!scenarioId) {
        showNotification("???????", "error");
        return;
    }

    try {
        const data = await TrpgApi.post<ApiResponse<Room>>("/api/rooms", {
            name: roomName,
            scenario_id: Number.parseInt(scenarioId, 10),
            scenario_title: scenarioTitle,
        });
        if (!data.success || !data.data) {
            showNotification(`??????: ${data.message || data.error || "????"}`, "error");
            return;
        }

        bootstrap.Modal.getInstance(document.getElementById("createSaveModal"))?.hide();
        await enterRoom(data.data);
        await loadRoomsList();
        showNotification(`???????????${data.data.room_code || data.data.code || data.data.id}`, "success");
    } catch (error) {
        showNotification(`??????: ${roomErrorMessage(error)}`, "error");
    }
}

async function joinRoomByCode(): Promise<void> {
    const roomCode = (document.getElementById("roomCodeInput") as HTMLInputElement | null)?.value.trim() || "";
    if (!roomCode) {
        showNotification("??????", "error");
        return;
    }

    try {
        const data = await TrpgApi.post<ApiResponse<Room>>("/api/rooms/join", { room_code: roomCode });
        if (!data.success || !data.data) {
            showNotification(`??????: ${data.message || data.error || "????"}`, "error");
            return;
        }
        await enterRoom(data.data);
        await loadRoomsList();
        showNotification("?????", "success");
    } catch (error) {
        showNotification(`??????: ${roomErrorMessage(error)}`, "error");
    }
}

async function loadRoomsList(): Promise<void> {
    try {
        const data = await TrpgApi.get<ApiResponse<Room[]>>("/api/rooms");
        if (data.success && data.data) renderRoomsList(data.data);
    } catch (error) {
        console.error("加载房间列表失败:", error);
    }
}

function renderRoomsList(rooms: Room[]): void {
    const roomListContainer = document.getElementById("saveList");
    if (!roomListContainer) return;

    if (rooms.length === 0) {
        roomListContainer.innerHTML = window.TrpgTemplates.render("room-empty-list");
        return;
    }

    roomListContainer.innerHTML = window.TrpgTemplates.render("room-card-grid", {
        cardsHtml: rooms.map((room) => renderRoomCard(room)).join(""),
    });

    roomListContainer.querySelectorAll<HTMLButtonElement>(".view-room-btn").forEach((button) => {
        button.addEventListener("click", async () => {
            const card = button.closest<HTMLElement>(".save-card");
            const roomId = card?.dataset.roomId;
            if (roomId) await openRoomDetail(roomId);
        });
    });
}

function renderRoomCard(room: Room): string {
    const isActive = currentRoom?.id === room.id;
    const members = activeRoomMembers(room).map((member) => member.username).join(", ") || "-";
    return window.TrpgTemplates.render("room-card", {
        roomId: room.id,
        activeClass: isActive ? "border-primary border-2 shadow-lg" : "",
        activeHeaderHtml: isActive ? window.TrpgTemplates.render("room-active-header") : "",
        name: room.name,
        roomCode: room.room_code || room.code || "-",
        scenarioTitle: room.scenario_title || "未知",
        members,
        actionLabel: isActive ? "管理房间" : "进入房间",
    });
}

async function openRoomDetail(roomId: string): Promise<void> {
    try {
        const data = await TrpgApi.get<ApiResponse<Room>>(`/api/rooms/${roomId}`);
        if (!data.success || !data.data) {
            showNotification(`加载房间失败: ${data.message || data.error || "未知错误"}`, "error");
            return;
        }
        await enterRoom(data.data);
    } catch (error) {
        showNotification(`加载房间失败: ${roomErrorMessage(error)}`, "error");
    }
}

async function enterRoom(room: Room): Promise<void> {
    if (currentRoom?.id) window.leaveSocketRoom?.(currentRoom.id);

    currentRoom = room;
    window.currentRoom = currentRoom;
    TrpgCookies.set(getLastRoomStorageKey(), room.id);

    showRoomDetailView();
    updateRoomDetail(room);
    updateRoomStatusBar(room);
    window.renderChatMessages?.(room.messages || []);
    window.joinSocketRoom?.(room.id);
    startAutosaveTimer();
    await loadRoomNodes();
    promptCurrentUserCharacterBinding(room);
}

function showRoomListView(): void {
    setDisplay("save-list-view", "block");
    setDisplay("save-detail-view", "none");
    void loadRoomsList();
}

function showRoomDetailView(): void {
    setDisplay("save-list-view", "none");
    setDisplay("save-detail-view", "block");
}

function updateRoomDetail(room: Room): void {
    setText("saveDetailTitle", room.name);
    setText("saveCreatedAt", room.created_at || "-");
    setText("saveScenarioTitle", room.scenario_title || "-");
    setText("saveParticipants", activeRoomMembers(room).map((member) => member.username).join(", ") || "-");
    setText("roomDetailCode", room.room_code || room.code || "-");
    setInput("recordRoomName", room.name);
    renderRoomCharacterBindings(room);
}

function renderRoomCharacterBindings(room: Room): void {
    const container = document.getElementById("roomCharacterBindings");
    if (!container) return;
    const members = room.members || [];
    if (members.length === 0) {
        container.innerHTML = window.TrpgTemplates.render("room-character-empty");
        return;
    }

    container.innerHTML = window.TrpgTemplates.render("room-character-binding-table", {
        rowsHtml: members.map((member) => renderRoomMemberBindingRow(room, member)).join(""),
    });

    container.querySelectorAll<HTMLButtonElement>("[data-bind-user-id]").forEach((button) => {
        button.addEventListener("click", () => openRoomCharacterBindModal(button.dataset.bindUserId || ""));
    });
    container.querySelectorAll<HTMLButtonElement>("[data-remove-user-id]").forEach((button) => {
        button.addEventListener("click", () => void removeRoomMember(button.dataset.removeUserId || ""));
    });
    container.querySelectorAll<HTMLButtonElement>("[data-promote-user-id]").forEach((button) => {
        button.addEventListener("click", () => void promoteRoomMember(button.dataset.promoteUserId || ""));
    });
}

function renderRoomMemberBindingRow(room: Room, member: RoomMember): string {
    const card = member.character_card;
    const canManage = canManageRoomMembers(room);
    const isSelf = String(member.user_id) === String(window.currentUser?.user_id);
    const isActive = isActiveRoomMember(member);
    const canChangeCard = isActive && (isElevatedUser() || isSelf);
    const canRemove = isActive && canManage && String(member.user_id) !== String(room.creator_id);
    const canPromote = isActive && canManage && String(member.user_id) !== String(room.creator_id) && member.room_role !== "admin";
    return window.TrpgTemplates.render("room-character-binding-row", {
        userId: member.user_id || "",
        username: member.username || "-",
        rowClass: isActive ? "" : "room-member-removed",
        cardName: card ? card.name || "未命名角色卡" : "未绑定",
        permission: member.permission_label || roomPermissionLabel(room, member),
        changeButtonHtml: canChangeCard ? window.TrpgTemplates.render("room-bind-character-button", { userId: member.user_id || "" }) : "",
        removeButtonHtml: canRemove ? window.TrpgTemplates.render("room-remove-member-button", { userId: member.user_id || "" }) : "",
        promoteButtonHtml: canPromote ? window.TrpgTemplates.render("room-promote-member-button", { userId: member.user_id || "" }) : "",
    });
}

function canManageRoomMembers(room: Room): boolean {
    if (isElevatedUser()) return true;
    const currentMember = activeRoomMembers(room).find((member) => String(member.user_id) === String(window.currentUser?.user_id));
    return currentMember?.room_role === "owner" || currentMember?.room_role === "admin" || String(room.creator_id) === String(window.currentUser?.user_id);
}

function roomPermissionLabel(room: Room, member: RoomMember): string {
    let label = "\u6210\u5458";
    if (["ADMIN", "OWNER"].includes(member.role || "")) label = "\u7ba1\u7406\u5458";
    else if (String(member.user_id) === String(room.creator_id) || member.room_role === "owner") label = "\u623f\u4e3b";
    else if (member.room_role === "admin") label = "\u7ba1\u7406\u5458";
    return isActiveRoomMember(member) ? label : `${label}\uff08\u5df2\u79fb\u9664\uff09`;
}

function promptCurrentUserCharacterBinding(room: Room): void {
    const currentMember = activeRoomMembers(room).find((member) => String(member.user_id) === String(window.currentUser?.user_id));
    if (!currentMember || currentMember.character_card || isElevatedUser()) return;
    openRoomCharacterBindModal(String(currentMember.user_id), "\u9996\u6b21\u52a0\u5165\u8be5\u623f\u95f4\uff0c\u8bf7\u7ed1\u5b9a\u4e00\u5f20\u4f60\u521b\u5efa\u7684\u89d2\u8272\u5361\u3002");
}

function openRoomCharacterBindModal(userId: string, message = "\u8bf7\u9009\u62e9\u8981\u7ed1\u5b9a\u5230\u8be5\u73a9\u5bb6\u7684\u89d2\u8272\u5361\u3002"): void {
    populateCharacterSelect("roomBindCharacterSelect");
    const targetInput = document.getElementById("roomBindTargetUserId") as HTMLInputElement | null;
    if (targetInput) targetInput.value = userId;
    setText("roomCharacterBindMessage", message);
    const modalElement = document.getElementById("roomCharacterBindModal");
    if (modalElement) new bootstrap.Modal(modalElement).show();
}

async function confirmRoomCharacterBinding(): Promise<void> {
    if (!currentRoom?.id) return;
    const userId = roomInputValue("roomBindTargetUserId") || String(window.currentUser?.user_id || "");
    const characterCard = getSelectedCharacterCardSnapshot("roomBindCharacterSelect");
    if (!characterCard) {
        showNotification("请选择要绑定的角色卡", "error");
        return;
    }
    const response = await TrpgApi.put<ApiResponse<Room>>(`/api/rooms/${currentRoom.id}/members/${encodeURIComponent(userId)}/character`, {
        character_card: characterCard,
    });
    if (!response.success || !response.data) {
        showNotification(response.message || response.error || "绑定角色卡失败", "error");
        return;
    }
    bootstrap.Modal.getInstance(document.getElementById("roomCharacterBindModal"))?.hide();
    await enterRoom(response.data);
}

async function removeRoomMember(userId: string): Promise<void> {
    if (!currentRoom?.id || !userId) return;
    const response = await TrpgApi.del<ApiResponse<Room>>(`/api/rooms/${currentRoom.id}/members/${encodeURIComponent(userId)}`);
    if (!response.success || !response.data) {
        showNotification(response.message || response.error || "删除玩家失败", "error");
        return;
    }
    await enterRoom(response.data);
}

async function promoteRoomMember(userId: string): Promise<void> {
    if (!currentRoom?.id || !userId) return;
    const response = await TrpgApi.put<ApiResponse<Room>>(`/api/rooms/${currentRoom.id}/members/${encodeURIComponent(userId)}/role`, { room_role: "admin" });
    if (!response.success || !response.data) {
        showNotification(response.message || response.error || "提权失败", "error");
        return;
    }
    await enterRoom(response.data);
}

function renderCharacterRecordList(records: CharacterRuntimeRecord[]): string {
    if (!records.length) return window.TrpgTemplates.render("room-record-empty");
    const recordsHtml = records.map((record) => window.TrpgTemplates.render("room-record-item", {
        typeLabel: record.type === "san" ? "San 损失" : "伤害",
        value: record.value,
        reason: record.reason || "未知",
        createdAt: record.created_at || "-",
        deleteButtonHtml: isElevatedUser() ? window.TrpgTemplates.render("room-record-delete-button", { recordId: record.id }) : "",
    })).join("");
    return window.TrpgTemplates.render("room-record-list", { recordsHtml });
}

async function submitCharacterRecord(): Promise<void> {
    const payload: CharacterRecordPayload = {
        roomName: roomInputValue("recordRoomName") || currentRoom?.name || "",
        username: roomInputValue("recordUsername"),
        type: recordTypeValue("recordType"),
        value: Number.parseInt(roomInputValue("recordValue") || "1", 10) || 1,
        reason: roomInputValue("recordReason") || "未知",
    };
    await recordCharacterChange(payload);
}

async function recordCharacterChange(payload: CharacterRecordPayload): Promise<unknown> {
    const roomName = String(payload.roomName || payload.roomId || "");
    const username = String(payload.username || "");
    const type = payload.type === "san" ? "san" : "damage";
    const value = typeof payload.value === "number" ? payload.value : Number(payload.value || 1);
    const reason = String(payload.reason || "未知");

    if (!roomName) {
        showNotification("请指定房间名", "error");
        return null;
    }
    if (!username) {
        showNotification("请填写用户名", "error");
        return null;
    }

    const data = await TrpgApi.post<ApiResponse<RoomRecordResponse>>(`/api/rooms/by-name/${encodeURIComponent(roomName)}/character-records`, {
        username,
        type,
        value,
        reason,
    });
    if (!data.success) {
        showNotification(data.message || data.error || "记录失败", "error");
        return null;
    }
    setText("recordToolResult", "记录已保存");
    if (currentRoom?.name === roomName && currentRoom.id) await openRoomDetail(currentRoom.id);
    return data.data || null;
}

async function deleteCharacterRecord(recordId: string): Promise<void> {
    if (!currentRoom?.id || !recordId) return;
    const data = await TrpgApi.del<ApiResponse>(`/api/rooms/${currentRoom.id}/character-records/${recordId}`);
    if (!data.success) {
        showNotification(data.message || data.error || "删除记录失败", "error");
        return;
    }
    await openRoomDetail(currentRoom.id);
}

function updateRoomStatusBar(room: Room): void {
    const statusBar = document.getElementById("saveStatusBar") as HTMLElement | null;
    if (!statusBar) return;
    statusBar.style.display = "block";
    setText("saveStatusName", room.name);
    setText("saveStatusScenario", room.scenario_title || "-");
}

async function deleteCurrentRoom(): Promise<void> {
    if (!currentRoom) return;
    if (!confirm("确定要删除这个房间吗？此操作不可恢复。")) return;

    try {
        const deletingRoomId = currentRoom.id;
        const data = await TrpgApi.del<ApiResponse>(`/api/rooms/${deletingRoomId}`);
        if (!data.success) {
            showNotification(`删除房间失败: ${data.message || data.error || "未知错误"}`, "error");
            return;
        }

        window.leaveSocketRoom?.(deletingRoomId);
        currentRoom = null;
        window.currentRoom = null;
        TrpgCookies.remove(getLastRoomStorageKey());
        stopAutosaveTimer();
        window.clearChatMessages?.();
        showRoomListView();
        showNotification("房间已删除", "success");
    } catch (error) {
        showNotification(`删除房间失败: ${roomErrorMessage(error)}`, "error");
    }
}

async function loadRoomNodes(): Promise<void> {
    if (!currentRoom) return;
    try {
        const data = await TrpgApi.get<ApiResponse<RoomNodeList>>(`/api/rooms/${currentRoom.id}/nodes`);
        if (data.success) renderRoomNodeList(data.data?.nodes || []);
    } catch (error) {
        console.error("加载回档节点失败:", error);
    }
}

function renderRoomNodeList(nodes: RoomNode[]): void {
    const nodeListContainer = document.getElementById("saveNodeList");
    if (!nodeListContainer) return;

    if (nodes.length === 0) {
        nodeListContainer.innerHTML = window.TrpgTemplates.render("room-node-empty");
        return;
    }

    nodeListContainer.innerHTML = window.TrpgTemplates.render("room-node-list", {
        nodesHtml: nodes.map(renderRoomNodeItem).join(""),
    });
    nodeListContainer.querySelectorAll<HTMLButtonElement>(".preview-node-btn").forEach((button) => {
        button.addEventListener("click", () => void previewRoomNode(button.dataset.nodeFilename || ""));
    });
    nodeListContainer.querySelectorAll<HTMLButtonElement>(".load-node-btn").forEach((button) => {
        button.addEventListener("click", () => void restoreRoomNode(button.dataset.nodeFilename || ""));
    });
    nodeListContainer.querySelectorAll<HTMLButtonElement>(".delete-node-btn").forEach((button) => {
        button.addEventListener("click", () => void deleteRoomNode(button.dataset.nodeFilename || ""));
    });
}

function renderRoomNodeItem(node: RoomNode): string {
    return window.TrpgTemplates.render("room-node-item", {
        filename: node.filename,
        createdAt: node.created_at || "-",
        messageCount: node.message_count || 0,
    });
}

async function previewRoomNode(nodeFilename: string): Promise<void> {
    if (!currentRoom || !nodeFilename) return;
    try {
        const data = await TrpgApi.get<ApiResponse<{ messages: ChatMessage[] }>>(`/api/rooms/${currentRoom.id}/nodes/${nodeFilename}`);
        if (!data.success || !data.data) {
            showNotification(`预览回档节点失败: ${data.message || data.error || "未知错误"}`, "error");
            return;
        }
        previewNodeFilename = nodeFilename;
        renderPreviewContent(data.data.messages || []);
        const modalElement = document.getElementById("saveNodePreviewModal");
        if (modalElement) new bootstrap.Modal(modalElement).show();
    } catch (error) {
        showNotification(`预览回档节点失败: ${roomErrorMessage(error)}`, "error");
    }
}

function renderPreviewContent(messages: ChatMessage[]): void {
    const previewContent = document.getElementById("saveNodePreviewContent");
    if (!previewContent) return;

    previewContent.innerHTML = window.TrpgTemplates.render("room-preview-list", {
        messagesHtml: messages.map((message) => window.TrpgTemplates.render("room-preview-message", {
            sender: message.sender_name || message.sender || "未知",
            content: message.content,
        })).join(""),
    });
}

async function createRoomNode(): Promise<void> {
    if (!currentRoom) {
        showNotification("请先进入一个房间", "error");
        return;
    }

    try {
        const data = await TrpgApi.post<ApiResponse>(`/api/rooms/${currentRoom.id}/nodes`);
        if (!data.success) {
            showNotification(`创建回档节点失败: ${data.message || data.error || "未知错误"}`, "error");
            return;
        }
        await loadRoomNodes();
        showNotification("回档节点已创建", "success");
    } catch (error) {
        showNotification(`创建回档节点失败: ${roomErrorMessage(error)}`, "error");
    }
}

async function restoreRoomNode(nodeFilename: string): Promise<void> {
    if (!currentRoom || !nodeFilename) return;
    try {
        const data = await TrpgApi.post<ApiResponse<{ messages: ChatMessage[] }>>(`/api/rooms/${currentRoom.id}/nodes/${nodeFilename}/restore`);
        if (!data.success || !data.data) {
            showNotification(`回档失败: ${data.message || data.error || "未知错误"}`, "error");
            return;
        }
        window.renderChatMessages?.(data.data.messages || []);
        await loadRoomNodes();
        showNotification("已回档到选定节点", "success");
    } catch (error) {
        showNotification(`回档失败: ${roomErrorMessage(error)}`, "error");
    }
}

async function deleteRoomNode(nodeFilename: string): Promise<void> {
    if (!currentRoom || !nodeFilename) return;
    if (!confirm("确定要删除这个回档节点吗？")) return;

    try {
        const data = await TrpgApi.del<ApiResponse>(`/api/rooms/${currentRoom.id}/nodes/${nodeFilename}`);
        if (!data.success) {
            showNotification(`删除回档节点失败: ${data.message || data.error || "未知错误"}`, "error");
            return;
        }
        await loadRoomNodes();
        showNotification("回档节点已删除", "success");
    } catch (error) {
        showNotification(`删除回档节点失败: ${roomErrorMessage(error)}`, "error");
    }
}

function startAutosaveTimer(): void {
    stopAutosaveTimer();
    const enableAutosave = (document.getElementById("enableAutosave") as HTMLInputElement | null)?.checked;
    if (!enableAutosave) return;

    const interval = Number.parseInt((document.getElementById("autosaveInterval") as HTMLInputElement | null)?.value || "300", 10) || 300;
    autosaveTimer = window.setInterval(() => {
        void saveRoomAutosave();
    }, interval * 1000);
}

function stopAutosaveTimer(): void {
    if (autosaveTimer !== null) {
        window.clearInterval(autosaveTimer);
        autosaveTimer = null;
    }
}

async function saveRoomAutosave(): Promise<void> {
    if (!currentRoom) return;
    try {
        await TrpgApi.post<ApiResponse>(`/api/rooms/${currentRoom.id}/autosave`);
    } catch (error) {
        console.error("自动存档失败:", error);
    }
}

async function autoLoadLastRoom(): Promise<void> {
    if (!window.currentUser?.user_id) return;
    const lastRoomId = TrpgCookies.get(getLastRoomStorageKey());
    if (!lastRoomId) return;
    await openRoomDetail(lastRoomId);
}

function clearCurrentRoom(): void {
    if (currentRoom?.id) window.leaveSocketRoom?.(currentRoom.id);
    currentRoom = null;
    window.currentRoom = null;
    stopAutosaveTimer();
    setDisplay("saveStatusBar", "none");
    showRoomListView();
}

function roomInputValue(id: string): string {
    return (document.getElementById(id) as HTMLInputElement | HTMLSelectElement | HTMLTextAreaElement | null)?.value.trim() || "";
}

function recordTypeValue(id: string): "damage" | "san" {
    return roomInputValue(id) === "san" ? "san" : "damage";
}

function setInput(id: string, value: string): void {
    const input = document.getElementById(id) as HTMLInputElement | null;
    if (input) input.value = value;
}

function setText(id: string, value: string): void {
    const element = document.getElementById(id);
    if (element) element.textContent = value;
}

function setDisplay(id: string, value: string): void {
    const element = document.getElementById(id) as HTMLElement | null;
    if (element) element.style.display = value;
}

function roomEscapeHtml(value: unknown): string {
    return String(value ?? "")
        .replace(/&/g, "&amp;")
        .replace(/</g, "&lt;")
        .replace(/>/g, "&gt;")
        .replace(/"/g, "&quot;")
        .replace(/'/g, "&#039;");
}

function roomErrorMessage(error: unknown): string {
    return error instanceof Error ? error.message : String(error);
}

window.initRoomManagement = initRoomManagement;
window.autoLoadLastRoom = autoLoadLastRoom;
window.clearCurrentRoom = clearCurrentRoom;
window.recordCharacterChange = recordCharacterChange;
