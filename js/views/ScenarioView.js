// 剧本视图类 - MVC架构的View层
class ScenarioView {
    constructor() {
        this.scenarioList = document.getElementById('scenarioList');
        this.initEventListeners();
        // 绑定剧本操作按钮事件（只绑定一次）
        this.bindScenarioActions();
    }

    // 初始化事件监听器
    initEventListeners() {
        // 创建剧本按钮
        document.getElementById('createScenario').addEventListener('click', () => {
            this.onCreateScenarioClick();
        });

        // 导入剧本按钮
        document.getElementById('importScenario').addEventListener('click', () => {
            document.getElementById('importScenarioFile').click();
        });

        // 文件选择事件
        document.getElementById('importScenarioFile').addEventListener('change', async (e) => {
            if (this.onImportScenario) {
                await this.onImportScenario(e.target.files);
            }
            // 清空文件输入，允许重复选择同一文件
            e.target.value = '';
        });

        // 保存剧本按钮
        document.getElementById('saveScenario').addEventListener('click', async () => {
            if (this.onSaveScenario) {
                await this.onSaveScenario();
            }
        });

        // 添加场景按钮
        document.getElementById('addScene').addEventListener('click', () => {
            this.addScene();
        });

        // 添加结局按钮
        document.getElementById('addEnding').addEventListener('click', () => {
            this.addEnding();
        });
    }

    // 渲染剧本列表
    renderScenarioList(scenarios) {
        this.scenarioList.innerHTML = '';

        scenarios.forEach(scenario => {
            const card = document.createElement('div');
            card.className = 'scenario-card';
            card.innerHTML = `
                <img src="https://via.placeholder.com/250x150?text=${scenario.title}" alt="${scenario.title}">
                <div class="scenario-card-body">
                    <div class="scenario-card-title">${scenario.title}</div>
                    <p>作者: ${scenario.author}</p>
                    <p>推荐人数: ${scenario.playerCount}</p>
                    <div class="scenario-card-actions">
                        <button class="btn btn-sm btn-primary preview-scenario" data-id="${scenario.id}">预览</button>
                        <button class="btn btn-sm btn-secondary edit-scenario" data-id="${scenario.id}">编辑</button>
                        <button class="btn btn-sm btn-danger delete-scenario" data-id="${scenario.id}">删除</button>
                    </div>
                </div>
            `;
            this.scenarioList.appendChild(card);
        });
    }

    // 绑定剧本操作按钮事件
    bindScenarioActions() {
        // 使用事件委托来绑定事件，确保动态添加的元素也能响应
        this.scenarioList.addEventListener('click', async (e) => {
            const btn = e.target.closest('button');
            if (!btn) return;

            const id = parseInt(btn.getAttribute('data-id'));
            if (isNaN(id)) return;

            if (btn.classList.contains('preview-scenario')) {
                if (this.onPreviewScenario) {
                    this.onPreviewScenario(id);
                }
            } else if (btn.classList.contains('edit-scenario')) {
                if (this.onEditScenario) {
                    this.onEditScenario(id);
                }
            } else if (btn.classList.contains('delete-scenario')) {
                if (this.onDeleteScenario) {
                    await this.onDeleteScenario(id);
                }
            }
        });
    }

    // 打开创建剧本模态框
    openCreateModal() {
        const modal = new bootstrap.Modal(document.getElementById('scenarioModal'));
        
        // 重置表单
        this.resetScenarioForm();
        
        // 绑定删除事件
        this.bindRemoveEvents();
        
        modal.show();
    }

    // 打开编辑剧本模态框
    openEditModal(scenario) {
        const modal = new bootstrap.Modal(document.getElementById('scenarioModal'));
        
        // 填充表单
        this.fillScenarioForm(scenario);
        
        // 绑定删除事件
        this.bindRemoveEvents();
        
        modal.show();
    }

