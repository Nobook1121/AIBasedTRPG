// 主脚本文件
import ScenarioController from './controllers/ScenarioController.js';
import ToolManager from '../tools/toolManager.js';
import configManager from '../config/ConfigManager.js';
import aiPlatformManager from '../config/AIPlatformManager.js';

// 全局工具管理器
let toolManager;

// DOM 加载完成后执行
document.addEventListener('DOMContentLoaded', async function() {
    // 初始化工具管理器
    toolManager = new ToolManager();
    
    // 初始化选项卡切换
    initTabs();
    
    // 初始化聊天功能
    initChat();
    
    // 初始化剧本管理
    initScenarioManagement();
    
    // 初始化角色卡管理
    initCharacterManagement();
    
    // 初始化骰子工具
    initDiceTool();
    
    // 初始化工具标签页
    initToolTabs();
    
    // 初始化设置标签页
    initSettingsTabs();
    
    // 加载并应用配置文件
    await loadAndApplyConfigs();
    
    // 初始化AI平台管理
    initAIPlatforms();
    
    // 初始化用户认证功能
    initAuth();
    
    // 添加全局事件监听器，确保遮罩层在所有模态框关闭后被正确移除
    document.addEventListener('hidden.bs.modal', function(event) {
        // 检查关闭的模态框是否有背景遮罩
        const modalElement = event.target;
        const modalInstance = bootstrap.Modal.getInstance(modalElement);
        
        // 只有当关闭的是没有背景遮罩的模态框时，才不移除遮罩层
        // 这样可以确保主配置模态框的遮罩层不会被错误移除
        setTimeout(() => {
            // 检查是否还有其他模态框是打开的
            const openModals = document.querySelectorAll('.modal.show');
            if (openModals.length === 0) {
                // 如果没有其他模态框打开，移除所有遮罩层
                const modalBackdrops = document.querySelectorAll('.modal-backdrop');
                modalBackdrops.forEach(backdrop => {
                    backdrop.remove();
                });
                console.log('所有模态框已关闭，已移除所有遮罩层');
            } else {
                console.log('还有其他模态框打开，保留遮罩层');
            }
        }, 100);
    });
});

// 加载并应用配置文件
async function loadAndApplyConfigs() {
    try {
        // 加载常规设置配置
        await configManager.loadConfig('general');
        
        // 应用常规设置到UI
        configManager.applyGeneralSettings();
        
        console.log('配置文件加载和应用完成');
    } catch (error) {
        console.error('加载配置文件时出错:', error);
    }
}

// 初始化AI平台管理
async function initAIPlatforms() {
    try {
        // 加载所有平台配置
        const platforms = await aiPlatformManager.loadPlatforms();
        
        // 渲染平台配置卡片
        renderPlatforms(platforms);
        
        // 绑定添加模型按钮事件
        bindAddModelEvents();
        
        // 绑定API测试按钮事件
        bindAPITestEvents();
        
        console.log('AI平台管理初始化完成');
    } catch (error) {
        console.error('初始化AI平台管理时出错:', error);
    }
}

// 渲染平台配置卡片
function renderPlatforms(platforms) {
    const container = document.getElementById('ai-platforms-container');
    if (!container) return;
    
    container.innerHTML = '';
    
    platforms.forEach(platform => {
        const card = createPlatformCard(platform);
        container.appendChild(card);
    });
}

// 创建平台配置卡片
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
    
    // 绑定平台卡片点击事件，打开配置模态窗口
    const cardHeader = card.querySelector('.platform-card-header');
    if (cardHeader) {
        cardHeader.addEventListener('click', function(e) {
            // 防止点击开关时触发配置窗口
            if (e.target.closest('.platform-toggle')) {
                return;
            }
            
            const platformName = this.getAttribute('data-platform');
            openPlatformConfigModal(platformName);
        });
    }
    
    // 绑定配置按钮点击事件
    const configBtn = card.querySelector('.config-btn');
    if (configBtn) {
        configBtn.addEventListener('click', function(e) {
            e.stopPropagation(); // 防止触发卡片点击事件
            const platformName = this.getAttribute('data-platform');
            openPlatformConfigModal(platformName);
        });
    }
    
    // 绑定平台启用/禁用切换事件
    const toggleInput = card.querySelector('.platform-toggle-input');
    if (toggleInput) {
        toggleInput.addEventListener('change', async function() {
            const platformName = this.getAttribute('data-platform');
            const enabled = this.checked;
            
            const success = await aiPlatformManager.setPlatformEnabled(platformName, enabled);
            if (success) {
                // 更新UI
                const toggleLabel = this.parentElement.previousElementSibling;
                toggleLabel.textContent = enabled ? '已启用' : '已禁用';
            }
        });
    }
    
    return card;
}

