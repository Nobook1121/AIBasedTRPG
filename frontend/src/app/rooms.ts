interface RoomNode {
    filename: string;
    created_at?: string;
    message_count?: number;
    automatic?: boolean;
}

interface RoomNodeList {
    nodes: RoomNode[];
}

interface RoomRecordResponse {
    room?: Room;
    record?: CharacterRuntimeRecord;
}

interface RoomEntrySelection {
    action: "join" | "create" | "invisible";
    createCharacter?: boolean;
    characterCard?: Partial<COC7CharacterCard>;
}

let currentRoom: Room | null = null;
let autosaveTimer: number | null = null;
let previewNodeFilename: string | null = null;
let roomEntryCharacterModal: BootstrapModalInstance | null = null;
let roomEntrySelectionResolver: ((result: RoomEntrySelection | null) => void) | null = null;
let roomEntrySelectionSettled = false;
let roomEntrySelectionAction: RoomEntrySelection["action"] = "join";
let roomEntrySelectionRoomId: string | null = null;
const roomActionLocks = new Set<string>();

function initRoomManagement(): void {
    window.currentRoom = currentRoom;
    const roomEntryModalElement = document.getElementById("roomEntryCharacterModal");
    roomEntryCharacterModal = roomEntryModalElement && typeof bootstrap !== "undefined" ? new bootstrap.Modal(roomEntryModalElement) : null;
    roomEntryModalElement?.addEventListener("hidden.bs.modal", () => {
        settleRoomEntrySelection(null);
    });

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
    document.getElementById("startRoomGame")?.addEventListener("click", () => {
        void startCurrentRoomGame();
    });
    document.getElementById("loadNodeFromPreviewBtn")?.addEventListener("click", () => {
        if (!previewNodeFilename) return;
        bootstrap.Modal.getInstance(document.getElementById("saveNodePreviewModal"))?.hide();
        void restoreRoomNode(previewNodeFilename);
    });
    document.getElementById("confirmRoomCharacterBind")?.addEventListener("click", () => {
        void confirmRoomCharacterBinding();
    });
    document.getElementById("confirmRoomEntryCharacter")?.addEventListener("click", () => {
        void confirmRoomEntryCharacterSelection();
    });
    document.getElementById("roomEntryInvisible")?.addEventListener("click", () => {
        settleRoomEntrySelection({ action: "invisible" });
        roomEntryCharacterModal?.hide();
    });
    document.getElementById("roomEntryCreateCharacter")?.addEventListener("click", () => {
        createCharacterFromRoomEntry();
    });

    populateCharacterSelectors();
    window.loadRoomsList = loadRoomsList;
    void loadRoomsList();
}

function getLastRoomStorageKey(): string {
    return `trpg_last_room_${window.currentUser?.user_id}`;
}

function getLastRoomCharacterStorageKey(roomId?: string): string {
    const scopedRoomId = roomId || TrpgCookies.get(getLastRoomStorageKey()) || "";
    return `trpg_last_room_character_${window.currentUser?.user_id}_${scopedRoomId}`;
}

function isElevatedUser(): boolean {
    return ["ADMIN", "OWNER"].includes(window.currentUser?.role || "");
}

function getCharacterCards(): COC7CharacterCard[] {
    return window.COC7CharacterSheet?.listCharacterCards?.() || [];
}