    // 重置剧本表单
    resetScenarioForm() {
        document.getElementById('scenarioTitle').value = '';
        document.getElementById('scenarioAuthor').value = '';
        document.getElementById('scenarioPlayerCount').value = '0';
        document.getElementById('scenarioNotes').value = '';
        document.getElementById('scenarioBackground').value = '';
        document.getElementById('scenarioPreparation').value = '';
        
        // 重置场景和结局
        const scenesContainer = document.getElementById('scenarioScenes');
        const endingsContainer = document.getElementById('scenarioEndings');
        scenesContainer.innerHTML = `
            <div class="scene-item mb-3 p-3 border rounded">
                <div class="d-flex justify-content-between align-items-center mb-2">
                    <h6>场景 1</h6>
                    <button type="button" class="btn btn-sm btn-danger remove-scene">删除</button>
                </div>
                <div class="form-group">
                    <label>场景内容</label>
                    <textarea class="form-control" rows="3"></textarea>
                </div>
                <div class="form-group mt-2">
                    <label>场景标记</label>
                    <textarea class="form-control" rows="2" placeholder="AI总结内容将显示在这里"></textarea>
                </div>
            </div>
        `;
        endingsContainer.innerHTML = `
            <div class="ending-item mb-3 p-3 border rounded">
                <div class="d-flex justify-content-between align-items-center mb-2">
                    <h6>结局 1</h6>
                    <button type="button" class="btn btn-sm btn-danger remove-ending">删除</button>
                </div>
                <div class="form-group">
                    <label>结局内容</label>
                    <textarea class="form-control" rows="3"></textarea>
                </div>
                <div class="form-group mt-2">
                    <label>结局标记</label>
                    <textarea class="form-control" rows="2" placeholder="AI总结内容将显示在这里"></textarea>
                </div>
            </div>
        `;
    }

    // 填充剧本表单
    fillScenarioForm(scenario) {
        document.getElementById('scenarioTitle').value = scenario.title;
        document.getElementById('scenarioAuthor').value = scenario.author;
        document.getElementById('scenarioPlayerCount').value = scenario.playerCount;
        document.getElementById('scenarioNotes').value = scenario.notes || '';
        document.getElementById('scenarioBackground').value = scenario.background || '';
        document.getElementById('scenarioPreparation').value = scenario.preparation || '';
        
        // 填充场景
        const scenesContainer = document.getElementById('scenarioScenes');
        scenesContainer.innerHTML = '';
        scenario.scenes.forEach((scene, index) => {
            const sceneItem = document.createElement('div');
            sceneItem.className = 'scene-item mb-3 p-3 border rounded';
            sceneItem.innerHTML = `
                <div class="d-flex justify-content-between align-items-center mb-2">
                    <h6>场景 ${index + 1}</h6>
                    <button type="button" class="btn btn-sm btn-danger remove-scene">删除</button>
                </div>
                <div class="form-group">
                    <label>场景内容</label>
                    <textarea class="form-control" rows="3">${scene.content}</textarea>
                </div>
                <div class="form-group mt-2">
                    <label>场景标记</label>
                    <textarea class="form-control" rows="2" placeholder="AI总结内容将显示在这里">${scene.marker}</textarea>
                </div>
            `;
            scenesContainer.appendChild(sceneItem);
        });
        
        // 填充结局
        const endingsContainer = document.getElementById('scenarioEndings');
        endingsContainer.innerHTML = '';
        scenario.endings.forEach((ending, index) => {
            const endingItem = document.createElement('div');
            endingItem.className = 'ending-item mb-3 p-3 border rounded';
            endingItem.innerHTML = `
                <div class="d-flex justify-content-between align-items-center mb-2">
                    <h6>结局 ${index + 1}</h6>
                    <button type="button" class="btn btn-sm btn-danger remove-ending">删除</button>
                </div>
                <div class="form-group">
                    <label>结局内容</label>
                    <textarea class="form-control" rows="3">${ending.content}</textarea>
                </div>
                <div class="form-group mt-2">
                    <label>结局标记</label>
                    <textarea class="form-control" rows="2" placeholder="AI总结内容将显示在这里">${ending.marker}</textarea>
                </div>
            `;
            endingsContainer.appendChild(endingItem);
        });
    }

