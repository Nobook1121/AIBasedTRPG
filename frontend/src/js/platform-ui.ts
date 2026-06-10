// @ts-nocheck
// AI平台管理界面模块

async function initAIPlatforms() {
    try {
        const platforms = await aiPlatformManager.loadPlatforms();
        renderPlatforms(platforms);
        bindRoleConfigSettings();
        await loadRoleConfigs();
        bindAddModelEvents();
        bindAPITestEvents();
        console.log('AI平台管理初始化完成');
    } catch (error) {
        console.error('初始化AI平台管理时出错:', error);
    }
}

function renderPlatforms(platforms) {
    const container = document.getElementById('ai-platforms-container');
    if (!container) return;

    container.innerHTML = '';
    platforms.forEach(platform => {
        const card = createPlatformCard(platform);
        container.appendChild(card);
    });
}

function bindRoleConfigSettings() {
    const list = document.getElementById('roleConfigList');
    if (!list || list.dataset.bound === 'true') return;

    list.dataset.bound = 'true';
    list.addEventListener('click', async function(event) {
        const button = event.target.closest('.save-role-config');
        if (!button) return;
        await saveRoleConfig(button.getAttribute('data-role-id'));
    });
}

async function loadRoleConfigs() {
    const list = document.getElementById('roleConfigList');
    if (!list) return;

    try {
        const response = await TrpgApi.get('/api/config/roles');
        if (!response.success) {
            setRoleConfigMessage(response.error || response.message || '加载角色配置失败', true);
            return;
        }
        renderRoleConfigCards(response.data?.roles || [], response.data?.enabled_providers || []);
        setRoleConfigMessage('');
    } catch (error) {
        console.error('加载角色配置失败:', error);
        setRoleConfigMessage('加载角色配置失败，请确认当前账号具有管理员权限', true);
    }
}

function renderRoleConfigCards(roles, providers) {
    const list = document.getElementById('roleConfigList');
    if (!list) return;

    if (!roles.length) {
        list.innerHTML = '<div class="role-config-card">暂无角色配置</div>';
        return;
    }

    list.innerHTML = roles.map(role => {
        const providerOptions = providers.map(provider => {
            const selected = provider.id === role.provider ? 'selected' : '';
            return `<option value="${escapeHtml(provider.id)}" ${selected}>${escapeHtml(provider.name)}</option>`;
        }).join('');
        const wakeWords = (role.wake_words || []).join(', ');
        return `
            <article class="role-config-card" data-role-id="${escapeHtml(role.id)}">
                <div class="role-config-card-header">
                    <div>
                        <h5 class="role-config-card-title">${escapeHtml(role.name)}</h5>
                        <div class="role-config-wake">${escapeHtml(wakeWords || '@' + role.name)}</div>
                    </div>
                    <button type="button" class="btn btn-primary save-role-config" data-role-id="${escapeHtml(role.id)}">
                        <i class="fa fa-floppy-o" aria-hidden="true"></i> 保存
                    </button>
                </div>
                <label class="form-label" for="roleWakeWords-${escapeHtml(role.id)}">唤醒词</label>
                <input class="form-control role-wake-input" id="roleWakeWords-${escapeHtml(role.id)}" value="${escapeHtml(wakeWords)}" placeholder="@KP, @Keeper">
                <label class="form-label" for="roleProvider-${escapeHtml(role.id)}">大模型提供商</label>
                <select class="form-control role-provider-select" id="roleProvider-${escapeHtml(role.id)}">
                    ${providerOptions}
                </select>
                <label class="form-label" for="rolePrompt-${escapeHtml(role.id)}">角色提示词</label>
                <textarea class="form-control role-config-prompt" id="rolePrompt-${escapeHtml(role.id)}" rows="8">${escapeHtml(role.prompt || '')}</textarea>
            </article>
        `;
    }).join('');
}

async function saveRoleConfig(roleId) {
    const card = document.querySelector(`.role-config-card[data-role-id="${CSS.escape(roleId)}"]`);
    if (!card) return;

    const wakeWords = card.querySelector('.role-wake-input').value
        .split(',')
        .map(item => item.trim())
        .filter(Boolean);
    const provider = card.querySelector('.role-provider-select').value;
    const prompt = card.querySelector('.role-config-prompt').value;

    try {
        const response = await TrpgApi.post(`/api/config/roles/${encodeURIComponent(roleId)}`, {
            name: card.querySelector('.role-config-card-title')?.textContent || roleId,
            wake_words: wakeWords,
            provider,
            prompt
        });
        if (!response.success) {
            setRoleConfigMessage(response.error || response.message || '保存角色配置失败', true);
            return;
        }
        setRoleConfigMessage('角色配置已保存');
        window.loadAIRoles?.();
        await loadRoleConfigs();
    } catch (error) {
        console.error('保存角色配置失败:', error);
        setRoleConfigMessage('保存角色配置失败，请稍后重试', true);
    }
}

