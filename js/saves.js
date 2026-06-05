// 存档管理模块

let currentSave = null;
let autosaveTimer = null;
let previewNodeFilename = null;

function initSaveManagement() {
    const createSaveBtn = document.getElementById('createSave');
    if (createSaveBtn) createSaveBtn.addEventListener('click', openCreateSaveModal);

    const backToSaveListBtn = document.getElementById('backToSaveList');
    if (backToSaveListBtn) backToSaveListBtn.addEventListener('click', showSaveListView);

    const deleteSaveBtn = document.getElementById('deleteSave');
    if (deleteSaveBtn) deleteSaveBtn.addEventListener('click', deleteCurrentSave);

    const confirmCreateSaveBtn = document.getElementById('confirmCreateSave');
    if (confirmCreateSaveBtn) confirmCreateSaveBtn.addEventListener('click', createSave);

    const createSaveNodeBtn = document.getElementById('createSaveNode');
    if (createSaveNodeBtn) createSaveNodeBtn.addEventListener('click', createSaveNode);

    const loadNodeFromPreviewBtn = document.getElementById('loadNodeFromPreviewBtn');
    if (loadNodeFromPreviewBtn) {
        loadNodeFromPreviewBtn.addEventListener('click', function() {
            if (previewNodeFilename) {
                const modal = bootstrap.Modal.getInstance(document.getElementById('saveNodePreviewModal'));
                if (modal) modal.hide();
                loadSaveNode(previewNodeFilename);
            }
        });
    }

    loadSavesList();
    console.log('存档管理初始化成功');
}

async function openCreateSaveModal() {
    const scenarioSelect = document.getElementById('saveScenario');
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

    const saveNameInput = document.getElementById('saveName');
    if (saveNameInput) saveNameInput.value = '';

    const modal = new bootstrap.Modal(document.getElementById('createSaveModal'));
    modal.show();
}

async function createSave() {
    const saveName = document.getElementById('saveName')?.value?.trim();
    const scenarioSelect = document.getElementById('saveScenario');
    const scenarioId = scenarioSelect?.value;
    const selectedOption = scenarioSelect?.options[scenarioSelect?.selectedIndex];
    const scenarioTitle = selectedOption?.dataset?.title || '';

    if (!saveName) {
        showNotification('请输入存档名称', 'error');
        return;
    }

    if (!scenarioId) {
        showNotification('请选择绑定的剧本', 'error');
        return;
    }

    try {
        const data = await TrpgApi.post('/api/saves', {
            name: saveName,
            scenario_id: parseInt(scenarioId),
            scenario_title: scenarioTitle
        });

        if (data.success) {
            showNotification('创建存档成功', 'success');
            const modal = bootstrap.Modal.getInstance(document.getElementById('createSaveModal'));
            if (modal) modal.hide();
            loadSavesList();
        } else {
            showNotification('创建存档失败: ' + data.message, 'error');
        }
    } catch (error) {
        console.error('创建存档失败:', error);
        showNotification('创建存档失败: ' + error.message, 'error');
    }
}

async function loadSavesList() {
    try {
        const data = await TrpgApi.get('/api/saves');
        if (data.success && data.data) {
            renderSavesList(data.data);
        }
    } catch (error) {
        console.error('加载存档列表失败:', error);
    }
}

function renderSavesList(saves) {
    const saveListContainer = document.getElementById('saveList');
    if (!saveListContainer) return;

    if (saves.length === 0) {
        saveListContainer.innerHTML = '<div class="text-center text-muted py-5">暂无存档，请点击"创建存档"按钮创建</div>';
        return;
    }

    let html = '<div class="row row-cols-1 row-cols-md-2 row-cols-lg-3 g-4">';
    saves.forEach(save => {
        const isActive = currentSave && currentSave.id == save.id;
        html += `
            <div class="col">
                <div class="card save-card h-100 ${isActive ? 'border-primary border-2 shadow-lg' : ''}" data-save-id="${save.id}" data-save-name="${save.name}">
                    ${isActive ? '<div class="card-header bg-primary text-white text-center py-2"><small><i class="fa fa-check-circle"></i> 当前已加载</small></div>' : ''}
                    <div class="card-body">
                        <h5 class="card-title">${save.name}</h5>
                        <p class="card-text">
                            <small class="text-muted">创建时间：${save.created_at}</small><br>
                            <small class="text-muted">绑定剧本：${save.scenario_title || '未知'}</small>
                        </p>
                    </div>
                    <div class="card-footer bg-transparent border-0">
                        <button class="btn btn-primary w-100 view-save-btn">${isActive ? '管理存档' : '查看存档'}</button>
                    </div>
                </div>
            </div>
        `;
    });
    html += '</div>';

    saveListContainer.innerHTML = html;

    saveListContainer.querySelectorAll('.view-save-btn').forEach(btn => {
        btn.addEventListener('click', function() {
            const card = this.closest('.save-card');
            const saveId = card.dataset.saveId;
            const saveName = card.dataset.saveName;
            viewSaveDetail(saveId, saveName);
        });
    });
}

