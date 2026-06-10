// @ts-nocheck
// Room management replaces the legacy save system.

let currentRoom = null;
let autosaveTimer = null;
let previewNodeFilename = null;

function initRoomManagement() {
    window.currentRoom = currentRoom;

    document.getElementById('createSave')?.addEventListener('click', openCreateRoomModal);
    document.getElementById('confirmCreateSave')?.addEventListener('click', createRoom);
    document.getElementById('joinRoom')?.addEventListener('click', joinRoomByCode);
    document.getElementById('backToSaveList')?.addEventListener('click', showRoomListView);
    document.getElementById('deleteSave')?.addEventListener('click', deleteCurrentRoom);
    document.getElementById('createSaveNode')?.addEventListener('click', createRoomNode);
    document.getElementById('loadNodeFromPreviewBtn')?.addEventListener('click', function() {
        if (!previewNodeFilename) return;
        bootstrap.Modal.getInstance(document.getElementById('saveNodePreviewModal'))?.hide();
        restoreRoomNode(previewNodeFilename);
    });

    loadRoomsList();
}

function getLastRoomStorageKey() {
    return `trpg_last_room_${window.currentUser?.user_id}`;
}

async function openCreateRoomModal() {
    const scenarioSelect = document.getElementById('roomScenarioSelect');
    if (scenarioSelect) {
        scenarioSelect.innerHTML = '<option value="">请选择剧本</option>';
        try {
            const data = await TrpgApi.get('/api/scenarios');
            if (data.success && data.data) {
                data.data.forEach(scenario => {
                    const option = document.createElement('option');
                    option.value = scenario.id;
                    option.textContent = scenario.title;
                    option.dataset.title = scenario.title;
                    scenarioSelect.appendChild(option);
                });
            }
        } catch (error) {
            console.error('加载剧本列表失败:', error);
        }
    }

    const roomNameInput = document.getElementById('saveName');
    if (roomNameInput) roomNameInput.value = '';
    new bootstrap.Modal(document.getElementById('createSaveModal')).show();
}

async function createRoom() {
    const roomName = document.getElementById('saveName')?.value?.trim();
    const scenarioSelect = document.getElementById('roomScenarioSelect');
    const scenarioId = scenarioSelect?.value;
    const selectedOption = scenarioSelect?.options[scenarioSelect?.selectedIndex];
    const scenarioTitle = selectedOption?.dataset?.title || '';

    if (!roomName) {
        showNotification('请输入房间名称', 'error');
        return;
    }
    if (!scenarioId) {
        showNotification('请选择房间剧本', 'error');
        return;
    }

    try {
        const data = await TrpgApi.post('/api/rooms', {
            name: roomName,
            scenario_id: parseInt(scenarioId),
            scenario_title: scenarioTitle,
        });
        if (!data.success) {
            showNotification('创建房间失败: ' + data.message, 'error');
            return;
        }

        bootstrap.Modal.getInstance(document.getElementById('createSaveModal'))?.hide();
        await enterRoom(data.data);
        await loadRoomsList();
        showNotification(`房间创建成功，房间码：${data.data.room_code}`, 'success');
    } catch (error) {
        showNotification('创建房间失败: ' + error.message, 'error');
    }
}

async function joinRoomByCode() {
    const roomCode = document.getElementById('roomCodeInput')?.value?.trim();
    if (!roomCode) {
        showNotification('请输入房间码', 'error');
        return;
    }

    try {
        const data = await TrpgApi.post('/api/rooms/join', { room_code: roomCode });
        if (!data.success) {
            showNotification('加入房间失败: ' + data.message, 'error');
            return;
        }
        await enterRoom(data.data);
        await loadRoomsList();
        showNotification('已加入房间', 'success');
    } catch (error) {
        showNotification('加入房间失败: ' + error.message, 'error');
    }
}

async function loadRoomsList() {
    try {
        const data = await TrpgApi.get('/api/rooms');
        if (data.success && data.data) {
            renderRoomsList(data.data);
        }
    } catch (error) {
        console.error('加载房间列表失败:', error);
    }
}

function renderRoomsList(rooms) {
    const roomListContainer = document.getElementById('saveList');
    if (!roomListContainer) return;

    if (rooms.length === 0) {
        roomListContainer.innerHTML = '<div class="text-center text-muted py-5">暂无房间，请创建房间或输入房间码加入。</div>';
        return;
    }

    let html = '<div class="row row-cols-1 row-cols-md-2 row-cols-lg-3 g-4">';
    rooms.forEach(room => {
        const isActive = currentRoom && currentRoom.id === room.id;
        const members = (room.members || []).map(member => member.username).join(', ') || '-';
        html += `
            <div class="col">
                <div class="card save-card h-100 ${isActive ? 'border-primary border-2 shadow-lg' : ''}" data-room-id="${room.id}">
                    ${isActive ? '<div class="card-header bg-primary text-white text-center py-2"><small><i class="fa fa-check-circle"></i> 当前房间</small></div>' : ''}
                    <div class="card-body">
                        <h5 class="card-title">${room.name}</h5>
                        <p class="card-text mb-2">
                            <small class="text-muted">房间码：${room.room_code}</small><br>
                            <small class="text-muted">剧本：${room.scenario_title || '未知'}</small><br>
                            <small class="text-muted">成员：${members}</small>
                        </p>
                    </div>
                    <div class="card-footer bg-transparent border-0">
                        <button class="btn btn-primary w-100 view-room-btn">${isActive ? '管理房间' : '进入房间'}</button>
                    </div>
                </div>
            </div>
        `;
    });
    html += '</div>';
    roomListContainer.innerHTML = html;

    roomListContainer.querySelectorAll('.view-room-btn').forEach(btn => {
        btn.addEventListener('click', async function() {
            const card = this.closest('.save-card');
            await openRoomDetail(card.dataset.roomId);
        });
    });
}

