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

function populateCharacterSelect(selectId: string): void {
    const select = document.getElementById(selectId) as HTMLSelectElement | null;
    if (!select) return;
    const currentValue = select.value;
    const cards = getCharacterCards();
    select.innerHTML = '<option value="">请选择角色卡</option>';
    cards.forEach((card) => {
        const option = document.createElement("option");
        option.value = card.id;
        option.textContent = card.name;
        select.appendChild(option);
    });
    if (cards.some((card) => card.id === currentValue)) select.value = currentValue;
}

function populateCharacterSelectors(): void {
    populateCharacterSelect("roomCharacterSelect");
    populateCharacterSelect("joinRoomCharacterSelect");
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
        scenarioSelect.innerHTML = '<option value="">请选择剧本</option>';
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
    const characterCard = getSelectedCharacterCardSnapshot("roomCharacterSelect");

    if (!roomName) {
        showNotification("请输入房间名称", "error");
        return;
    }
    if (!scenarioId) {
        showNotification("请选择房间剧本", "error");
        return;
    }
    if (!characterCard && !isElevatedUser()) {
        showNotification("请选择要绑定的角色卡", "error");
        return;
    }

    try {
        const data = await TrpgApi.post<ApiResponse<Room>>("/api/rooms", {
            name: roomName,
            scenario_id: Number.parseInt(scenarioId, 10),
            scenario_title: scenarioTitle,
            character_card: characterCard,
        });
        if (!data.success || !data.data) {
            showNotification(`创建房间失败: ${data.message || data.error || "未知错误"}`, "error");
            return;
        }

        bootstrap.Modal.getInstance(document.getElementById("createSaveModal"))?.hide();
        await enterRoom(data.data);
        await loadRoomsList();
        showNotification(`房间创建成功，房间码：${data.data.room_code || data.data.code || data.data.id}`, "success");
    } catch (error) {
        showNotification(`创建房间失败: ${roomErrorMessage(error)}`, "error");
    }
}

async function joinRoomByCode(): Promise<void> {
    populateCharacterSelectors();
    const roomCode = (document.getElementById("roomCodeInput") as HTMLInputElement | null)?.value.trim() || "";
    const characterCard = getSelectedCharacterCardSnapshot("joinRoomCharacterSelect");
    if (!characterCard && !isElevatedUser()) {
        showNotification("请选择要绑定的角色卡", "error");
        return;
    }
    if (!roomCode) {
        showNotification("请输入房间码", "error");
        return;
    }

    try {
        const data = await TrpgApi.post<ApiResponse<Room>>("/api/rooms/join", { room_code: roomCode, character_card: characterCard });
        if (!data.success || !data.data) {
            showNotification(`加入房间失败: ${data.message || data.error || "未知错误"}`, "error");
            return;
        }
        await enterRoom(data.data);
        await loadRoomsList();
        showNotification("已加入房间", "success");
    } catch (error) {
        showNotification(`加入房间失败: ${roomErrorMessage(error)}`, "error");
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
        roomListContainer.innerHTML = '<div class="text-center text-muted py-5">暂无房间，请创建房间或输入房间码加入。</div>';
        return;
    }

    roomListContainer.innerHTML = `
        <div class="row row-cols-1 row-cols-md-2 row-cols-lg-3 g-4">
            ${rooms.map((room) => renderRoomCard(room)).join("")}
        </div>
    `;

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
    const members = (room.members || []).map((member) => member.username).join(", ") || "-";
    return `
        <div class="col">
            <div class="card save-card h-100 ${isActive ? "border-primary border-2 shadow-lg" : ""}" data-room-id="${roomEscapeHtml(room.id)}">
                ${isActive ? '<div class="card-header bg-primary text-white text-center py-2"><small><i class="fa fa-check-circle"></i> 当前房间</small></div>' : ""}
                <div class="card-body">
                    <h5 class="card-title">${roomEscapeHtml(room.name)}</h5>
                    <p class="card-text mb-2">
                        <small class="text-muted">房间码：${roomEscapeHtml(room.room_code || room.code || "-")}</small><br>
                        <small class="text-muted">剧本：${roomEscapeHtml(room.scenario_title || "未知")}</small><br>
                        <small class="text-muted">成员：${roomEscapeHtml(members)}</small>
                    </p>
                </div>
                <div class="card-footer bg-transparent border-0">
                    <button class="btn btn-primary w-100 view-room-btn">${isActive ? "管理房间" : "进入房间"}</button>
                </div>
            </div>
        </div>
    `;
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
    setText("saveParticipants", (room.members || []).map((member) => member.username).join(", ") || "-");
    setText("roomDetailCode", room.room_code || room.code || "-");
    setInput("recordRoomName", room.name);
    renderRoomCharacterBindings(room);
}