function getRoomEntryCards(): COC7CharacterCard[] {
    const cards = getCharacterCards();
    if (isElevatedUser()) return cards;
    const user = window.currentUser;
    if (!user) return [];
    return cards.filter((card) => {
        const playerId = String(card.playerId || "");
        return playerId === String(user.user_id) || playerId === user.username;
    });
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

function populateRoomEntryCharacterSelect(): void {
    const select = document.getElementById("roomEntryCharacterSelect") as HTMLSelectElement | null;
    const emptyMessage = document.getElementById("roomEntryCharacterEmpty") as HTMLElement | null;
    const confirmButton = document.getElementById("confirmRoomEntryCharacter") as HTMLButtonElement | null;
    if (!select) return;

    const currentValue = select.value;
    const cards = getRoomEntryCards();
    select.innerHTML = window.TrpgTemplates.render("select-placeholder-option", { label: "请选择角色卡" });
    cards.forEach((card) => {
        const option = document.createElement("option");
        option.value = card.id;
        option.textContent = card.name;
        select.appendChild(option);
    });
    const rememberedCardId = roomEntrySelectionRoomId ? TrpgCookies.get(getLastRoomCharacterStorageKey(roomEntrySelectionRoomId)) : "";
    const nextValue = cards.some((card) => card.id === rememberedCardId)
        ? rememberedCardId
        : (cards.some((card) => card.id === currentValue) ? currentValue : "");
    if (nextValue) select.value = nextValue;
    if (emptyMessage) emptyMessage.hidden = cards.length > 0;
    if (confirmButton) confirmButton.disabled = cards.length === 0;
    const invisibleButton = document.getElementById("roomEntryInvisible") as HTMLButtonElement | null;
    if (invisibleButton) invisibleButton.hidden = !isElevatedUser() || roomEntrySelectionAction === "create";
}

async function promptRoomEntryCharacterSelection(action: RoomEntrySelection["action"], roomId: string | null = null): Promise<RoomEntrySelection | null> {
    roomEntrySelectionAction = action;
    roomEntrySelectionRoomId = roomId;
    // Character management loads cards asynchronously during application
    // startup. Refreshing the room list can happen before that request ends.
    await window.reloadCharacterManagement?.();
    populateRoomEntryCharacterSelect();
    roomEntrySelectionSettled = false;
    setText("roomEntryCharacterMessage", action === "create" ? "创建房间前请选择要使用的角色卡。" : "进入房间前请选择要使用的角色卡。");
    if (!roomEntryCharacterModal) return Promise.resolve(null);

    return new Promise((resolve) => {
        roomEntrySelectionResolver = resolve;
        roomEntryCharacterModal?.show();
    });
}

function settleRoomEntrySelection(result: RoomEntrySelection | null): void {
    if (roomEntrySelectionSettled || !roomEntrySelectionResolver) return;
    roomEntrySelectionSettled = true;
    const resolve = roomEntrySelectionResolver;
    roomEntrySelectionResolver = null;
    resolve(result);
}

async function confirmRoomEntryCharacterSelection(): Promise<void> {
    const characterCard = getSelectedCharacterCardSnapshot("roomEntryCharacterSelect");
    if (!characterCard) {
        showNotification("请选择要使用的角色卡", "error");
        return;
    }
    settleRoomEntrySelection({ action: roomEntrySelectionAction, characterCard });
    if (roomEntrySelectionRoomId) {
        syncRoomCharacterSelection(roomEntrySelectionRoomId, characterCard);
    }
    roomEntryCharacterModal?.hide();
}

function createCharacterFromRoomEntry(): void {
    settleRoomEntrySelection({ action: roomEntrySelectionAction, createCharacter: true });
    roomEntryCharacterModal?.hide();
    window.switchMainTab?.("characters");
    document.getElementById("createCharacter")?.click();
}

function getSelectedCharacterCardSnapshot(selectId: string): Partial<COC7CharacterCard> | null {
    const cardId = (document.getElementById(selectId) as HTMLSelectElement | null)?.value;
    if (!cardId) return null;
    return window.COC7CharacterSheet?.getCharacterCardSnapshot?.(cardId) || null;
}

function syncRoomCharacterSelection(roomId: string, characterCard: Partial<COC7CharacterCard> | null): void {
    if (!window.currentUser?.user_id || !roomId) return;
    const storageKey = getLastRoomCharacterStorageKey(roomId);
    const characterId = String(characterCard?.id || "").trim();
    if (!characterId) {
        TrpgCookies.remove(storageKey);
        return;
    }
    TrpgCookies.set(storageKey, characterId);
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
    return runRoomAction("create-room", "confirmCreateSave", async () => {
        await createRoomUnlocked();
    });
}

async function createRoomUnlocked(): Promise<void> {
    const roomName = (document.getElementById("saveName") as HTMLInputElement | null)?.value.trim() || "";
    const scenarioSelect = document.getElementById("roomScenarioSelect") as HTMLSelectElement | null;
    const scenarioId = scenarioSelect?.value || "";
    const selectedOption = scenarioSelect?.options[scenarioSelect.selectedIndex];
    const scenarioTitle = selectedOption?.dataset.title || "";

    if (!roomName) {
        showNotification("请输入房间名称", "error");
        return;
    }
    if (!scenarioId) {
        showNotification("请选择剧本", "error");
        return;
    }

    bootstrap.Modal.getInstance(document.getElementById("createSaveModal"))?.hide();
    const roomEntrySelection = await promptRoomEntryCharacterSelection("create");
    if (!roomEntrySelection || roomEntrySelection.createCharacter || roomEntrySelection.action === "invisible") return;

    try {
        const data = await TrpgApi.post<ApiResponse<Room>>("/api/rooms", {
            name: roomName,
            scenario_id: Number.parseInt(scenarioId, 10),
            scenario_title: scenarioTitle,
            character_card: roomEntrySelection.characterCard,
        });
        if (!data.success || !data.data) {
            showNotification(`创建房间失败：${data.message || data.error || "未知错误"}`, "error");
            return;
        }

        bootstrap.Modal.getInstance(document.getElementById("createSaveModal"))?.hide();
        await enterRoom(data.data);
        await loadRoomsList();
        showNotification(`房间已创建：${data.data.room_code || data.data.code || data.data.id}`, "success");
    } catch (error) {
        showNotification(`创建房间失败：${roomErrorMessage(error)}`, "error");
    }
}

async function joinRoomByCode(): Promise<void> {
    return runRoomAction("join-room", "joinRoom", async () => {
        await joinRoomByCodeUnlocked();
    });
}

async function joinRoomByCodeUnlocked(): Promise<void> {
    const roomCode = (document.getElementById("roomCodeInput") as HTMLInputElement | null)?.value.trim() || "";
    if (!roomCode) {
        showNotification("请输入房间码", "error");
        return;
    }

    const roomEntrySelection = await promptRoomEntryCharacterSelection("join");
    if (!roomEntrySelection) return;
    if (roomEntrySelection.createCharacter || roomEntrySelection.action === "create") return;

    try {
        const endpoint = roomEntrySelection.action === "invisible" ? "/api/rooms/spectate" : "/api/rooms/join";
        const data = await TrpgApi.post<ApiResponse<Room>>(endpoint, {
            room_code: roomCode,
            ...(roomEntrySelection.action === "invisible" ? {} : { character_card: roomEntrySelection.characterCard }),
        });
        if (!data.success || !data.data) {
            showNotification(`加入房间失败：${data.message || data.error || "未知错误"}`, "error");
            return;
        }
        await enterRoom(data.data);
        await loadRoomsList();
        showNotification(roomEntrySelection.action === "invisible" ? "已隐身进入房间" : "已加入房间", "success");
    } catch (error) {
        showNotification(`加入房间失败：${roomErrorMessage(error)}`, "error");
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
    roomListContainer.querySelectorAll<HTMLButtonElement>(".leave-room-btn").forEach((button) => {
        button.addEventListener("click", () => void leaveRoom(button.dataset.roomId || ""));
    });
}

function renderRoomCard(room: Room): string {
    const isActive = currentRoom?.id === room.id;
    const isCurrentMember = activeRoomMembers(room).some((member) => String(member.user_id) === String(window.currentUser?.user_id || ""));
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
        leaveButtonHtml: isCurrentMember && room.invisible_view !== true
            ? window.TrpgTemplates.render("room-leave-button", { roomId: room.id })
            : "",
    });
}