async function openRoomDetail(roomId) {
    try {
        const data = await TrpgApi.get(`/api/rooms/${roomId}`);
        if (!data.success) {
            showNotification('加载房间失败: ' + data.message, 'error');
            return;
        }
        await enterRoom(data.data);
    } catch (error) {
        showNotification('加载房间失败: ' + error.message, 'error');
    }
}

async function enterRoom(room) {
    if (currentRoom?.id && window.leaveSocketRoom) {
        window.leaveSocketRoom(currentRoom.id);
    }

    currentRoom = room;
    window.currentRoom = currentRoom;
    TrpgCookies.set(getLastRoomStorageKey(), room.id);

    showRoomDetailView();
    updateRoomDetail(room);
    updateRoomStatusBar(room);
    window.renderChatMessages(room.messages || []);
    window.joinSocketRoom?.(room.id);
    startAutosaveTimer();
    await loadRoomNodes();
}

function showRoomListView() {
    document.getElementById('save-list-view').style.display = 'block';
    document.getElementById('save-detail-view').style.display = 'none';
    loadRoomsList();
}

function showRoomDetailView() {
    document.getElementById('save-list-view').style.display = 'none';
    document.getElementById('save-detail-view').style.display = 'block';
}

function updateRoomDetail(room) {
    document.getElementById('saveDetailTitle').textContent = room.name;
    document.getElementById('saveCreatedAt').textContent = room.created_at || '-';
    document.getElementById('saveScenarioTitle').textContent = room.scenario_title || '-';
    document.getElementById('saveParticipants').textContent = (room.members || []).map(member => member.username).join(', ') || '-';
    const roomCode = document.getElementById('roomDetailCode');
    if (roomCode) roomCode.textContent = room.room_code || '-';
}

function updateRoomStatusBar(room) {
    const statusBar = document.getElementById('saveStatusBar');
    const statusName = document.getElementById('saveStatusName');
    const statusScenario = document.getElementById('saveStatusScenario');
    if (!statusBar) return;

    statusBar.style.display = 'block';
    if (statusName) statusName.textContent = room.name;
    if (statusScenario) statusScenario.textContent = room.scenario_title || '-';
}

async function deleteCurrentRoom() {
    if (!currentRoom) return;
    if (!confirm('确定要删除这个房间吗？此操作不可恢复。')) return;

    try {
        const data = await TrpgApi.del(`/api/rooms/${currentRoom.id}`);
        if (!data.success) {
            showNotification('删除房间失败: ' + data.message, 'error');
            return;
        }

        window.leaveSocketRoom?.(currentRoom.id);
        currentRoom = null;
        window.currentRoom = null;
        TrpgCookies.remove(getLastRoomStorageKey());
        stopAutosaveTimer();
        window.clearChatMessages?.();
        showRoomListView();
        showNotification('房间已删除', 'success');
    } catch (error) {
        showNotification('删除房间失败: ' + error.message, 'error');
    }
}

async function loadRoomNodes() {
    if (!currentRoom) return;
    try {
        const data = await TrpgApi.get(`/api/rooms/${currentRoom.id}/nodes`);
        if (data.success) {
            renderRoomNodeList(data.data.nodes || []);
        }
    } catch (error) {
        console.error('加载回档节点失败:', error);
    }
}

function renderRoomNodeList(nodes) {
    const nodeListContainer = document.getElementById('saveNodeList');
    if (!nodeListContainer) return;

    if (nodes.length === 0) {
        nodeListContainer.innerHTML = '<div class="text-center text-muted py-3">暂无回档节点</div>';
        return;
    }

    let html = '<div class="list-group">';
    nodes.forEach(node => {
        html += `
            <div class="list-group-item list-group-item-action d-flex justify-content-between align-items-center">
                <div>
                    <h6 class="mb-1">回档节点</h6>
                    <small class="text-muted">创建时间：${node.created_at} | 消息数：${node.message_count}</small>
                </div>
                <div>
                    <button class="btn btn-sm btn-secondary preview-node-btn me-2" data-node-filename="${node.filename}">预览</button>
                    <button class="btn btn-sm btn-primary load-node-btn me-2" data-node-filename="${node.filename}">回档</button>
                    <button class="btn btn-sm btn-danger delete-node-btn" data-node-filename="${node.filename}">删除</button>
                </div>
            </div>
        `;
    });
    html += '</div>';
    nodeListContainer.innerHTML = html;

    nodeListContainer.querySelectorAll('.preview-node-btn').forEach(btn => {
        btn.addEventListener('click', function() {
            previewRoomNode(this.dataset.nodeFilename);
        });
    });
    nodeListContainer.querySelectorAll('.load-node-btn').forEach(btn => {
        btn.addEventListener('click', function() {
            restoreRoomNode(this.dataset.nodeFilename);
        });
    });
    nodeListContainer.querySelectorAll('.delete-node-btn').forEach(btn => {
        btn.addEventListener('click', function() {
            deleteRoomNode(this.dataset.nodeFilename);
        });
    });
}