function renderRoomCharacterBindings(room: Room): void {
    const container = document.getElementById("roomCharacterBindings");
    if (!container) return;
    const members = room.members || [];
    if (members.length === 0) {
        container.innerHTML = '<div class="text-muted">暂无参与玩家</div>';
        return;
    }

    container.innerHTML = members.map((member) => {
        const card = member.character_card;
        const state = member.character_state || {};
        const injuryRecords = state.injury_records || [];
        const sanityRecords = state.sanity_records || [];
        return `
            <div class="room-character-binding border rounded p-3 mb-3">
                <div class="d-flex justify-content-between align-items-start gap-3">
                    <div>
                        <div class="fw-bold">${roomEscapeHtml(member.username || "-")}</div>
                        <div class="text-muted">${card ? roomEscapeHtml(card.name || "未命名角色") : "未绑定角色卡"}</div>
                    </div>
                    <div class="text-end">
                        <span class="badge bg-primary">HP ${state.current_hp ?? "-"} / ${state.max_hp ?? "-"}</span>
                        <span class="badge bg-secondary">San ${state.current_san ?? "-"} / ${state.max_san ?? "-"}</span>
                    </div>
                </div>
                <div class="row mt-3">
                    <div class="col-md-6">
                        <h6>生命值/受伤记录</h6>
                        ${renderCharacterRecordList(injuryRecords)}
                    </div>
                    <div class="col-md-6">
                        <h6>San 值鉴定和损失记录</h6>
                        ${renderCharacterRecordList(sanityRecords)}
                    </div>
                </div>
            </div>
        `;
    }).join("");

    container.querySelectorAll<HTMLButtonElement>("[data-record-id]").forEach((button) => {
        button.addEventListener("click", () => {
            void deleteCharacterRecord(button.dataset.recordId || "");
        });
    });
}

function renderCharacterRecordList(records: CharacterRuntimeRecord[]): string {
    if (!records.length) return '<div class="text-muted small">暂无记录</div>';
    return `<div class="list-group">${records.map((record) => `
        <div class="list-group-item d-flex justify-content-between gap-2">
            <div>
                <div>${record.type === "san" ? "San 损失" : "伤害"} ${record.value}</div>
                <small class="text-muted">${roomEscapeHtml(record.reason || "未知")} · ${roomEscapeHtml(record.created_at || "-")}</small>
            </div>
            ${isElevatedUser() ? `<button type="button" class="btn btn-sm btn-outline-danger" data-record-id="${roomEscapeHtml(record.id)}">删除</button>` : ""}
        </div>
    `).join("")}</div>`;
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
        nodeListContainer.innerHTML = '<div class="text-center text-muted py-3">暂无回档节点</div>';
        return;
    }

    nodeListContainer.innerHTML = `<div class="list-group">${nodes.map(renderRoomNodeItem).join("")}</div>`;
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
    return `
        <div class="list-group-item list-group-item-action d-flex justify-content-between align-items-center">
            <div>
                <h6 class="mb-1">回档节点</h6>
                <small class="text-muted">创建时间：${roomEscapeHtml(node.created_at || "-")} | 消息数：${node.message_count || 0}</small>
            </div>
            <div>
                <button class="btn btn-sm btn-secondary preview-node-btn me-2" data-node-filename="${roomEscapeHtml(node.filename)}">预览</button>
                <button class="btn btn-sm btn-primary load-node-btn me-2" data-node-filename="${roomEscapeHtml(node.filename)}">回档</button>
                <button class="btn btn-sm btn-danger delete-node-btn" data-node-filename="${roomEscapeHtml(node.filename)}">删除</button>
            </div>
        </div>
    `;
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

    previewContent.innerHTML = `
        <div class="preview-messages">
            ${messages.map((message) => `
                <div class="preview-message mb-3 p-3 border rounded bg-light">
                    <div class="fw-bold text-primary mb-2">${roomEscapeHtml(message.sender_name || message.sender || "未知")}</div>
                    <div class="markdown-body">${roomEscapeHtml(message.content)}</div>
                </div>
            `).join("")}
        </div>
    `;
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