async function leaveRoom(roomId: string): Promise<void> {
    if (!roomId) return;
    if (!window.confirm("确定退出这个房间吗？")) return;
    try {
        const response = await TrpgApi.post<ApiResponse<Room>>(`/api/rooms/${encodeURIComponent(roomId)}/leave`, {});
        if (!response.success) {
            showNotification(response.message || response.error || "退出房间失败", "error");
            return;
        }
        if (currentRoom?.id === roomId) {
            window.leaveSocketRoom?.(roomId);
            currentRoom = null;
            window.currentRoom = null;
            TrpgCookies.remove(getLastRoomStorageKey());
            showRoomListView();
        }
        await loadRoomsList();
        showNotification("已退出房间", "success");
    } catch (error) {
        showNotification(`退出房间失败：${roomErrorMessage(error)}`, "error");
    }
}

async function openRoomDetail(roomId: string): Promise<void> {
    try {
        const data = await TrpgApi.get<ApiResponse<Room>>(`/api/rooms/${roomId}`);
        if (!data.success || !data.data) {
            showNotification(`加载房间失败: ${data.message || data.error || "未知错误"}`, "error");
            return;
        }

        // A refresh restores the room from its cookie. If the server already
        // has an active member record with a bound card, re-enter directly.
        // Prompting here races character-card loading and can incorrectly
        // present an empty selector, while also rebinding the card.
        const currentUserId = String(window.currentUser?.user_id || "");
        const existingMember = currentUserId
            ? activeRoomMembers(data.data).find((member) => String(member.user_id) === currentUserId)
            : undefined;
        if (existingMember?.character_card || (isElevatedUser() && !existingMember)) {
            await enterRoom(data.data);
            return;
        }

        const roomEntrySelection = await promptRoomEntryCharacterSelection("join", roomId);
        if (!roomEntrySelection || roomEntrySelection.createCharacter || roomEntrySelection.action === "create") return;

        if (roomEntrySelection.action === "invisible") {
            const spectateResponse = await TrpgApi.get<ApiResponse<Room>>(`/api/rooms/${encodeURIComponent(roomId)}/spectate`);
            if (!spectateResponse.success || !spectateResponse.data) {
                showNotification(spectateResponse.message || spectateResponse.error || "隐身进入房间失败", "error");
                return;
            }
            await enterRoom(spectateResponse.data);
            showNotification("已隐身进入房间", "success");
            return;
        }

        const userId = currentUserId;
        if (!userId) return;

        if (!existingMember) {
            const joinResponse = await TrpgApi.post<ApiResponse<Room>>("/api/rooms/join", {
                room_code: data.data.room_code || data.data.code,
                character_card: roomEntrySelection.characterCard,
            });
            if (!joinResponse.success || !joinResponse.data) {
                showNotification(joinResponse.message || joinResponse.error || "加入房间失败", "error");
                return;
            }
            await enterRoom(joinResponse.data);
            showNotification("已加入房间", "success");
            return;
        }

        const bindResponse = await TrpgApi.put<ApiResponse<Room>>(
            `/api/rooms/${encodeURIComponent(roomId)}/members/${encodeURIComponent(userId)}/character`,
            { character_card: roomEntrySelection.characterCard },
        );
        if (!bindResponse.success || !bindResponse.data) {
            showNotification(bindResponse.message || bindResponse.error || "绑定角色卡失败", "error");
            return;
        }
        await enterRoom(bindResponse.data);
    } catch (error) {
        showNotification(`加载房间失败: ${roomErrorMessage(error)}`, "error");
    }
}