async function previewRoomNode(nodeFilename) {
    if (!currentRoom) return;
    try {
        const data = await TrpgApi.get(`/api/rooms/${currentRoom.id}/nodes/${nodeFilename}`);
        if (!data.success) {
            showNotification('预览回档节点失败: ' + data.message, 'error');
            return;
        }
        previewNodeFilename = nodeFilename;
        renderPreviewContent(data.data.messages || []);
        new bootstrap.Modal(document.getElementById('saveNodePreviewModal')).show();
    } catch (error) {
        showNotification('预览回档节点失败: ' + error.message, 'error');
    }
}

function renderPreviewContent(messages) {
    const previewContent = document.getElementById('saveNodePreviewContent');
    if (!previewContent) return;

    let html = '<div class="preview-messages">';
    messages.forEach(message => {
        html += `
            <div class="preview-message mb-3 p-3 border rounded bg-light">
                <div class="fw-bold text-primary mb-2">${message.sender_name || message.sender || '未知'}</div>
                <div class="markdown-body">${message.content}</div>
            </div>
        `;
    });
    html += '</div>';
    previewContent.innerHTML = html;
}

async function createRoomNode() {
    if (!currentRoom) {
        showNotification('请先进入一个房间', 'error');
        return;
    }

    try {
        const data = await TrpgApi.post(`/api/rooms/${currentRoom.id}/nodes`);
        if (!data.success) {
            showNotification('创建回档节点失败: ' + data.message, 'error');
            return;
        }
        await loadRoomNodes();
        showNotification('回档节点已创建', 'success');
    } catch (error) {
        showNotification('创建回档节点失败: ' + error.message, 'error');
    }
}

async function restoreRoomNode(nodeFilename) {
    if (!currentRoom) return;
    try {
        const data = await TrpgApi.post(`/api/rooms/${currentRoom.id}/nodes/${nodeFilename}/restore`);
        if (!data.success) {
            showNotification('回档失败: ' + data.message, 'error');
            return;
        }
        window.renderChatMessages(data.data.messages || []);
        await loadRoomNodes();
        showNotification('已回档到选定节点', 'success');
    } catch (error) {
        showNotification('回档失败: ' + error.message, 'error');
    }
}

async function deleteRoomNode(nodeFilename) {
    if (!currentRoom) return;
    if (!confirm('确定要删除这个回档节点吗？')) return;

    try {
        const data = await TrpgApi.del(`/api/rooms/${currentRoom.id}/nodes/${nodeFilename}`);
        if (!data.success) {
            showNotification('删除回档节点失败: ' + data.message, 'error');
            return;
        }
        await loadRoomNodes();
        showNotification('回档节点已删除', 'success');
    } catch (error) {
        showNotification('删除回档节点失败: ' + error.message, 'error');
    }
}

function startAutosaveTimer() {
    stopAutosaveTimer();
    const enableAutosave = document.getElementById('enableAutosave')?.checked;
    if (!enableAutosave) return;

    const interval = parseInt(document.getElementById('autosaveInterval')?.value) || 300;
    autosaveTimer = setInterval(saveRoomAutosave, interval * 1000);
}

function stopAutosaveTimer() {
    if (autosaveTimer) {
        clearInterval(autosaveTimer);
        autosaveTimer = null;
    }
}

async function saveRoomAutosave() {
    if (!currentRoom) return;
    try {
        await TrpgApi.post(`/api/rooms/${currentRoom.id}/autosave`);
    } catch (error) {
        console.error('自动存档失败:', error);
    }
}

async function autoLoadLastRoom() {
    if (!window.currentUser?.user_id) return;

    const lastRoomId = TrpgCookies.get(getLastRoomStorageKey());
    if (!lastRoomId) return;
    await openRoomDetail(lastRoomId);
}

function clearCurrentRoom() {
    if (currentRoom?.id) {
        window.leaveSocketRoom?.(currentRoom.id);
    }
    currentRoom = null;
    window.currentRoom = null;
    stopAutosaveTimer();
    document.getElementById('saveStatusBar').style.display = 'none';
    showRoomListView();
}

window.initRoomManagement = initRoomManagement;
window.autoLoadLastRoom = autoLoadLastRoom;
window.clearCurrentRoom = clearCurrentRoom;