async function viewSaveDetail(saveId, saveName) {
    currentSave = { id: saveId, name: saveName };

    try {
        const data = await TrpgApi.get(`/api/saves/${saveId}/nodes`);
        if (data.success) {
            showSaveDetailView();
            document.getElementById('saveDetailTitle').textContent = saveName;
            document.getElementById('saveCreatedAt').textContent = data.data.info.created_at || '-';
            document.getElementById('saveScenarioTitle').textContent = data.data.info.scenario_title || '-';
            document.getElementById('saveParticipants').textContent = (data.data.info.participants || []).join(', ') || '-';
            renderSaveNodeList(data.data.nodes);
            updateSaveStatusBar(saveName, data.data.info.scenario_title);
            loadAutosave();
            startAutosaveTimer();
            updateCurrentSaveStatus();

            localStorage.setItem('lastSaveId', saveId);
            localStorage.setItem('lastSaveName', saveName);
            localStorage.setItem('lastSaveScenario', data.data.info.scenario_title || '');
        }
    } catch (error) {
        console.error('查看存档详情失败:', error);
        showNotification('查看存档详情失败: ' + error.message, 'error');
    }
}

function showSaveListView() {
    document.getElementById('save-list-view').style.display = 'block';
    document.getElementById('save-detail-view').style.display = 'none';
    stopAutosaveTimer();
    loadSavesList();
}

function updateCurrentSaveStatus() {
    const currentSaveStatus = document.getElementById('currentSaveStatus');
    const currentSaveName = document.getElementById('currentSaveName');

    if (currentSave && currentSave.name) {
        currentSaveStatus.style.display = 'block';
        currentSaveName.textContent = currentSave.name;
    } else {
        currentSaveStatus.style.display = 'none';
    }
}

function showSaveDetailView() {
    document.getElementById('save-list-view').style.display = 'none';
    document.getElementById('save-detail-view').style.display = 'block';
}

async function deleteCurrentSave() {
    if (!currentSave) return;

    if (!confirm('确定要删除这个存档吗？此操作不可恢复！')) return;

    try {
        const data = await TrpgApi.del(`/api/saves/${currentSave.id}`);
        if (data.success) {
            showNotification('删除存档成功', 'success');
            showSaveListView();
        } else {
            showNotification('删除存档失败: ' + data.message, 'error');
        }
    } catch (error) {
        console.error('删除存档失败:', error);
        showNotification('删除存档失败: ' + error.message, 'error');
    }
}

function renderSaveNodeList(nodes) {
    const nodeListContainer = document.getElementById('saveNodeList');
    if (!nodeListContainer) return;

    if (nodes.length === 0) {
        nodeListContainer.innerHTML = '<div class="text-center text-muted py-3">暂无存档节点</div>';
        return;
    }

    let html = '<div class="list-group">';
    nodes.forEach(node => {
        html += `
            <div class="list-group-item list-group-item-action d-flex justify-content-between align-items-center">
                <div>
                    <h6 class="mb-1">存档节点</h6>
                    <small class="text-muted">创建时间：${node.created_at} | 消息数：${node.message_count}</small>
                </div>
                <div>
                    <button class="btn btn-sm btn-secondary preview-node-btn me-2" data-node-filename="${node.filename}">预览</button>
                    <button class="btn btn-sm btn-primary load-node-btn me-2" data-node-filename="${node.filename}">加载</button>
                    <button class="btn btn-sm btn-danger delete-node-btn" data-node-filename="${node.filename}">删除</button>
                </div>
            </div>
        `;
    });
    html += '</div>';

    nodeListContainer.innerHTML = html;

    nodeListContainer.querySelectorAll('.preview-node-btn').forEach(btn => {
        btn.addEventListener('click', function() {
            previewSaveNode(this.dataset.nodeFilename);
        });
    });

    nodeListContainer.querySelectorAll('.load-node-btn').forEach(btn => {
        btn.addEventListener('click', function() {
            loadSaveNode(this.dataset.nodeFilename);
        });
    });

    nodeListContainer.querySelectorAll('.delete-node-btn').forEach(btn => {
        btn.addEventListener('click', function() {
            deleteSaveNode(this.dataset.nodeFilename);
        });
    });
}

async function previewSaveNode(nodeFilename) {
    if (!currentSave) return;

    try {
        const data = await TrpgApi.get(`/api/saves/${currentSave.id}/nodes/${nodeFilename}`);
        if (data.success) {
            previewNodeFilename = nodeFilename;
            renderPreviewContent(data.data.messages);
            const modal = new bootstrap.Modal(document.getElementById('saveNodePreviewModal'));
            modal.show();
        } else {
            showNotification('预览存档节点失败: ' + data.message, 'error');
        }
    } catch (error) {
        console.error('预览存档节点失败:', error);
        showNotification('预览存档节点失败: ' + error.message, 'error');
    }
}

function renderPreviewContent(messages) {
    const previewContent = document.getElementById('saveNodePreviewContent');
    if (!previewContent) return;

    let html = '<div class="preview-messages">';

    messages.forEach(msg => {
        html += `
            <div class="preview-message mb-3 p-3 border rounded bg-light">
                <div class="fw-bold text-primary mb-2">${msg.sender}: </div>
                <div class="markdown-body">${msg.content}</div>
            </div>
        `;
    });

    html += '</div>';
    previewContent.innerHTML = html;
}