// 打开平台配置模态窗口
async function openPlatformConfigModal(platformName) {
    try {
        console.log('开始打开平台配置模态窗口:', platformName);
        // 加载平台配置
        const platform = await aiPlatformManager.getPlatform(platformName);
        console.log('平台配置加载成功:', platform);
        if (!platform) {
            alert('平台配置加载失败');
            return;
        }
        
        // 检查模态框元素是否存在
        const modalElement = document.getElementById('platformConfigModal');
        console.log('模态框元素:', modalElement);
        if (!modalElement) {
            console.error('模态框元素不存在');
            return;
        }
        
        // 更新模态窗口标题
        document.getElementById('platformConfigModalLabel').textContent = `${platform.name} 配置`;
        
        // 生成配置内容
        let configContent = `
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
        
        // 为非LMStudio平台添加模型管理部分
        if (platform.platform !== 'lmstudio') {
            configContent += `
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
            // 为LMStudio平台添加特殊说明和测试连接按钮
            configContent += `
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
        
        // 更新模态窗口内容
        document.getElementById('platformConfigContent').innerHTML = configContent;
        
        // 绑定密码显示/隐藏切换事件
        const passwordToggles = document.querySelectorAll('.password-toggle');
        passwordToggles.forEach(toggle => {
            toggle.addEventListener('click', function() {
                const targetId = this.getAttribute('data-target');
                const input = document.getElementById(targetId);
                if (input) {
                    input.type = input.type === 'password' ? 'text' : 'password';
                    const icon = this.querySelector('i');
                    if (icon) {
                        if (input.type === 'password') {
                            icon.className = 'bi bi-eye';
                        } else {
                            icon.className = 'bi bi-eye-slash';
                        }
                    }
                }
            });
        });
        
        // 绑定超时滑块事件
        const timeoutSlider = document.getElementById(`modal-timeout-${platform.platform}`);
        if (timeoutSlider) {
            timeoutSlider.addEventListener('input', function() {
                const value = this.value;
                const platformName = this.getAttribute('data-platform');
                const valueDisplay = document.getElementById(`modal-timeout-value-${platformName}`);
                if (valueDisplay) {
                    valueDisplay.textContent = `${value}秒`;
                }
            });
        }
        
        // 绑定模型相关事件（仅对非LMStudio平台）
        if (platform.platform !== 'lmstudio') {
            // 绑定模型启用/禁用切换事件
            const modelToggles = document.querySelectorAll('.model-toggle-input');
            modelToggles.forEach(toggle => {
                toggle.addEventListener('change', function() {
                    const platformName = this.getAttribute('data-platform');
                    const modelId = this.getAttribute('data-model');
                    const enabled = this.checked;
                    
                    // 这里可以添加模型启用/禁用的逻辑
                    console.log(`模型 ${modelId} 已${enabled ? '启用' : '禁用'}`);
                });
            });
            
            // 绑定删除模型按钮事件
            const removeModelBtns = document.querySelectorAll('.remove-model-btn');
            removeModelBtns.forEach(btn => {
                btn.addEventListener('click', async function() {
                    const platformName = this.getAttribute('data-platform');
                    const modelId = this.getAttribute('data-model');
                    
                    if (confirm('确定要删除这个模型吗？')) {
                        const success = await aiPlatformManager.removeModel(platformName, modelId);
                        if (success) {
                            // 重新打开模态窗口，刷新模型列表
                            openPlatformConfigModal(platformName);
                        }
                    }
                });
            });
            
            // 绑定添加模型按钮事件
            const addModelBtns = document.querySelectorAll('.add-model-btn');
            addModelBtns.forEach(btn => {
                btn.addEventListener('click', function() {
                    const platform = this.getAttribute('data-platform');
                    
                    // 存储当前平台
                    window.currentPlatform = platform;
                    
                    // 重置表单
                    document.getElementById('modelName').value = '';
                    document.getElementById('modelId').value = '';
                    document.getElementById('modelDescription').value = '';
                    const addModelMessage = document.getElementById('addModelMessage');
                    if (addModelMessage) {
                        addModelMessage.textContent = '';
                        addModelMessage.className = 'add-model-message';
                    }
                    document.getElementById('addModelBtn').disabled = true;
                    
                    // 打开添加模型模态窗口
                    const addModelModal = new bootstrap.Modal(document.getElementById('addModelModal'), { backdrop: false });
                    addModelModal.show();
                });
            });
            
            // 绑定模型测试连接按钮事件
            const testModelBtns = document.querySelectorAll('.test-model-btn');
            testModelBtns.forEach(btn => {
                btn.addEventListener('click', function() {
                    const platform = this.getAttribute('data-platform');
                    const modelId = this.getAttribute('data-model');
                    testModelAPI(platform, modelId);
                });
            });
            
            // 绑定模型配置按钮事件
            const configModelBtns = document.querySelectorAll('.config-model-btn');
            configModelBtns.forEach(btn => {
                btn.addEventListener('click', function(event) {
                    // 阻止事件冒泡，防止点击配置按钮时触发模态窗口背景点击事件
                    event.stopPropagation();
                    
                    const platform = this.getAttribute('data-platform');
                    const modelId = this.getAttribute('data-model');
                    configModel(platform, modelId);
                });
            });
        } else {
            // 绑定LMStudio平台的测试连接按钮事件
            const testPlatformBtns = document.querySelectorAll('.test-platform-btn');
            testPlatformBtns.forEach(btn => {
                btn.addEventListener('click', function() {
                    const platform = this.getAttribute('data-platform');
                    
                    // 显示测试模态窗口
                    const testModal = new bootstrap.Modal(document.getElementById('apiTestModal'), { backdrop: false });
                    testModal.show();
                    
                    // 显示加载状态
                    document.getElementById('testLoading').classList.remove('d-none');
                    document.getElementById('testResult').classList.add('d-none');
                    document.getElementById('testError').classList.add('d-none');
                    document.getElementById('testDetails').classList.add('d-none');
                    document.getElementById('reTestBtn').style.display = 'none';
                    
                    // 执行API测试
                    testAPI(platform);
                });
            });
        }
        
        // 绑定保存配置按钮事件
        document.getElementById('savePlatformConfigBtn').onclick = async function() {
            try {
                // 收集配置数据
                const apiKey = document.getElementById(`modal-api-key-${platform.platform}`).value;
                let baseUrl = document.getElementById(`modal-base-url-${platform.platform}`).value;
                const timeout = parseInt(document.getElementById(`modal-timeout-${platform.platform}`).value);
                
                // 确保baseURL以"/v1/chat/completions"结尾
                if (!baseUrl.endsWith('/v1/chat/completions')) {
                    baseUrl += '/v1/chat/completions';
                }
                
                // 更新平台配置
                platform.config.api_key = apiKey;
                platform.config.base_url = baseUrl;
                platform.config.timeout = timeout;
                
                // 保存配置
                await aiPlatformManager.savePlatformConfig(platform.platform, platform);
                
                // 关闭模态窗口
                const modal = bootstrap.Modal.getInstance(document.getElementById('platformConfigModal'));
                modal.hide();
                
                // 显示成功提示
                alert('配置保存成功');
            } catch (error) {
                console.error('保存配置失败:', error);
                alert('配置保存失败');
            }
        };
        
        // 显示模态窗口
        console.log('准备显示模态窗口');
        const modal = new bootstrap.Modal(modalElement);
        console.log('模态窗口实例创建成功:', modal);
        modal.show();
        console.log('模态窗口已显示');
        
        // 立即调整模态框和背景遮罩层的z-index
        setTimeout(() => {
            const modalBackdrops = document.querySelectorAll('.modal-backdrop');
            modalBackdrops.forEach(backdrop => {
                backdrop.style.zIndex = '1000';
            });
            modalElement.style.zIndex = '2000';
            console.log('已调整模态框和背景遮罩层的z-index');
        }, 0);
        
        // 添加模态框关闭事件监听器，确保遮罩层被正确移除
        modalElement.addEventListener('hidden.bs.modal', function() {
            setTimeout(() => {
                const modalBackdrops = document.querySelectorAll('.modal-backdrop');
                modalBackdrops.forEach(backdrop => {
                    backdrop.remove();
                });
                console.log('模态框关闭，已移除所有遮罩层');
            }, 100);
        });
    } catch (error) {
        console.error('打开平台配置模态窗口失败:', error);
        alert('打开配置窗口失败');
    }
}

// 绑定添加模型按钮事件
function bindAddModelEvents() {
    document.addEventListener('click', function(e) {
        if (e.target.classList.contains('add-model-btn')) {
            const platform = e.target.getAttribute('data-platform');
            
            // 存储当前平台
            window.currentPlatform = platform;
            
            // 重置表单
            document.getElementById('modelName').value = '';
            document.getElementById('modelId').value = '';
            document.getElementById('modelDescription').value = '';
            
            // 启用/禁用确认按钮
            document.getElementById('addModelBtn').disabled = true;
            
            // 显示模态窗口
            const modal = new bootstrap.Modal(document.getElementById('addModelModal'));
            modal.show();
        }
    });
    
    // 绑定表单验证事件
    const modelNameInput = document.getElementById('modelName');
    const modelIdInput = document.getElementById('modelId');
    const addModelBtn = document.getElementById('addModelBtn');
    
    function validateForm() {
        const nameValid = modelNameInput.value.trim() !== '';
        const idValid = modelIdInput.value.trim() !== '';
        addModelBtn.disabled = !nameValid || !idValid;
    }
    
    if (modelNameInput) {
        modelNameInput.addEventListener('input', validateForm);
    }
    
    if (modelIdInput) {
        modelIdInput.addEventListener('input', validateForm);
    }
    
    // 绑定添加模型按钮点击事件
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
                // 关闭模态窗口
                const modal = bootstrap.Modal.getInstance(document.getElementById('addModelModal'));
                modal.hide();
                
                // 重新渲染平台卡片
                const platforms = await aiPlatformManager.loadPlatforms();
                renderPlatforms(platforms);
                
                // 显示成功提示
                showNotification('模型添加成功', 'success');
            } else {
                showNotification('模型添加失败', 'error');
            }
        });
    }
}

// 绑定API测试按钮事件
function bindAPITestEvents() {
    document.addEventListener('click', function(e) {
        if (e.target.classList.contains('test-api-btn')) {
            const platform = e.target.getAttribute('data-platform');
            
            // 显示测试模态窗口
            const modal = new bootstrap.Modal(document.getElementById('apiTestModal'));
            modal.show();
            
            // 显示加载状态
            document.getElementById('testLoading').classList.remove('d-none');
            document.getElementById('testStatus').classList.add('d-none');
            document.getElementById('testResult').classList.add('d-none');
            document.getElementById('testError').classList.add('d-none');
            document.getElementById('testDetails').classList.add('d-none');
            document.getElementById('reTestBtn').style.display = 'none';
            
            // 执行API测试
            testAPI(platform);
        }
    });
    
    // 绑定重新测试按钮事件
    const reTestBtn = document.getElementById('reTestBtn');
    if (reTestBtn) {
        reTestBtn.addEventListener('click', function() {
            const platform = window.currentTestingPlatform;
            if (platform) {
                // 显示加载状态
                document.getElementById('testLoading').classList.remove('d-none');
                document.getElementById('testStatus').classList.add('d-none');
                document.getElementById('testResult').classList.add('d-none');
                document.getElementById('testError').classList.add('d-none');
                document.getElementById('testDetails').classList.add('d-none');
                document.getElementById('reTestBtn').style.display = 'none';
                
                // 清除测试详情内容
                const testDetails = document.getElementById('testDetails');
                if (testDetails) {
                    testDetails.innerHTML = '';
                }
                
                // 执行API测试
                testAPI(platform);
            }
        });
    }
}

// 执行API测试
async function testAPI(platform) {
    window.currentTestingPlatform = platform;
    
    try {
        // 清除上一次的测试结果
        document.getElementById('testLoading').classList.remove('d-none');
        document.getElementById('testResult').classList.add('d-none');
        document.getElementById('testError').classList.add('d-none');
        document.getElementById('reTestBtn').style.display = 'none';
        
        // 清除测试详情内容
        const testDetails = document.getElementById('testDetails');
        if (testDetails) {
            testDetails.innerHTML = '';
        }
        
        // 获取平台配置
        const platformConfig = aiPlatformManager.getPlatform(platform);
        if (!platformConfig) {
            throw new Error('平台配置不存在');
        }
        
        // 对于LMStudio平台，使用默认模型ID
        let modelId;
        if (platform === 'lmstudio') {
            modelId = 'local-model';
        } else {
            // 对于其他平台，使用第一个启用的模型
            if (!platformConfig.models.length) {
                throw new Error('平台无可用模型');
            }
            const model = platformConfig.models.find(m => m.enabled) || platformConfig.models[0];
            modelId = model.id;
        }
        
        // 执行测试
        const result = await aiPlatformManager.testAPI(platform, modelId);
        
        // 隐藏加载状态
        document.getElementById('testLoading').classList.add('d-none');
        
        if (result.success) {
            // 显示成功结果
            document.getElementById('testResult').classList.remove('d-none');
            document.getElementById('testDetails').classList.remove('d-none');
            
            // 填充测试详情
            const testDetails = document.getElementById('testDetails');
            if (testDetails) {
                // 确保测试详情元素有内容
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
        } else {
            // 显示错误结果
            document.getElementById('testError').classList.remove('d-none');
            const errorMessage = document.getElementById('errorMessage');
            if (errorMessage) {
                errorMessage.textContent = result.error;
            }
        }
        
        // 显示重新测试按钮
        const reTestBtn = document.getElementById('reTestBtn');
        if (reTestBtn) {
            reTestBtn.style.display = 'inline-block';
        }
    } catch (error) {
        // 隐藏加载状态
        document.getElementById('testLoading').classList.add('d-none');
        
        // 显示错误结果
        document.getElementById('testError').classList.remove('d-none');
        document.getElementById('errorMessage').textContent = error.message;
        
        // 显示重新测试按钮
        document.getElementById('reTestBtn').style.display = 'inline-block';
    }
}

// 测试模型API连接
async function testModelAPI(platform, modelId) {
    try {
        // 清除上一次的测试结果
        document.getElementById('testLoading').classList.remove('d-none');
        document.getElementById('testResult').classList.add('d-none');
        document.getElementById('testError').classList.add('d-none');
        document.getElementById('reTestBtn').style.display = 'none';
        
        // 清除测试详情内容
        const testDetails = document.getElementById('testDetails');
        if (testDetails) {
            testDetails.innerHTML = '';
        }
        
        // 显示测试模态窗口
        const testModal = new bootstrap.Modal(document.getElementById('apiTestModal'), { backdrop: false });
        testModal.show();
        
        // 获取平台配置
        const platformConfig = aiPlatformManager.getPlatform(platform);
        if (!platformConfig) {
            throw new Error('平台配置不存在');
        }
        
        // 获取模型信息
        const model = platformConfig.models.find(m => m.id === modelId);
        if (!model) {
            throw new Error('模型不存在');
        }
        
        // 执行测试
        const result = await aiPlatformManager.testAPI(platform, modelId);
        
        // 隐藏加载状态
        document.getElementById('testLoading').classList.add('d-none');
        
        if (result.success) {
            // 显示成功结果
            document.getElementById('testResult').classList.remove('d-none');
            document.getElementById('testDetails').classList.remove('d-none');
            
            // 填充测试详情
            const testDetails = document.getElementById('testDetails');
            if (testDetails) {
                // 确保测试详情元素有内容
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
        } else {
            // 显示错误结果
            document.getElementById('testError').classList.remove('d-none');
            const errorMessage = document.getElementById('errorMessage');
            if (errorMessage) {
                errorMessage.textContent = result.error;
            }
        }
        
        // 显示重新测试按钮
        const reTestBtn = document.getElementById('reTestBtn');
        if (reTestBtn) {
            reTestBtn.style.display = 'inline-block';
        }
        
    } catch (error) {
        console.error('测试模型API连接失败:', error);
        
        // 隐藏加载状态
        document.getElementById('testLoading').classList.add('d-none');
        
        // 显示错误结果
        document.getElementById('testError').classList.remove('d-none');
        document.getElementById('errorMessage').textContent = error.message;
        
        // 显示重新测试按钮
        document.getElementById('reTestBtn').style.display = 'inline-block';
    }
}

// 配置模型
function configModel(platform, modelId) {
    // 这里可以添加模型配置逻辑
    console.log(`配置模型: ${platform} - ${modelId}`);
    alert(`配置模型: ${platform} - ${modelId}`);
}

// 显示通知
function showNotification(message, type = 'info') {
    const container = document.querySelector('.notification-container');
    if (!container) return;
    
    const notification = document.createElement('div');
    notification.className = `notification notification-${type}`;
    notification.textContent = message;
    
    container.appendChild(notification);
    
    setTimeout(() => {
        notification.remove();
    }, 3000);
}

// 初始化选项卡切换
function initTabs() {
    try {
        const navLinks = document.querySelectorAll('#sidebar .nav-link');
        const tabContents = document.querySelectorAll('.tab-content');
        
        if (navLinks.length === 0 || tabContents.length === 0) {
            console.error('无法找到导航链接或标签内容');
            return;
        }
        
        navLinks.forEach(link => {
            link.addEventListener('click', function(e) {
                e.preventDefault();
                
                // 移除所有活动状态
                navLinks.forEach(l => l.classList.remove('active'));
                tabContents.forEach(tab => tab.classList.remove('active'));
                
                // 添加当前活动状态
                this.classList.add('active');
                const tabId = this.getAttribute('data-tab');
                
                if (!tabId) {
                    console.error('导航链接缺少data-tab属性');
                    return;
                }
                
                const targetTab = document.getElementById(tabId);
                if (!targetTab) {
                    console.error(`找不到id为${tabId}的标签内容`);
                    return;
                }
                
                targetTab.classList.add('active');
                console.log(`切换到标签页: ${tabId}`);
            });
        });
        
        console.log('标签切换初始化成功');
    } catch (error) {
        console.error('初始化标签切换时出错:', error);
    }
}

// 初始化聊天功能
function initChat() {
    const chatInput = document.getElementById('chatInput');
    const sendButton = document.getElementById('sendButton');
    const chatHistory = document.getElementById('chatHistory');
    
    // 发送消息
    function sendMessage() {
        const message = chatInput.value.trim();
        if (message) {
            // 检查是否是命令
            const commandResult = toolManager.handleCommand(message);
            
            if (commandResult) {
                // 处理命令
                addMessage('player', '我', message);
                chatInput.value = '';
                
                // 检查是否是骰子命令
                if (message.toLowerCase().startsWith('/dice')) {
                    // 显示骰娘的回复
                    setTimeout(() => {
                        addMessage('dice', '骰娘', commandResult);
                    }, 500);
                } else {
                    // 显示系统回复
                    setTimeout(() => {
                        addMessage('system', '系统', commandResult);
                    }, 500);
                }
            } else {
                // 添加玩家消息
                addMessage('player', '我', message);
                chatInput.value = '';
                
                // 发送消息到后端API
                fetch('/api/messages', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json'
                    },
                    body: JSON.stringify({
                        content: message,
                        user_id: 'user_' + Date.now()
                    })
                })
                .then(response => response.json())
                .then(data => {
                    console.log('消息发送成功:', data);
                    // 模拟 AI 回复
                    setTimeout(() => {
                        addMessage('kp', 'KP', '这是 AI 的回复...');
                    }, 1000);
                })
                .catch(error => {
                    console.error('消息发送失败:', error);
                    // 即使发送失败，也显示模拟回复
                    setTimeout(() => {
                        addMessage('kp', 'KP', '这是 AI 的回复...');
                    }, 1000);
                });
            }
        }
    }
    
    // 添加消息到聊天历史
    function addMessage(type, sender, content) {
        const messageDiv = document.createElement('div');
        
        // 根据消息类型设置不同的样式类
        let messageClass = '';
        let avatarSrc = '';
        
        switch (type) {
            case 'player':
                messageClass = 'player-message';
                // 使用当前用户的头像，如果没有则使用默认头像
                const userAvatar = document.querySelector('.user-avatar img')?.src || 'https://via.placeholder.com/40';
                avatarSrc = userAvatar;
                break;
            case 'kp':
                messageClass = 'kp-message';
                // 使用KP的专属默认头像
                avatarSrc = '/assets/avatars/default_kp.jpg';
                break;
            case 'dice':
                messageClass = 'dice-message';
                // 使用骰娘的专属头像，添加时间戳避免缓存
                avatarSrc = `/assets/avatars/default_dice.jpg?t=${Date.now()}`;
                // 强制设置发送者为骰娘
                sender = '骰娘';
                break;
            case 'system':
                messageClass = 'other-message';
                // 使用系统的专属默认头像
                avatarSrc = '/assets/avatars/default_system.jpg';
                break;
            case 'other':
                messageClass = 'other-message';
                avatarSrc = 'https://via.placeholder.com/40';
                break;
            default:
                messageClass = 'other-message';
                avatarSrc = 'https://via.placeholder.com/40';
        }
        
        messageDiv.className = `message ${messageClass}`;
        
        const now = new Date();
        const time = `${now.getHours().toString().padStart(2, '0')}:${now.getMinutes().toString().padStart(2, '0')}`;
        
        // 构建消息HTML，包含头像、发送者、时间和内容
        messageDiv.innerHTML = `
            <div class="message-avatar">
                <img src="${avatarSrc}" alt="${sender}">
            </div>
            <div class="message-content-container">
                <div class="message-header">
                    <span class="message-sender">${sender}</span>
                    <span class="message-time">${time}</span>
                </div>
                <div class="message-content">${content}</div>
            </div>
        `;
        
        chatHistory.appendChild(messageDiv);
        
        // 自动滚动到最新消息
        setTimeout(() => {
            chatHistory.scrollTop = chatHistory.scrollHeight;
        }, 100);
    }
    
    // 绑定事件
    sendButton.addEventListener('click', sendMessage);
    chatInput.addEventListener('keypress', function(e) {
        if (e.key === 'Enter') {
            sendMessage();
        }
    });
}

// 初始化剧本管理
function initScenarioManagement() {
    // 创建剧本控制器实例
    new ScenarioController();
    
    // 绑定封面上传事件 - 使用事件委托，确保动态添加的元素也能响应
    document.addEventListener('change', function(e) {
        if (e.target.id === 'coverUpload') {
            handleCoverUpload(e);
        }
    });
}

// 全局变量，用于存储当前编辑的剧本ID
let currentEditingScenarioId = null;

// 设置当前编辑的剧本ID
function setCurrentEditingScenarioId(id) {
    currentEditingScenarioId = id;
}

// 处理封面上传
function handleCoverUpload(e) {
    const file = e.target.files[0];
    if (file) {
        // 检查文件大小（限制为5MB）
        if (file.size > 5 * 1024 * 1024) {
            showNotification('封面文件大小不能超过5MB', 'error');
            return;
        }
        
        // 检查文件类型
        if (!file.type.startsWith('image/')) {
            showNotification('请上传图片文件', 'error');
            return;
        }
        
        // 预览封面
        const reader = new FileReader();
        reader.onload = function(e) {
            document.getElementById('coverPreview').src = e.target.result;
        };
        reader.readAsDataURL(file);
        
        // 保存文件到隐藏字段，以便在保存剧本时使用
        window.uploadedCoverFile = file;
        
        // 上传封面到服务器
        const formData = new FormData();
        formData.append('cover', file);
        // 传递剧本标题到服务器
        const scenarioTitle = document.getElementById('scenarioTitle').value.trim() || 'unknown_scenario';
        formData.append('scenario_title', scenarioTitle);
        
        fetch('/api/scenarios/cover', {
            method: 'POST',
            body: formData
        })
        .then(response => {
            if (!response.ok) {
                return response.json().then(err => {
                    throw new Error(err.message || '上传失败');
                });
            }
            return response.json();
        })
        .then(data => {
            if (data.success) {
                showNotification('封面上传成功', 'success');
                // 保存封面URL到隐藏字段，以便在保存剧本时使用
                document.getElementById('scenarioCoverUrl').value = data.data.cover_url;
            } else {
                showNotification(data.message, 'error');
            }
        })
        .catch(error => {
            console.error('上传封面失败:', error);
            showNotification('上传封面失败: ' + error.message, 'error');
        });
    }
}

// 初始化角色卡管理
function initCharacterManagement() {
    const createCharacterBtn = document.getElementById('createCharacter');
    const saveCharacterBtn = document.getElementById('saveCharacter');
    const characterModal = new bootstrap.Modal(document.getElementById('characterModal'));
    const characterList = document.getElementById('characterList');
    
    // 角色卡数据
    let characters = [];
    
    // 打开创建角色卡模态框
    createCharacterBtn.addEventListener('click', function() {
        document.getElementById('characterName').value = '';
        document.getElementById('playerId').value = '';
        document.getElementById('characterBio').value = '';
        document.getElementById('strength').value = '';
        document.getElementById('constitution').value = '';
        document.getElementById('dexterity').value = '';
        document.getElementById('intelligence').value = '';
        document.getElementById('willpower').value = '';
        document.getElementById('luck').value = '';
        document.getElementById('characterSkills').value = '';
        characterModal.show();
    });
    
    // 保存角色卡
    saveCharacterBtn.addEventListener('click', function() {
        const character = {
            id: Date.now(),
            name: document.getElementById('characterName').value,
            playerId: document.getElementById('playerId').value,
            bio: document.getElementById('characterBio').value,
            attributes: {
                strength: document.getElementById('strength').value,
                constitution: document.getElementById('constitution').value,
                dexterity: document.getElementById('dexterity').value,
                intelligence: document.getElementById('intelligence').value,
                willpower: document.getElementById('willpower').value,
                luck: document.getElementById('luck').value
            },
            skills: document.getElementById('characterSkills').value
        };
        
        characters.push(character);
        updateCharacterList();
        characterModal.hide();
    });
    
    // 更新角色卡列表
    function updateCharacterList() {
        characterList.innerHTML = '';
        
        characters.forEach(character => {
            const card = document.createElement('div');
            card.className = 'character-card';
            card.innerHTML = `
                <h5>${character.name}</h5>
                <p>玩家ID: ${character.playerId}</p>
                <p>简介: ${character.bio.substring(0, 50)}${character.bio.length > 50 ? '...' : ''}</p>
                <div class="character-card-actions">
                    <button class="btn btn-sm btn-primary">查看</button>
                    <button class="btn btn-sm btn-secondary">编辑</button>
                    <button class="btn btn-sm btn-danger">删除</button>
                </div>
            `;
            characterList.appendChild(card);
        });
    }
    
    // 加载模拟角色卡数据
    loadMockCharacters();
    
    function loadMockCharacters() {
        characters = [
            {
                id: 1,
                name: '侦探',
                playerId: '玩家1',
                bio: '一名经验丰富的侦探，擅长调查和推理。',
                attributes: {
                    strength: 40,
                    constitution: 50,
                    dexterity: 60,
                    intelligence: 80,
                    willpower: 70,
                    luck: 50
                },
                skills: '侦查:70,推理:80,格斗:40'
            },
            {
                id: 2,
                name: '医生',
                playerId: '玩家2',
                bio: '一名专业的医生，擅长治疗和解剖。',
                attributes: {
                    strength: 30,
                    constitution: 60,
                    dexterity: 50,
                    intelligence: 70,
                    willpower: 60,
                    luck: 40
                },
                skills: '医学:80,急救:70,说服:50'
            }
        ];
        updateCharacterList();
    }
}

// 初始化骰子工具
function initDiceTool() {
    const rollDiceBtn = document.getElementById('rollDice');
    const diceType = document.getElementById('diceType');
    const diceResult = document.getElementById('diceResult');
    
    rollDiceBtn.addEventListener('click', function() {
        const type = diceType.value;
        const sides = parseInt(type.replace('d', ''));
        const result = Math.floor(Math.random() * sides) + 1;
        
        diceResult.textContent = `结果: ${result}`;
    });
}

// 初始化工具标签页
function initToolTabs() {
    const toolTabs = document.querySelectorAll('.tool-tab');
    const toolContents = document.querySelectorAll('.tool-content');
    
    if (toolTabs.length === 0 || toolContents.length === 0) {
        console.error('无法找到工具标签或工具内容');
        return;
    }
    
    toolTabs.forEach(tab => {
        tab.addEventListener('click', function() {
            const toolName = this.getAttribute('data-tool');
            
            // 移除所有活动状态
            toolTabs.forEach(t => t.classList.remove('active'));
            toolContents.forEach(content => content.classList.remove('active'));
            
            // 添加当前活动状态
            this.classList.add('active');
            const targetContent = document.getElementById(`${toolName}-tool-content`);
            if (targetContent) {
                targetContent.classList.add('active');
            }
        });
    });
    
    console.log('工具标签页初始化成功');
}

// 初始化设置标签页
function initSettingsTabs() {
    const settingsTabs = document.querySelectorAll('.settings-tab');
    const settingsContents = document.querySelectorAll('.settings-content');
    
    if (settingsTabs.length === 0 || settingsContents.length === 0) {
        console.error('无法找到设置标签或设置内容');
        return;
    }
    
    settingsTabs.forEach(tab => {
        tab.addEventListener('click', function() {
            const settingsName = this.getAttribute('data-settings');
            
            // 移除所有活动状态
            settingsTabs.forEach(t => t.classList.remove('active'));
            settingsContents.forEach(content => content.classList.remove('active'));
            
            // 添加当前活动状态
            this.classList.add('active');
            const targetContent = document.getElementById(`${settingsName}-settings-content`);
            if (targetContent) {
                targetContent.classList.add('active');
            }
        });
    });
    
    // 绑定温度滑块值显示
    const temperatureSlider = document.getElementById('temperature');
    const temperatureValue = document.getElementById('temperatureValue');
    if (temperatureSlider && temperatureValue) {
        temperatureSlider.addEventListener('input', function() {
            temperatureValue.textContent = this.value;
        });
    }
    
    console.log('设置标签页初始化成功');
}

// 初始化用户认证功能
function initAuth() {
    console.log('开始初始化用户认证功能');
    
    // 检查认证状态
    checkAuthStatus();
    
    // 绑定登录/注册切换标签
    const authTabs = document.querySelectorAll('.auth-tab');
    console.log('找到的认证标签数量:', authTabs.length);
    authTabs.forEach(tab => {
        tab.addEventListener('click', function() {
            const tabName = this.getAttribute('data-tab');
            switchAuthTab(tabName);
        });
    });
    
    // 使用事件委托绑定登录按钮事件
    console.log('使用事件委托绑定登录按钮事件');
    document.addEventListener('click', function(e) {
        if (e.target.id === 'loginButton') {
            console.log('登录按钮被点击');
            login();
        }
    });
    
    // 使用事件委托绑定注册按钮事件
    document.addEventListener('click', function(e) {
        if (e.target.id === 'registerButton') {
            register();
        }
    });
    
    // 绑定登出按钮事件
    const logoutButton = document.getElementById('logoutButton');
    console.log('登出按钮元素:', logoutButton);
    if (logoutButton) {
        logoutButton.addEventListener('click', logout);
    }
    
    // 绑定关闭弹窗按钮事件
    const closeAuthModal = document.getElementById('close-auth-modal');
    console.log('关闭认证弹窗按钮元素:', closeAuthModal);
    if (closeAuthModal) {
        closeAuthModal.addEventListener('click', closeAuthModalFunc);
    }
    
    // 绑定用户信息点击事件
    const userInfo = document.getElementById('userInfo');
    console.log('用户信息元素:', userInfo);
    if (userInfo) {
        userInfo.addEventListener('click', toggleUserSettings);
    }
    
    // 绑定关闭设置面板按钮事件
    const closeSettingsPanel = document.getElementById('close-settings-panel');
    console.log('关闭设置面板按钮元素:', closeSettingsPanel);
    if (closeSettingsPanel) {
        closeSettingsPanel.addEventListener('click', closeSettingsPanelFunc);
    }
    
    // 绑定保存用户设置按钮事件
    const saveUserSettings = document.getElementById('saveUserSettings');
    console.log('保存用户设置按钮元素:', saveUserSettings);
    if (saveUserSettings) {
        saveUserSettings.addEventListener('click', saveUserSettingsFunc);
    }
    
    // 绑定头像上传事件
    const avatarUpload = document.getElementById('avatarUpload');
    console.log('头像上传元素:', avatarUpload);
    if (avatarUpload) {
        avatarUpload.addEventListener('change', handleAvatarUpload);
    }
    
    console.log('用户认证功能初始化完成');
}

// 处理头像上传
function handleAvatarUpload(e) {
    const file = e.target.files[0];
    if (file) {
        // 检查文件大小（限制为2MB）
        if (file.size > 2 * 1024 * 1024) {
            showNotification('头像文件大小不能超过2MB', 'error');
            return;
        }
        
        // 检查文件类型
        if (!file.type.startsWith('image/')) {
            showNotification('请上传图片文件', 'error');
            return;
        }
        
        // 预览头像
        const reader = new FileReader();
        reader.onload = function(e) {
            document.getElementById('avatarPreview').src = e.target.result;
        };
        reader.readAsDataURL(file);
    }
}

// 切换登录/注册标签
function switchAuthTab(tabName) {
    // 更新标签状态
    document.querySelectorAll('.auth-tab').forEach(tab => {
        tab.classList.remove('active');
    });
    document.querySelector(`.auth-tab[data-tab="${tabName}"]`).classList.add('active');
    
    // 更新表单显示
    document.querySelectorAll('.auth-form').forEach(form => {
        form.classList.remove('active');
    });
    document.getElementById(`${tabName}-form`).classList.add('active');
}

// 检查认证状态
function checkAuthStatus() {
    fetch('/api/auth/status')
        .then(response => response.json())
        .then(data => {
            if (data.success) {
                // 已登录
                showLoggedInState(data.data);
                closeAuthModalFunc();
            } else {
                // 未登录
                showAuthModal();
            }
        })
        .catch(error => {
            console.error('检查认证状态失败:', error);
            showAuthModal();
        });
}

// 显示认证弹窗
function showAuthModal() {
    document.getElementById('auth-modal').style.display = 'flex';
}

// 关闭认证弹窗
function closeAuthModalFunc() {
    document.getElementById('auth-modal').style.display = 'none';
}

// 显示已登录状态
function showLoggedInState(userData) {
    // 更新用户信息区域
    document.getElementById('userName').textContent = userData.username;
    // 更新用户头像
    if (userData.avatar) {
        document.querySelector('.user-avatar img').src = userData.avatar;
    }
    
    // 隐藏认证弹窗
    closeAuthModalFunc();
    
    // 隐藏用户设置面板
    closeSettingsPanelFunc();
}

// 切换用户设置面板
function toggleUserSettings() {
    const settingsPanel = document.getElementById('user-settings-panel');
    if (settingsPanel.style.display === 'block') {
        closeSettingsPanelFunc();
    } else {
        openSettingsPanel();
    }
}

// 打开用户设置面板
function openSettingsPanel() {
    document.getElementById('user-settings-panel').style.display = 'block';
    
    // 加载用户信息
    fetch('/api/auth/status')
        .then(response => response.json())
        .then(data => {
            if (data.success) {
                document.getElementById('editUsername').value = data.data.username;
                document.getElementById('editEmail').value = data.data.email;
                // 加载用户头像
                if (data.data.avatar) {
                    document.getElementById('avatarPreview').src = data.data.avatar;
                }
            }
        })
        .catch(error => {
            console.error('获取用户信息失败:', error);
        });
}

// 关闭用户设置面板
function closeSettingsPanelFunc() {
    document.getElementById('user-settings-panel').style.display = 'none';
}

// 登录
function login() {
    const username = document.getElementById('loginUsername').value;
    const password = document.getElementById('loginPassword').value;
    const rememberMe = document.getElementById('rememberMe').checked;
    const stayLoggedIn = document.getElementById('stayLoggedIn').checked;
    const autoLogin = document.getElementById('autoLogin').checked;
    const messageElement = document.getElementById('loginMessage');
    
    if (!username || !password) {
        messageElement.textContent = '请输入用户名和密码';
        messageElement.style.color = 'red';
        return;
    }
    
    fetch('/api/auth/login', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json'
        },
        body: JSON.stringify({ 
            username, 
            password,
            remember_me: rememberMe,
            stay_logged_in: stayLoggedIn,
            auto_login: autoLogin
        })
    })
    .then(response => response.json())
    .then(data => {
        if (data.success) {
            messageElement.textContent = '登录成功';
            messageElement.style.color = 'green';
            showLoggedInState(data.data);
        } else {
            messageElement.textContent = data.message;
            messageElement.style.color = 'red';
        }
    })
    .catch(error => {
        console.error('登录失败:', error);
        messageElement.textContent = '登录失败，请稍后重试';
        messageElement.style.color = 'red';
    });
}

// 注册
function register() {
    const username = document.getElementById('registerUsername').value;
    const password = document.getElementById('registerPassword').value;
    const email = document.getElementById('registerEmail').value;
    const messageElement = document.getElementById('registerMessage');
    
    if (!username || !password || !email) {
        messageElement.textContent = '请输入用户名、密码和邮箱';
        messageElement.style.color = 'red';
        return;
    }
    
    fetch('/api/auth/register', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json'
        },
        body: JSON.stringify({ username, password, email })
    })
    .then(response => response.json())
    .then(data => {
        if (data.success) {
            messageElement.textContent = '注册成功，请登录';
            messageElement.style.color = 'green';
            switchAuthTab('login');
        } else {
            messageElement.textContent = data.message;
            messageElement.style.color = 'red';
        }
    })
    .catch(error => {
        console.error('注册失败:', error);
        messageElement.textContent = '注册失败，请稍后重试';
        messageElement.style.color = 'red';
    });
}

// 登出
function logout() {
    fetch('/api/auth/logout', {
        method: 'POST'
    })
    .then(response => response.json())
    .then(data => {
        if (data.success) {
            document.getElementById('userName').textContent = '未登录';
            closeSettingsPanelFunc();
            showAuthModal();
        }
    })
    .catch(error => {
        console.error('登出失败:', error);
    });
}

// 保存用户设置
function saveUserSettingsFunc() {
    const username = document.getElementById('editUsername').value;
    const nickname = document.getElementById('editNickname').value;
    const email = document.getElementById('editEmail').value;
    const password = document.getElementById('editPassword').value;
    const confirmPassword = document.getElementById('confirmPassword').value;
    const messageElement = document.getElementById('settingsMessage');
    const avatarInput = document.getElementById('avatarUpload');
    
    if (!username || !email) {
        messageElement.textContent = '请输入用户名和邮箱';
        messageElement.style.color = 'red';
        return;
    }
    
    if (password && password !== confirmPassword) {
        messageElement.textContent = '两次输入的密码不一致';
        messageElement.style.color = 'red';
        return;
    }
    
    // 创建FormData对象
    const formData = new FormData();
    formData.append('username', username);
    formData.append('nickname', nickname);
    formData.append('email', email);
    if (password) {
        formData.append('password', password);
    }
    
    // 添加头像文件（如果有）
    if (avatarInput.files && avatarInput.files[0]) {
        formData.append('avatar', avatarInput.files[0]);
    }
    
    // 发送更新请求
    fetch('/api/auth/update', {
        method: 'POST',
        body: formData
    })
    .then(response => response.json())
    .then(data => {
        if (data.success) {
            messageElement.textContent = '设置保存成功';
            messageElement.style.color = 'green';
            
            // 更新用户头像
            if (data.data && data.data.avatar) {
                document.querySelector('.user-avatar img').src = data.data.avatar;
            }
        } else {
            messageElement.textContent = data.message;
            messageElement.style.color = 'red';
        }
    })
    .catch(error => {
        console.error('更新用户设置失败:', error);
        messageElement.textContent = '更新失败，请稍后重试';
        messageElement.style.color = 'red';
    });
    
    // 3秒后关闭消息
    setTimeout(() => {
        messageElement.textContent = '';
    }, 3000);
}