    // 绑定删除事件
    bindRemoveEvents() {
        // 删除场景
        document.querySelectorAll('.remove-scene').forEach(btn => {
            btn.addEventListener('click', () => {
                const sceneItem = btn.closest('.scene-item');
                sceneItem.remove();
                this.updateSceneNumbers();
            });
        });
        
        // 删除结局
        document.querySelectorAll('.remove-ending').forEach(btn => {
            btn.addEventListener('click', () => {
                const endingItem = btn.closest('.ending-item');
                endingItem.remove();
                this.updateEndingNumbers();
            });
        });
    }

    // 更新场景编号
    updateSceneNumbers() {
        const scenes = document.querySelectorAll('.scene-item');
        scenes.forEach((scene, index) => {
            scene.querySelector('h6').textContent = `场景 ${index + 1}`;
        });
    }

    // 更新结局编号
    updateEndingNumbers() {
        const endings = document.querySelectorAll('.ending-item');
        endings.forEach((ending, index) => {
            ending.querySelector('h6').textContent = `结局 ${index + 1}`;
        });
    }

    // 添加场景
    addScene() {
        const scenesContainer = document.getElementById('scenarioScenes');
        const sceneCount = scenesContainer.querySelectorAll('.scene-item').length + 1;
        
        const sceneItem = document.createElement('div');
        sceneItem.className = 'scene-item mb-3 p-3 border rounded';
        sceneItem.innerHTML = `
            <div class="d-flex justify-content-between align-items-center mb-2">
                <h6>场景 ${sceneCount}</h6>
                <button type="button" class="btn btn-sm btn-danger remove-scene">删除</button>
            </div>
            <div class="form-group">
                <label>场景内容</label>
                <textarea class="form-control" rows="3"></textarea>
            </div>
            <div class="form-group mt-2">
                <label>场景标记</label>
                <textarea class="form-control" rows="2" placeholder="AI总结内容将显示在这里"></textarea>
            </div>
        `;
        
        scenesContainer.appendChild(sceneItem);
        this.bindRemoveEvents();
    }

    // 添加结局
    addEnding() {
        const endingsContainer = document.getElementById('scenarioEndings');
        const endingCount = endingsContainer.querySelectorAll('.ending-item').length + 1;
        
        const endingItem = document.createElement('div');
        endingItem.className = 'ending-item mb-3 p-3 border rounded';
        endingItem.innerHTML = `
            <div class="d-flex justify-content-between align-items-center mb-2">
                <h6>结局 ${endingCount}</h6>
                <button type="button" class="btn btn-sm btn-danger remove-ending">删除</button>
            </div>
            <div class="form-group">
                <label>结局内容</label>
                <textarea class="form-control" rows="3"></textarea>
            </div>
            <div class="form-group mt-2">
                <label>结局标记</label>
                <textarea class="form-control" rows="2" placeholder="AI总结内容将显示在这里"></textarea>
            </div>
        `;
        
        endingsContainer.appendChild(endingItem);
        this.bindRemoveEvents();
    }

    // 获取表单数据
    getFormData() {
        // 表单验证
        const title = document.getElementById('scenarioTitle').value.trim();
        const author = document.getElementById('scenarioAuthor').value.trim();
        const playerCount = document.getElementById('scenarioPlayerCount').value;
        
        if (!title || !author || !playerCount) {
            throw new Error('请填写所有必填项！');
        }
        
        // 收集场景数据
        const scenes = [];
        document.querySelectorAll('.scene-item').forEach((scene, index) => {
            const content = scene.querySelectorAll('textarea')[0].value;
            const marker = scene.querySelectorAll('textarea')[1].value;
            scenes.push({
                id: index + 1,
                content: content,
                marker: marker
            });
        });
        
        // 收集结局数据
        const endings = [];
        document.querySelectorAll('.ending-item').forEach((ending, index) => {
            const content = ending.querySelectorAll('textarea')[0].value;
            const marker = ending.querySelectorAll('textarea')[1].value;
            endings.push({
                id: index + 1,
                content: content,
                marker: marker
            });
        });
        
        // 构建剧本数据
        return {
            title: title,
            author: author,
            playerCount: parseInt(playerCount),
            notes: document.getElementById('scenarioNotes').value,
            background: document.getElementById('scenarioBackground').value,
            preparation: document.getElementById('scenarioPreparation').value,
            scenes: scenes,
            endings: endings
        };
    }