async function createSaveNode() {
    if (!currentSave) {
        showNotification('请先选择一个存档', 'error');
        return;
    }

    const messages = getCurrentChatMessages();
    if (messages.length === 0) {
        showNotification('当前没有聊天记录可保存', 'error');
        return;
    }

    try {
        const data = await TrpgApi.post(`/api/saves/${currentSave.id}/nodes`, {
            messages: messages
        });
        if (data.success) {
            showNotification('创建存档节点成功', 'success');
            viewSaveDetail(currentSave.id, currentSave.name);
        } else {
            showNotification('创建存档节点失败: ' + data.message, 'error');
        }
    } catch (error) {
        console.error('创建存档节点失败:', error);
        showNotification('创建存档节点失败: ' + error.message, 'error');
    }
}

async function loadSaveNode(nodeFilename) {
    if (!currentSave) return;

    try {
        const data = await TrpgApi.get(`/api/saves/${currentSave.id}/nodes/${nodeFilename}`);
        if (data.success) {
            renderChatMessages(data.data.messages);
            updateSaveStatusBar(currentSave.name, '');
            showNotification('加载存档节点成功', 'success');
        } else {
            showNotification('加载存档节点失败: ' + data.message, 'error');
        }
    } catch (error) {
        console.error('加载存档节点失败:', error);
        showNotification('加载存档节点失败: ' + error.message, 'error');
    }
}

async function deleteSaveNode(nodeFilename) {
    if (!currentSave) return;

    if (!confirm('确定要删除这个存档节点吗？此操作不可恢复！')) return;

    try {
        const data = await TrpgApi.del(`/api/saves/${currentSave.id}/nodes/${nodeFilename}`);
        if (data.success) {
            showNotification('删除存档节点成功', 'success');
            viewSaveDetail(currentSave.id, currentSave.name);
        } else {
            showNotification('删除存档节点失败: ' + data.message, 'error');
        }
    } catch (error) {
        console.error('删除存档节点失败:', error);
        showNotification('删除存档节点失败: ' + error.message, 'error');
    }
}

function startAutosaveTimer() {
    stopAutosaveTimer();
    const interval = parseInt(document.getElementById('autosaveInterval')?.value) || 60;
    autosaveTimer = setInterval(saveAutosave, interval * 1000);
    console.log('自动存档定时器已启动，间隔:', interval, '秒');
}

function stopAutosaveTimer() {
    if (autosaveTimer) {
        clearInterval(autosaveTimer);
        autosaveTimer = null;
        console.log('自动存档定时器已停止');
    }
}

async function saveAutosave() {
    if (!currentSave) return;

    const enableAutosave = document.getElementById('enableAutosave')?.checked;
    if (!enableAutosave) return;

    const messages = getCurrentChatMessages();

    try {
        await TrpgApi.post(`/api/saves/${currentSave.id}/autosave`, {
            messages: messages
        });
    } catch (error) {
        console.error('保存自动存档失败:', error);
    }
}

async function loadAutosave() {
    if (!currentSave) return;

    try {
        const data = await TrpgApi.get(`/api/saves/${currentSave.id}/autosave`);
        if (data.success && data.data && data.data.messages && data.data.messages.length > 0) {
            renderChatMessages(data.data.messages);
            showNotification('已自动加载存档', 'success');
        }
    } catch (error) {
        console.error('加载自动存档失败:', error);
    }
}

function updateSaveStatusBar(saveName, scenarioTitle) {
    const saveStatusBar = document.getElementById('saveStatusBar');
    const saveStatusName = document.getElementById('saveStatusName');
    const saveStatusScenario = document.getElementById('saveStatusScenario');

    if (saveStatusBar && saveName) {
        saveStatusBar.style.display = 'block';
        if (saveStatusName) saveStatusName.textContent = saveName;
        if (saveStatusScenario) saveStatusScenario.textContent = scenarioTitle ? `剧本：${scenarioTitle}` : '';
    }
}

async function autoLoadLastSave() {
    const lastSaveId = localStorage.getItem('lastSaveId');
    const lastSaveName = localStorage.getItem('lastSaveName');
    const lastSaveScenario = localStorage.getItem('lastSaveScenario');

    if (!lastSaveId || !lastSaveName) return;

    try {
        const data = await TrpgApi.get(`/api/saves/${lastSaveId}/nodes`);
        if (data.success) {
            currentSave = { id: lastSaveId, name: lastSaveName };
            updateSaveStatusBar(lastSaveName, lastSaveScenario);
            startAutosaveTimer();
            updateCurrentSaveStatus();

            const autosaveData = await TrpgApi.get(`/api/saves/${lastSaveId}/autosave`);
            if (autosaveData.success && autosaveData.data && autosaveData.data.messages && autosaveData.data.messages.length > 0) {
                renderChatMessages(autosaveData.data.messages);
            }
        }
    } catch (error) {
        console.error('自动加载上次存档失败:', error);
    }
}