async function enterRoom(room: Room): Promise<void> {
    if (currentRoom?.id) window.leaveSocketRoom?.(currentRoom.id);

    currentRoom = room;
    window.currentRoom = currentRoom;
    window.restoreThinkingState?.();
    window.resumePendingAIRequest?.();
    const invisibleView = room.invisible_view === true;
    if (invisibleView) TrpgCookies.remove(getLastRoomStorageKey());
    else TrpgCookies.set(getLastRoomStorageKey(), room.id);

    showRoomDetailView();
    updateRoomDetail(room);
    updateRoomStatusBar(room);
    const messages = Array.isArray(room.messages)
        ? room.messages
        : window.getCurrentChatMessages?.() || [];
    window.renderChatMessages?.(messages);
    setText("homeRoomTitle", room.name);
    setText("homeRoomOnlineCount", formatRoomOnlineCount(room));
    const selfMember = activeRoomMembers(room).find((member) => String(member.user_id) === String(window.currentUser?.user_id));
    if (selfMember?.character_card) {
        syncRoomCharacterSelection(room.id, selfMember.character_card);
    }
    window.setChatReadOnly?.(invisibleView);
    applyInvisibleRoomView(invisibleView);
    if (invisibleView) {
        stopAutosaveTimer();
        renderRoomNodeList([]);
        return;
    }
    window.joinSocketRoom?.(room.id);
    startAutosaveTimer();
    await loadRoomNodes();
}