    // 预览剧本
    previewScenario(scenario) {
        if (scenario) {
            let previewContent = `
                <h3>${scenario.title}</h3>
                <p><strong>作者:</strong> ${scenario.author}</p>
                <p><strong>推荐人数:</strong> ${scenario.playerCount}</p>
                <p><strong>备注:</strong> ${scenario.notes || '无'}</p>
                <p><strong>背景/引入:</strong> ${scenario.background || '无'}</p>
                <p><strong>游戏准备:</strong> ${scenario.preparation || '无'}</p>
                <h4>场景</h4>
            `;
            
            scenario.scenes.forEach(scene => {
                previewContent += `
                    <div class="mb-3">
                        <h5>场景 ${scene.id}</h5>
                        <p>${scene.content}</p>
                        ${scene.marker ? `<p><strong>标记:</strong> ${scene.marker}</p>` : ''}
                    </div>
                `;
            });
            
            previewContent += `<h4>结局</h4>`;
            
            scenario.endings.forEach(ending => {
                previewContent += `
                    <div class="mb-3">
                        <h5>结局 ${ending.id}</h5>
                        <p>${ending.content}</p>
                        ${ending.marker ? `<p><strong>标记:</strong> ${ending.marker}</p>` : ''}
                    </div>
                `;
            });
            
            // 创建预览模态框
            const modal = document.createElement('div');
            modal.className = 'modal fade';
            modal.id = 'previewModal';
            modal.tabIndex = -1;
            modal.innerHTML = `
                <div class="modal-dialog modal-lg">
                    <div class="modal-content">
                        <div class="modal-header">
                            <h5 class="modal-title">剧本预览</h5>
                            <button type="button" class="btn-close" data-bs-dismiss="modal" aria-label="Close"></button>
                        </div>
                        <div class="modal-body">
                            ${previewContent}
                        </div>
                        <div class="modal-footer">
                            <button type="button" class="btn btn-secondary" data-bs-dismiss="modal">关闭</button>
                        </div>
                    </div>
                </div>
            `;
            
            document.body.appendChild(modal);
            const previewModal = new bootstrap.Modal(modal);
            previewModal.show();
            
            // 清理模态框
            modal.addEventListener('hidden.bs.modal', () => {
                modal.remove();
            });
        }
    }

    // 关闭模态框
    closeModal() {
        const modal = bootstrap.Modal.getInstance(document.getElementById('scenarioModal'));
        if (modal) {
            modal.hide();
        }
    }

    // 显示消息
    showMessage(message, isError = false) {
        // 创建通知元素
        const notification = document.createElement('div');
        notification.className = `notification ${isError ? 'notification-error' : 'notification-success'}`;
        notification.textContent = message;
        
        // 获取通知容器
        const container = document.querySelector('.notification-container');
        container.appendChild(notification);
        
        // 3秒后自动移除通知
        setTimeout(() => {
            notification.remove();
        }, 3000);
    }

    // 绑定事件处理函数
    setEventHandlers(handlers) {
        this.onCreateScenarioClick = handlers.onCreateScenarioClick;
        this.onSaveScenario = handlers.onSaveScenario;
        this.onPreviewScenario = handlers.onPreviewScenario;
        this.onEditScenario = handlers.onEditScenario;
        this.onDeleteScenario = handlers.onDeleteScenario;
        this.onImportScenario = handlers.onImportScenario;
    }
}

// 导出模块
export default ScenarioView;