function setRoleConfigMessage(message, isError = false) {
    const messageElement = document.getElementById('roleConfigMessage');
    if (!messageElement) return;

    messageElement.textContent = message;
    messageElement.classList.toggle('error', Boolean(isError));
    messageElement.classList.toggle('success', Boolean(message && !isError));
}

function escapeHtml(value) {
    return String(value ?? '')
        .replace(/&/g, '&amp;')
        .replace(/</g, '&lt;')
        .replace(/>/g, '&gt;')
        .replace(/"/g, '&quot;')
        .replace(/'/g, '&#39;');
}

function createPlatformCard(platform) {
    const card = document.createElement('div');
    card.className = 'ai-platform-card';

    card.innerHTML = `
        <div class="platform-header platform-card-header" data-platform="${platform.platform}">
            <div class="platform-info">
                <img src="${platform.icon}" alt="${platform.name}" class="platform-icon">
                <div class="platform-details">
                    <h5>${platform.name}</h5>
                    <p>${platform.description}</p>
                </div>
            </div>
            <div class="platform-toggle">
                <label for="toggle-${platform.platform}">${platform.enabled ? '已启用' : '已禁用'}</label>
                <div class="form-check form-switch">
                    <input class="form-check-input platform-toggle-input" type="checkbox" id="toggle-${platform.platform}" ${platform.enabled ? 'checked' : ''} data-platform="${platform.platform}">
                </div>
            </div>
            <div class="platform-action">
                <button class="btn btn-sm btn-primary config-btn" data-platform="${platform.platform}">配置</button>
            </div>
        </div>
    `;

    const cardHeader = card.querySelector('.platform-card-header');
    if (cardHeader) {
        cardHeader.addEventListener('click', function(e) {
            if (e.target.closest('.platform-toggle')) return;

            const platformName = this.getAttribute('data-platform');
            openPlatformConfigModal(platformName);
        });
    }

    const configBtn = card.querySelector('.config-btn');
    if (configBtn) {
        configBtn.addEventListener('click', function(e) {
            e.stopPropagation();
            const platformName = this.getAttribute('data-platform');
            openPlatformConfigModal(platformName);
        });
    }

    const toggleInput = card.querySelector('.platform-toggle-input');
    if (toggleInput) {
        toggleInput.addEventListener('change', async function() {
            const platformName = this.getAttribute('data-platform');
            const enabled = this.checked;

            const success = await aiPlatformManager.setPlatformEnabled(platformName, enabled);
            if (success) {
                const toggleLabel = this.parentElement.previousElementSibling;
                toggleLabel.textContent = enabled ? '已启用' : '已禁用';
            }
        });
    }

    return card;
}

async function openPlatformConfigModal(platformName) {
    try {
        console.log('开始打开平台配置模态窗口:', platformName);
        const platform = await aiPlatformManager.getPlatform(platformName);
        console.log('平台配置加载成功:', platform);
        if (!platform) {
            alert('平台配置加载失败');
            return;
        }

        const modalElement = document.getElementById('platformConfigModal');
        console.log('模态框元素:', modalElement);
        if (!modalElement) {
            console.error('模态框元素不存在');
            return;
        }

        document.getElementById('platformConfigModalLabel').textContent = `${platform.name} 配置`;

        let configContent = buildPlatformConfigHTML(platform);
        document.getElementById('platformConfigContent').innerHTML = configContent;

        bindPasswordToggles();
        bindTimeoutSlider(platform.platform);

        if (platform.platform !== 'lmstudio') {
            bindModelEvents(platform);
        } else {
            bindLMStudioEvents(platform);
        }

        document.getElementById('savePlatformConfigBtn').onclick = async function() {
            try {
                const apiKey = document.getElementById(`modal-api-key-${platform.platform}`).value;
                let baseUrl = document.getElementById(`modal-base-url-${platform.platform}`).value;
                const timeout = parseInt(document.getElementById(`modal-timeout-${platform.platform}`).value);

                if (!baseUrl.endsWith('/v1/chat/completions')) {
                    baseUrl += '/v1/chat/completions';
                }

                platform.config.api_key = apiKey;
                platform.config.base_url = baseUrl;
                platform.config.timeout = timeout;

                await aiPlatformManager.savePlatformConfig(platform.platform, platform);

                const modal = bootstrap.Modal.getInstance(document.getElementById('platformConfigModal'));
                modal.hide();

                alert('配置保存成功');
            } catch (error) {
                console.error('保存配置失败:', error);
                alert('配置保存失败');
            }
        };

        if (platform.platform !== 'lmstudio') {
            bindAddModelFormEvents(platform);
        }

        const modal = new bootstrap.Modal(modalElement, { backdrop: false });
        modal.show();
    } catch (error) {
        console.error('打开平台配置模态窗口失败:', error);
    }
}

function buildPlatformConfigHTML(platform) {
    let html = `
        <div class="api-config">
            <h6>API配置</h6>
            <div class="form-group">
                <label for="modal-api-key-${platform.platform}">API Key</label>
                <div class="password-input-group">
                    <input type="password" class="form-control api-key-input" id="modal-api-key-${platform.platform}" value="${platform.config.api_key || ''}" data-platform="${platform.platform}">
                    <span class="password-toggle" data-target="modal-api-key-${platform.platform}"><i class="bi bi-eye"></i></span>
                </div>
            </div>
            <div class="form-group mt-2">
                <label for="modal-base-url-${platform.platform}">Base URL</label>
                <input type="text" class="form-control base-url-input" id="modal-base-url-${platform.platform}" value="${platform.config.base_url}" data-platform="${platform.platform}">
            </div>
            <div class="form-group mt-2">
                <label for="modal-timeout-${platform.platform}">超时设置 (${platform.config.timeout}秒)</label>
                <input type="range" class="form-range timeout-slider" id="modal-timeout-${platform.platform}" min="10" max="60" step="5" value="${platform.config.timeout}" data-platform="${platform.platform}">
                <div class="timeout-value" id="modal-timeout-value-${platform.platform}">${platform.config.timeout}秒</div>
            </div>
        </div>
    `;

    if (platform.platform !== 'lmstudio') {
        html += `
            <div class="models-section">
                <h6>
                    模型管理
                    <button class="btn btn-sm btn-primary add-model-btn" data-platform="${platform.platform}">+ 添加模型</button>
                </h6>
                <div class="models-list" id="modal-models-list-${platform.platform}">
                    ${platform.models.map(model => `
                        <div class="model-item">
                            <div class="model-info">
                                <h7>${model.name}</h7>
                                <p>${model.description}</p>
                            </div>
                            <div class="model-actions">
                                <div class="form-check form-switch">
                                    <input class="form-check-input model-toggle-input" type="checkbox" id="modal-model-toggle-${platform.platform}-${model.id}" ${model.enabled ? 'checked' : ''} data-platform="${platform.platform}" data-model="${model.id}">
                                </div>
                                <button class="btn btn-sm btn-primary test-model-btn" data-platform="${platform.platform}" data-model="${model.id}">测试连接</button>
                                <button class="btn btn-sm btn-primary config-model-btn" data-platform="${platform.platform}" data-model="${model.id}">配置</button>
                                <button class="btn btn-sm btn-danger remove-model-btn" data-platform="${platform.platform}" data-model="${model.id}">删除</button>
                            </div>
                        </div>
                    `).join('')}
                </div>
            </div>
        `;
    } else {
        html += `
            <div class="models-section">
                <h6>
                    模型说明
                    <button class="btn btn-sm btn-primary test-platform-btn" data-platform="${platform.platform}">测试连接</button>
                </h6>
                <div class="alert alert-info">
                    <p>LMStudio平台使用本地运行的模型，无需选择模型。</p>
                    <p>请确保LMStudio服务器正在运行，默认端口为1234。</p>
                    <p>API Key可以设置为任意值，LMStudio会忽略它。</p>
                </div>
            </div>
        `;
    }

    return html;
}

function bindPasswordToggles() {
    document.querySelectorAll('.password-toggle').forEach(toggle => {
        toggle.addEventListener('click', function() {
            const targetId = this.getAttribute('data-target');
            const input = document.getElementById(targetId);
            if (input) {
                input.type = input.type === 'password' ? 'text' : 'password';
                const icon = this.querySelector('i');
                if (icon) {
                    icon.className = input.type === 'password' ? 'bi bi-eye' : 'bi bi-eye-slash';
                }
            }
        });
    });
}

function bindTimeoutSlider(platformName) {
    const timeoutSlider = document.getElementById(`modal-timeout-${platformName}`);
    if (timeoutSlider) {
        timeoutSlider.addEventListener('input', function() {
            const value = this.value;
            const name = this.getAttribute('data-platform');
            const valueDisplay = document.getElementById(`modal-timeout-value-${name}`);
            if (valueDisplay) {
                valueDisplay.textContent = `${value}秒`;
            }
        });
    }
}

function bindModelEvents(platform) {
    document.querySelectorAll('.model-toggle-input').forEach(toggle => {
        toggle.addEventListener('change', function() {
            const platformName = this.getAttribute('data-platform');
            const modelId = this.getAttribute('data-model');
            const enabled = this.checked;
            console.log(`模型 ${modelId} 已${enabled ? '启用' : '禁用'}`);
        });
    });

    document.querySelectorAll('.remove-model-btn').forEach(btn => {
        btn.addEventListener('click', async function() {
            const platformName = this.getAttribute('data-platform');
            const modelId = this.getAttribute('data-model');

            if (confirm('确定要删除这个模型吗？')) {
                const success = await aiPlatformManager.removeModel(platformName, modelId);
                if (success) {
                    openPlatformConfigModal(platformName);
                }
            }
        });
    });

    document.querySelectorAll('.test-model-btn').forEach(btn => {
        btn.addEventListener('click', function() {
            const platformName = this.getAttribute('data-platform');
            const modelId = this.getAttribute('data-model');
            testModelAPI(platformName, modelId);
        });
    });

    document.querySelectorAll('.config-model-btn').forEach(btn => {
        btn.addEventListener('click', function(event) {
            event.stopPropagation();
            const platformName = this.getAttribute('data-platform');
            const modelId = this.getAttribute('data-model');
            configModel(platformName, modelId);
        });
    });
}

function bindLMStudioEvents(platform) {
    document.querySelectorAll('.test-platform-btn').forEach(btn => {
        btn.addEventListener('click', function() {
            const platformName = this.getAttribute('data-platform');

            const testModal = new bootstrap.Modal(document.getElementById('apiTestModal'), { backdrop: false });
            testModal.show();

            resetTestModal();
            testAPI(platformName);
        });
    });
}

function bindAddModelFormEvents(platform) {
    document.querySelectorAll('.add-model-btn').forEach(btn => {
        btn.addEventListener('click', function() {
            const platformName = this.getAttribute('data-platform');

            window.currentPlatform = platformName;

            document.getElementById('modelName').value = '';
            document.getElementById('modelId').value = '';
            document.getElementById('modelDescription').value = '';
            const addModelMessage = document.getElementById('addModelMessage');
            if (addModelMessage) {
                addModelMessage.textContent = '';
                addModelMessage.className = 'add-model-message';
            }
            document.getElementById('addModelBtn').disabled = true;

            const addModelModal = new bootstrap.Modal(document.getElementById('addModelModal'), { backdrop: false });
            addModelModal.show();
        });
    });
}

function bindAddModelEvents() {
    document.addEventListener('click', function(e) {
        if (!e.target.classList.contains('add-model-btn')) return;

        const platform = e.target.getAttribute('data-platform');
        window.currentPlatform = platform;

        document.getElementById('modelName').value = '';
        document.getElementById('modelId').value = '';
        document.getElementById('modelDescription').value = '';
        document.getElementById('addModelBtn').disabled = true;

        const modal = new bootstrap.Modal(document.getElementById('addModelModal'));
        modal.show();
    });

    const modelNameInput = document.getElementById('modelName');
    const modelIdInput = document.getElementById('modelId');
    const addModelBtn = document.getElementById('addModelBtn');

    function validateForm() {
        const nameValid = modelNameInput.value.trim() !== '';
        const idValid = modelIdInput.value.trim() !== '';
        addModelBtn.disabled = !nameValid || !idValid;
    }

    if (modelNameInput) modelNameInput.addEventListener('input', validateForm);
    if (modelIdInput) modelIdInput.addEventListener('input', validateForm);

    if (addModelBtn) {
        addModelBtn.addEventListener('click', async function() {
            const platform = window.currentPlatform;
            if (!platform) return;

            const model = {
                name: document.getElementById('modelName').value.trim(),
                id: document.getElementById('modelId').value.trim(),
                description: document.getElementById('modelDescription').value.trim()
            };

            const success = await aiPlatformManager.addModel(platform, model);
            if (success) {
                const modal = bootstrap.Modal.getInstance(document.getElementById('addModelModal'));
                modal.hide();

                const platforms = await aiPlatformManager.loadPlatforms();
                renderPlatforms(platforms);

                showNotification('模型添加成功', 'success');
            } else {
                showNotification('模型添加失败', 'error');
            }
        });
    }
}

function bindAPITestEvents() {
    document.addEventListener('click', function(e) {
        if (!e.target.classList.contains('test-api-btn')) return;

        const platform = e.target.getAttribute('data-platform');

        const modal = new bootstrap.Modal(document.getElementById('apiTestModal'));
        modal.show();

        resetTestModal();
        testAPI(platform);
    });

    const reTestBtn = document.getElementById('reTestBtn');
    if (reTestBtn) {
        reTestBtn.addEventListener('click', function() {
            const platform = window.currentTestingPlatform;
            if (platform) {
                resetTestModal();
                testAPI(platform);
            }
        });
    }
}

function resetTestModal() {
    document.getElementById('testLoading').classList.remove('d-none');
    document.getElementById('testStatus').classList.add('d-none');
    document.getElementById('testResult').classList.add('d-none');
    document.getElementById('testError').classList.add('d-none');
    document.getElementById('testDetails').classList.add('d-none');
    document.getElementById('reTestBtn').style.display = 'none';

    const testDetails = document.getElementById('testDetails');
    if (testDetails) testDetails.innerHTML = '';
}

async function testAPI(platform) {
    window.currentTestingPlatform = platform;

    try {
        resetTestModal();

        const platformConfig = aiPlatformManager.getPlatform(platform);
        if (!platformConfig) throw new Error('平台配置不存在');

        let modelId;
        if (platform === 'lmstudio') {
            modelId = 'local-model';
        } else {
            if (!platformConfig.models.length) throw new Error('平台无可用模型');
            const model = platformConfig.models.find(m => m.enabled) || platformConfig.models[0];
            modelId = model.id;
        }

        const result = await aiPlatformManager.testAPI(platform, modelId);

        document.getElementById('testLoading').classList.add('d-none');

        if (result.success) {
            document.getElementById('testResult').classList.remove('d-none');
            document.getElementById('testDetails').classList.remove('d-none');
            fillTestDetails(result);
        } else {
            document.getElementById('testError').classList.remove('d-none');
            const errorMessage = document.getElementById('errorMessage');
            if (errorMessage) errorMessage.textContent = result.error;
        }

        const reTestBtn = document.getElementById('reTestBtn');
        if (reTestBtn) reTestBtn.style.display = 'inline-block';
    } catch (error) {
        document.getElementById('testLoading').classList.add('d-none');
        document.getElementById('testError').classList.remove('d-none');
        document.getElementById('errorMessage').textContent = error.message;
        document.getElementById('reTestBtn').style.display = 'inline-block';
    }
}

async function testModelAPI(platform, modelId) {
    try {
        resetTestModal();

        const testModal = new bootstrap.Modal(document.getElementById('apiTestModal'), { backdrop: false });
        testModal.show();

        const platformConfig = aiPlatformManager.getPlatform(platform);
        if (!platformConfig) throw new Error('平台配置不存在');

        const model = platformConfig.models.find(m => m.id === modelId);
        if (!model) throw new Error('模型不存在');

        const result = await aiPlatformManager.testAPI(platform, modelId);

        document.getElementById('testLoading').classList.add('d-none');

        if (result.success) {
            document.getElementById('testResult').classList.remove('d-none');
            document.getElementById('testDetails').classList.remove('d-none');
            fillTestDetails(result);
        } else {
            document.getElementById('testError').classList.remove('d-none');
            const errorMessage = document.getElementById('errorMessage');
            if (errorMessage) errorMessage.textContent = result.error;
        }

        const reTestBtn = document.getElementById('reTestBtn');
        if (reTestBtn) reTestBtn.style.display = 'inline-block';
    } catch (error) {
        console.error('测试模型API连接失败:', error);
        document.getElementById('testLoading').classList.add('d-none');
        document.getElementById('testError').classList.remove('d-none');
        document.getElementById('errorMessage').textContent = error.message;
        document.getElementById('reTestBtn').style.display = 'inline-block';
    }
}

function fillTestDetails(result) {
    const testDetails = document.getElementById('testDetails');
    if (testDetails) {
        testDetails.innerHTML = `
            <h6>测试详情</h6>
            <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 10px; margin-bottom: 10px;">
                <p><strong>测试时间：</strong><span id="testTime">${result.time}</span></p>
                <p><strong>测试类型：</strong>文本对话测试</p>
                <p><strong>模型类型：</strong><span id="testModel">${result.model}</span></p>
                <p><strong>平均速度：</strong><span id="testSpeed">${result.speed}</span></p>
            </div>
            <p><strong>测试消耗：</strong><span id="testConsumption">${result.consumption}</span></p>
        `;
    }
}

async function configModel(platform, modelId) {
    try {
        const platformConfig = aiPlatformManager.getPlatform(platform);
        if (!platformConfig) throw new Error('平台配置不存在');

        const model = platformConfig.models.find(m => m.id === modelId);
        if (!model) throw new Error('模型不存在');

        let modelRequestConfig = '';
        try {
            const response = await fetch(`config/aimodel/${platform}/${modelId}.json`);
            if (response.ok) {
                modelRequestConfig = JSON.stringify(await response.json(), null, 2);
            } else {
                const defaultResponse = await fetch('config/aiplatform/default-request.json');
                if (defaultResponse.ok) {
                    const defaultConfig = await defaultResponse.json();
                    defaultConfig.model = modelId;
                    modelRequestConfig = JSON.stringify(defaultConfig, null, 2);
                }
            }
        } catch (error) {
            console.error('加载模型请求配置失败:', error);
            const defaultResponse = await fetch('config/aiplatform/default-request.json');
            if (defaultResponse.ok) {
                const defaultConfig = await defaultResponse.json();
                defaultConfig.model = modelId;
                modelRequestConfig = JSON.stringify(defaultConfig, null, 2);
            }
        }

        const modalElement = document.createElement('div');
        modalElement.className = 'modal fade';
        modalElement.id = 'modelConfigModal';
        modalElement.tabIndex = -1;
        modalElement.setAttribute('aria-labelledby', 'modelConfigModalLabel');
        modalElement.setAttribute('aria-hidden', 'true');

        modalElement.innerHTML = `
            <div class="modal-dialog modal-lg">
                <div class="modal-content">
                    <div class="modal-header">
                        <h5 class="modal-title" id="modelConfigModalLabel">${model.name} 配置</h5>
                        <button type="button" class="btn-close" data-bs-dismiss="modal" aria-label="Close"></button>
                    </div>
                    <div class="modal-body">
                        <div class="form-group">
                            <label for="modelRequestConfig">JSON配置</label>
                            <textarea class="form-control" id="modelRequestConfig" rows="20">${modelRequestConfig}</textarea>
                        </div>
                    </div>
                    <div class="modal-footer">
                        <button type="button" class="btn btn-secondary" data-bs-dismiss="modal">关闭</button>
                        <button type="button" class="btn btn-primary" id="saveModelConfigBtn">保存</button>
                    </div>
                </div>
            </div>
        `;

        document.body.appendChild(modalElement);

        const modal = new bootstrap.Modal(modalElement);
        modal.show();

        document.getElementById('saveModelConfigBtn').addEventListener('click', async function() {
            try {
                const requestConfig = JSON.parse(document.getElementById('modelRequestConfig').value);

                const { response: saveResponse } = await TrpgApi.requestWithResponse('/api/config/aimodel/save', {
                    method: 'POST',
                    body: {
                        platform: platform,
                        modelId: modelId,
                        content: requestConfig
                    }
                });

                if (saveResponse.ok) {
                    alert('JSON配置保存成功');
                    modal.hide();
                } else {
                    throw new Error('保存JSON配置失败');
                }
            } catch (error) {
                console.error('保存JSON配置失败:', error);
                alert('保存JSON配置失败: ' + error.message);
            }
        });

        modalElement.addEventListener('hidden.bs.modal', function() {
            setTimeout(() => modalElement.remove(), 100);
        });
    } catch (error) {
        console.error('配置模型失败:', error);
        alert('配置模型失败: ' + error.message);
    }
}

function showNotification(message, type) {
    type = type || 'info';
    const container = document.querySelector('.notification-container');
    if (!container) return;

    const notification = document.createElement('div');
    notification.className = `notification notification-${type}`;
    notification.textContent = message;

    container.appendChild(notification);

    setTimeout(() => notification.remove(), 3000);
}