function applyInvisibleRoomView(invisible: boolean): void {
    document.querySelectorAll<HTMLElement>("[data-room-sensitive]").forEach((element) => {
        element.hidden = invisible;
    });
    const onlineCount = document.getElementById("homeRoomOnlineCount") as HTMLElement | null;
    if (onlineCount) onlineCount.hidden = invisible;
    setDisplay("saveStatusBar", invisible ? "none" : "block");
    const deleteButton = document.getElementById("deleteSave") as HTMLButtonElement | null;
    const createNodeButton = document.getElementById("createSaveNode") as HTMLButtonElement | null;
    if (deleteButton) deleteButton.hidden = invisible;
    if (createNodeButton) createNodeButton.hidden = invisible;
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
    setText("roomDetailTokens", Number(room.token_usage?.total_tokens || 0).toLocaleString());
    setInput("recordRoomName", room.name);
    setText("homeRoomOnlineCount", formatRoomOnlineCount(room));
    renderRoomCharacterBindings(room);
    updateStartGameButton(room);
}

function updateStartGameButton(room: Room): void {
    const button = document.getElementById("startRoomGame") as HTMLButtonElement | null;
    if (!button) return;
    const isOwner = String(room.creator_id || room.owner_id || "") === String(window.currentUser?.user_id || "");
    button.hidden = room.invisible_view === true || room.started === true || !isOwner;
}

async function startCurrentRoomGame(): Promise<void> {
    if (!currentRoom?.id) return;
    const button = document.getElementById("startRoomGame") as HTMLButtonElement | null;
    if (button) button.disabled = true;
    try {
        const data = await TrpgApi.post<ApiResponse<{ room: Room; messages: ChatMessage[] }>>(`/api/rooms/${encodeURIComponent(currentRoom.id)}/start`);
        if (!data.success || !data.data) {
            showNotification(data.message || data.error || "开始游戏失败", "error");
            return;
        }
        currentRoom = { ...currentRoom, ...data.data.room, messages: data.data.messages };
        window.currentRoom = currentRoom;
        updateRoomDetail(currentRoom);
        window.renderChatMessages?.(data.data.messages || []);
        showNotification("游戏已开始", "success");
    } catch (error) {
        showNotification(`开始游戏失败：${roomErrorMessage(error)}`, "error");
    } finally {
        if (button) button.disabled = false;
    }
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
    container.querySelectorAll<HTMLButtonElement>("[data-room-character-preview]").forEach((button) => {
        button.addEventListener("click", () => previewRoomCharacter(button.dataset.roomCharacterPreview || ""));
    });
}

function renderRoomMemberBindingRow(room: Room, member: RoomMember): string {
    const card = member.character_card;
    const canManage = canManageRoomMembers(room);
    const isSelf = String(member.user_id) === String(window.currentUser?.user_id);
    const isActive = isActiveRoomMember(member);
    const isOnline = member.is_online === true;
    const canChangeCard = isActive && (isElevatedUser() || isSelf || canManage);
    const canRemove = isActive && canManage && String(member.user_id) !== String(room.creator_id);
    const canPromote = isActive && canManage && String(member.user_id) !== String(room.creator_id) && member.room_role !== "admin";
    const cardPreviewHtml = card
        ? `<button type="button" class="btn btn-link p-0 room-character-preview" data-room-character-preview="${encodeURIComponent(JSON.stringify(card))}">${escapeRoomHtml(card.name || "未命名角色卡")}</button>`
        : "未绑定";
    return window.TrpgTemplates.render("room-character-binding-row", {
        userId: member.user_id || "",
        username: `${member.username || "-"}（${isOnline ? "在线" : "离线"}）`,
        rowClass: isActive ? "" : "room-member-removed",
        cardName: card ? card.name || "未命名角色卡" : "未绑定",
        cardPreviewHtml,
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
    return runRoomAction(`bind-character:${currentRoom.id}:${userId}`, "confirmRoomCharacterBind", async () => {
        await confirmRoomCharacterBindingUnlocked(userId);
    });
}

async function confirmRoomCharacterBindingUnlocked(userId: string): Promise<void> {
    if (!currentRoom?.id) return;
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
    if (String(userId) === String(window.currentUser?.user_id)) {
        syncRoomCharacterSelection(currentRoom.id, characterCard);
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
    return runRoomAction("submit-character-record", "submitCharacterRecord", async () => {
        await submitCharacterRecordUnlocked();
    });
}

async function submitCharacterRecordUnlocked(): Promise<void> {
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
        nodeLabel: node.automatic ? "自动存档" : "回档节点",
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
        await loadRoomNodes();
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
    window.setChatReadOnly?.(false);
    applyInvisibleRoomView(false);
    setDisplay("saveStatusBar", "none");
    const startButton = document.getElementById("startRoomGame") as HTMLButtonElement | null;
    if (startButton) startButton.hidden = true;
    setText("homeRoomTitle", "未加入房间");
    setText("homeRoomOnlineCount", "在线玩家 0/0");
    showRoomListView();
}

function previewRoomCharacter(encodedCard: string): void {
    try {
        const rawCard = JSON.parse(decodeURIComponent(encodedCard)) as Partial<COC7CharacterCard>;
        const card = window.COC7CharacterSheet?.createCharacterCard?.(rawCard as COC7CharacterCardInput) || (rawCard as COC7CharacterCard);
        const previewHtml = window.COC7CharacterSheet?.renderCharacterDetail?.(card) || `<h4>${escapeRoomHtml(card.name || "未命名角色卡")}</h4>`;
        const modalElement = document.createElement("div");
        modalElement.className = "modal fade";
        modalElement.innerHTML = `<div class="modal-dialog modal-xl"><div class="modal-content"><div class="modal-header"><h5 class="modal-title">角色卡预览</h5><button type="button" class="btn-close" data-bs-dismiss="modal"></button></div><div class="modal-body">${previewHtml}</div></div></div>`;
        document.body.appendChild(modalElement);
        const instance = new bootstrap.Modal(modalElement);
        instance.show();
        modalElement.addEventListener("hidden.bs.modal", () => modalElement.remove());
    } catch {
        showNotification("角色卡预览失败", "error");
    }
}

function formatRoomOnlineCount(room: Room): string {
    const members = room.members || [];
    const online = members.filter((member) => member.is_online === true).length;
    const total = members.filter((member) => member.status !== "removed").length;
    return window.TrpgI18n?.t("room.status.online_players.count", `在线玩家 ${online}/${total}`, { online, total })
        || `在线玩家 ${online}/${total}`;
}

function escapeRoomHtml(value: unknown): string {
    return String(value ?? "")
        .replace(/&/g, "&amp;")
        .replace(/</g, "&lt;")
        .replace(/>/g, "&gt;")
        .replace(/\"/g, "&quot;")
        .replace(/'/g, "&#039;");
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
    if (!element) return;
    const fallbackKeys: Record<string, [string, string]> = {
        homeRoomTitle: ["home.not_joined", "未加入房间"],
        homeRoomOnlineCount: ["room.status.online_players", "在线玩家 0/0"],
        saveStatusName: ["room.status.not_joined", "未加入"],
    };
    const fallback = fallbackKeys[id];
    const nextValue = fallback && value === fallback[1]
        ? window.TrpgI18n?.t(fallback[0], value) || value
        : value;
    if (fallback) element.removeAttribute("data-i18n");
    element.textContent = nextValue;
}

async function runRoomAction(actionKey: string, buttonId: string, action: () => Promise<void>): Promise<void> {
    if (roomActionLocks.has(actionKey)) return;
    roomActionLocks.add(actionKey);
    setRoomButtonBusy(buttonId, true);
    try {
        await action();
    } finally {
        roomActionLocks.delete(actionKey);
        setRoomButtonBusy(buttonId, false);
    }
}

function setRoomButtonBusy(buttonId: string, busy: boolean): void {
    const button = document.getElementById(buttonId) as HTMLButtonElement | null;
    if (!button) return;
    button.disabled = busy;
    button.dataset.busy = busy ? "true" : "false";
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
