interface RoleConfig {
    id: string;
    name: string;
    wake_words?: string[];
    provider?: string;
    prompt?: string;
}

interface RoleConfigResponse {
    roles: RoleConfig[];
    enabled_providers: Array<{ id: string; name: string }>;
}

async function initAIPlatforms(): Promise<void> {
    try {
        const platforms = await aiPlatformManager.loadPlatforms();
        renderPlatforms(platforms);
        bindRoleConfigSettings();
        await loadRoleConfigs();
        bindAddModelEvents();
        bindAPITestEvents();
        console.log("AI 平台管理初始化完成");
    } catch (error) {
        console.error("初始化 AI 平台管理失败:", error);
    }
}

function renderPlatforms(platforms: AIPlatformConfig[]): void {
    const container = document.getElementById("ai-platforms-container");
    if (!container) return;
    container.innerHTML = "";
    platforms.forEach((platform) => container.appendChild(createPlatformCard(platform)));
}

function bindRoleConfigSettings(): void {
    const list = document.getElementById("roleConfigList");
    if (!list || list.dataset.bound === "true") return;

    list.dataset.bound = "true";
    list.addEventListener("click", (event) => {
        const button = (event.target as HTMLElement).closest<HTMLButtonElement>(".save-role-config");
        if (!button) return;
        void saveRoleConfig(button.dataset.roleId || "");
    });
}

async function loadRoleConfigs(): Promise<void> {
    const list = document.getElementById("roleConfigList");
    if (!list) return;

    try {
        const response = await TrpgApi.get<ApiResponse<RoleConfigResponse>>("/api/config/roles");
        if (!response.success || !response.data) {
            setRoleConfigMessage(response.error || response.message || "加载角色配置失败", true);
            return;
        }
        renderRoleConfigCards(response.data.roles || [], response.data.enabled_providers || []);
        setRoleConfigMessage("");
    } catch (error) {
        console.error("加载角色配置失败:", error);
        setRoleConfigMessage("加载角色配置失败，请确认当前账号具有管理员权限", true);
    }
}

function renderRoleConfigCards(roles: RoleConfig[], providers: Array<{ id: string; name: string }>): void {
    const list = document.getElementById("roleConfigList");
    if (!list) return;

    if (roles.length === 0) {
        list.innerHTML = '<div class="role-config-card">暂无角色配置</div>';
        return;
    }

    list.innerHTML = roles.map((role) => {
        const providerOptions = providers.map((provider) => {
            const selected = provider.id === role.provider ? "selected" : "";
            return `<option value="${platformEscapeHtml(provider.id)}" ${selected}>${platformEscapeHtml(provider.name)}</option>`;
        }).join("");
        const wakeWords = (role.wake_words || []).join(", ");
        return `
            <article class="role-config-card" data-role-id="${platformEscapeHtml(role.id)}">
                <div class="role-config-card-header">
                    <div>
                        <h5 class="role-config-card-title">${platformEscapeHtml(role.name)}</h5>
                        <div class="role-config-wake">${platformEscapeHtml(wakeWords || `@${role.name}`)}</div>
                    </div>
                    <button type="button" class="btn btn-primary save-role-config" data-role-id="${platformEscapeHtml(role.id)}">
                        <i class="fa fa-floppy-o" aria-hidden="true"></i> 保存
                    </button>
                </div>
                <label class="form-label" for="roleWakeWords-${platformEscapeHtml(role.id)}">唤醒词</label>
                <input class="form-control role-wake-input" id="roleWakeWords-${platformEscapeHtml(role.id)}" value="${platformEscapeHtml(wakeWords)}" placeholder="@KP, @Keeper">
                <label class="form-label" for="roleProvider-${platformEscapeHtml(role.id)}">大模型提供商</label>
                <select class="form-control role-provider-select" id="roleProvider-${platformEscapeHtml(role.id)}">${providerOptions}</select>
                <label class="form-label" for="rolePrompt-${platformEscapeHtml(role.id)}">角色提示词</label>
                <textarea class="form-control role-config-prompt" id="rolePrompt-${platformEscapeHtml(role.id)}" rows="8">${platformEscapeHtml(role.prompt || "")}</textarea>
            </article>
        `;
    }).join("");
}

async function saveRoleConfig(roleId: string): Promise<void> {
    if (!roleId) return;
    const card = document.querySelector<HTMLElement>(`.role-config-card[data-role-id="${CSS.escape(roleId)}"]`);
    if (!card) return;

    const wakeWords = (card.querySelector<HTMLInputElement>(".role-wake-input")?.value || "")
        .split(",")
        .map((item) => item.trim())
        .filter(Boolean);
    const provider = card.querySelector<HTMLSelectElement>(".role-provider-select")?.value || "";
    const prompt = card.querySelector<HTMLTextAreaElement>(".role-config-prompt")?.value || "";

    try {
        const response = await TrpgApi.post<ApiResponse>(`/api/config/roles/${encodeURIComponent(roleId)}`, {
            name: card.querySelector(".role-config-card-title")?.textContent || roleId,
            wake_words: wakeWords,
            provider,
            prompt,
        });
        if (!response.success) {
            setRoleConfigMessage(response.error || response.message || "保存角色配置失败", true);
            return;
        }
        setRoleConfigMessage("角色配置已保存");
        window.loadAIRoles?.();
        await loadRoleConfigs();
    } catch (error) {
        console.error("保存角色配置失败:", error);
        setRoleConfigMessage("保存角色配置失败，请稍后重试", true);
    }
}

function setRoleConfigMessage(message: string, isError = false): void {
    const messageElement = document.getElementById("roleConfigMessage");
    if (!messageElement) return;
    messageElement.textContent = message;
    messageElement.classList.toggle("error", isError);
    messageElement.classList.toggle("success", Boolean(message && !isError));
}

function createPlatformCard(platform: AIPlatformConfig): HTMLElement {
    const card = document.createElement("div");
    card.className = "ai-platform-card";
    card.innerHTML = `
        <div class="platform-header platform-card-header" data-platform="${platformEscapeHtml(platform.platform)}">
            <div class="platform-info">
                <img src="${platformEscapeHtml(platform.icon)}" alt="${platformEscapeHtml(platform.name)}" class="platform-icon">
                <div class="platform-details">
                    <h5>${platformEscapeHtml(platform.name)}</h5>
                    <p>${platformEscapeHtml(platform.description)}</p>
                </div>
            </div>
            <div class="platform-toggle">
                <label for="toggle-${platformEscapeHtml(platform.platform)}">${platform.enabled ? "已启用" : "已禁用"}</label>
                <div class="form-check form-switch">
                    <input class="form-check-input platform-toggle-input" type="checkbox" id="toggle-${platformEscapeHtml(platform.platform)}" ${platform.enabled ? "checked" : ""} data-platform="${platformEscapeHtml(platform.platform)}">
                </div>
            </div>
            <div class="platform-action">
                <button class="btn btn-sm btn-primary config-btn" data-platform="${platformEscapeHtml(platform.platform)}">配置</button>
            </div>
        </div>
    `;

    card.querySelector(".platform-card-header")?.addEventListener("click", (event) => {
        if ((event.target as HTMLElement).closest(".platform-toggle")) return;
        void openPlatformConfigModal(platform.platform);
    });

    card.querySelector(".config-btn")?.addEventListener("click", (event) => {
        event.stopPropagation();
        void openPlatformConfigModal(platform.platform);
    });

    card.querySelector<HTMLInputElement>(".platform-toggle-input")?.addEventListener("change", async (event) => {
        const input = event.currentTarget as HTMLInputElement;
        const success = await aiPlatformManager.setPlatformEnabled(platform.platform, input.checked);
        if (success) {
            const label = card.querySelector<HTMLLabelElement>(`label[for="toggle-${CSS.escape(platform.platform)}"]`);
            if (label) label.textContent = input.checked ? "已启用" : "已禁用";
        }
    });

    return card;
}

async function openPlatformConfigModal(platformName: string): Promise<void> {
    const platform = aiPlatformManager.getPlatform(platformName);
    if (!platform) {
        alert("平台配置加载失败");
        return;
    }

    const modalElement = document.getElementById("platformConfigModal");
    const content = document.getElementById("platformConfigContent");
    const title = document.getElementById("platformConfigModalLabel");
    if (!modalElement || !content || !title) return;

    title.textContent = `${platform.name} 配置`;
    content.innerHTML = buildPlatformConfigHTML(platform);
    bindPasswordToggles();
    bindTimeoutSlider(platform.platform);
    bindModelEvents(platform);
    bindPlatformSave(platform);

    new bootstrap.Modal(modalElement, { backdrop: false }).show();
}

function buildPlatformConfigHTML(platform: AIPlatformConfig): string {
    return `
        <div class="api-config">
            <h6>API 配置</h6>
            <div class="form-group">
                <label for="modal-api-key-${platformEscapeHtml(platform.platform)}">API Key</label>
                <div class="password-input-group">
                    <input type="password" class="form-control api-key-input" id="modal-api-key-${platformEscapeHtml(platform.platform)}" value="${platformEscapeHtml(platform.config.api_key || "")}">
                    <span class="password-toggle" data-target="modal-api-key-${platformEscapeHtml(platform.platform)}"><i class="bi bi-eye"></i></span>
                </div>
            </div>
            <div class="form-group mt-2">
                <label for="modal-base-url-${platformEscapeHtml(platform.platform)}">Base URL</label>
                <input type="text" class="form-control base-url-input" id="modal-base-url-${platformEscapeHtml(platform.platform)}" value="${platformEscapeHtml(platform.config.base_url)}">
            </div>
            <div class="form-group mt-2">
                <label for="modal-timeout-${platformEscapeHtml(platform.platform)}">超时设置 (${platform.config.timeout} 秒)</label>
                <input type="range" class="form-range timeout-slider" id="modal-timeout-${platformEscapeHtml(platform.platform)}" min="10" max="60" step="5" value="${platform.config.timeout}" data-platform="${platformEscapeHtml(platform.platform)}">
                <div class="timeout-value" id="modal-timeout-value-${platformEscapeHtml(platform.platform)}">${platform.config.timeout} 秒</div>
            </div>
        </div>
        ${platform.platform === "lmstudio" ? buildLMStudioHelp(platform) : buildModelList(platform)}
    `;
}

function buildModelList(platform: AIPlatformConfig): string {
    return `
        <div class="models-section">
            <h6>
                模型管理
                <button class="btn btn-sm btn-primary add-model-btn" data-platform="${platformEscapeHtml(platform.platform)}">+ 添加模型</button>
            </h6>
            <div class="models-list" id="modal-models-list-${platformEscapeHtml(platform.platform)}">
                ${platform.models.map((model) => `
                    <div class="model-item">
                        <div class="model-info">
                            <h7>${platformEscapeHtml(model.name)}</h7>
                            <p>${platformEscapeHtml(model.description)}</p>
                        </div>
                        <div class="model-actions">
                            <div class="form-check form-switch">
                                <input class="form-check-input model-toggle-input" type="checkbox" ${model.enabled ? "checked" : ""} data-platform="${platformEscapeHtml(platform.platform)}" data-model="${platformEscapeHtml(model.id)}">
                            </div>
                            <button class="btn btn-sm btn-primary test-model-btn" data-platform="${platformEscapeHtml(platform.platform)}" data-model="${platformEscapeHtml(model.id)}">测试连接</button>
                            <button class="btn btn-sm btn-primary config-model-btn" data-platform="${platformEscapeHtml(platform.platform)}" data-model="${platformEscapeHtml(model.id)}">配置</button>
                            <button class="btn btn-sm btn-danger remove-model-btn" data-platform="${platformEscapeHtml(platform.platform)}" data-model="${platformEscapeHtml(model.id)}">删除</button>
                        </div>
                    </div>
                `).join("")}
            </div>
        </div>
    `;
}

function buildLMStudioHelp(platform: AIPlatformConfig): string {
    return `
        <div class="models-section">
            <h6>模型说明 <button class="btn btn-sm btn-primary test-platform-btn" data-platform="${platformEscapeHtml(platform.platform)}">测试连接</button></h6>
            <div class="alert alert-info">
                <p>LMStudio 平台使用本地运行的模型，无需选择模型。</p>
                <p>请确认 LMStudio 服务正在运行。</p>
            </div>
        </div>
    `;
}

function bindPasswordToggles(): void {
    document.querySelectorAll<HTMLElement>(".password-toggle").forEach((toggle) => {
        toggle.addEventListener("click", () => {
            const targetId = toggle.dataset.target || "";
            const input = document.getElementById(targetId) as HTMLInputElement | null;
            if (!input) return;
            input.type = input.type === "password" ? "text" : "password";
            const icon = toggle.querySelector("i");
            if (icon) icon.className = input.type === "password" ? "bi bi-eye" : "bi bi-eye-slash";
        });
    });
}

function bindTimeoutSlider(platformName: string): void {
    document.getElementById(`modal-timeout-${platformName}`)?.addEventListener("input", (event) => {
        const input = event.currentTarget as HTMLInputElement;
        const valueDisplay = document.getElementById(`modal-timeout-value-${platformName}`);
        if (valueDisplay) valueDisplay.textContent = `${input.value} 秒`;
    });
}

function bindPlatformSave(platform: AIPlatformConfig): void {
    const saveButton = document.getElementById("savePlatformConfigBtn");
    if (!saveButton) return;
    saveButton.onclick = async () => {
        const apiKey = document.getElementById(`modal-api-key-${platform.platform}`) as HTMLInputElement | null;
        const baseUrl = document.getElementById(`modal-base-url-${platform.platform}`) as HTMLInputElement | null;
        const timeout = document.getElementById(`modal-timeout-${platform.platform}`) as HTMLInputElement | null;
        if (!apiKey || !baseUrl || !timeout) return;

        platform.config.api_key = apiKey.value;
        platform.config.base_url = normalizeChatCompletionsUrl(baseUrl.value);
        platform.config.timeout = Number.parseInt(timeout.value, 10);
        await aiPlatformManager.savePlatformConfig(platform.platform, platform);
        bootstrap.Modal.getInstance(document.getElementById("platformConfigModal"))?.hide();
        alert("配置保存成功");
    };
}

function bindModelEvents(platform: AIPlatformConfig): void {
    document.querySelectorAll<HTMLButtonElement>(".remove-model-btn").forEach((button) => {
        button.addEventListener("click", async () => {
            const modelId = button.dataset.model || "";
            if (!modelId || !confirm("确定要删除这个模型吗？")) return;
            if (await aiPlatformManager.removeModel(platform.platform, modelId)) {
                await openPlatformConfigModal(platform.platform);
            }
        });
    });

    document.querySelectorAll<HTMLButtonElement>(".test-model-btn, .test-platform-btn").forEach((button) => {
        button.addEventListener("click", () => {
            const modelId = button.dataset.model || (platform.platform === "lmstudio" ? "local-model" : platform.models[0]?.id || "");
            if (modelId) void testModelAPI(platform.platform, modelId);
        });
    });

    document.querySelectorAll<HTMLButtonElement>(".config-model-btn").forEach((button) => {
        button.addEventListener("click", () => {
            const modelId = button.dataset.model || "";
            if (modelId) void configModel(platform.platform, modelId);
        });
    });
}

function bindAddModelEvents(): void {
    document.addEventListener("click", (event) => {
        const button = (event.target as HTMLElement).closest<HTMLButtonElement>(".add-model-btn");
        if (!button) return;
        window.currentPlatform = button.dataset.platform || "";
        setFormValue("modelName", "");
        setFormValue("modelId", "");
        setFormValue("modelDescription", "");
        setDisabled("addModelBtn", true);
        const modalElement = document.getElementById("addModelModal");
        if (modalElement) new bootstrap.Modal(modalElement).show();
    });

    ["modelName", "modelId"].forEach((id) => {
        document.getElementById(id)?.addEventListener("input", validateAddModelForm);
    });

    document.getElementById("addModelBtn")?.addEventListener("click", async () => {
        const platform = window.currentPlatform || "";
        if (!platform) return;
        const model = {
            name: formValue("modelName").trim(),
            id: formValue("modelId").trim(),
            description: formValue("modelDescription").trim(),
        };
        const success = await aiPlatformManager.addModel(platform, model);
        if (success) {
            bootstrap.Modal.getInstance(document.getElementById("addModelModal"))?.hide();
            renderPlatforms(await aiPlatformManager.loadPlatforms());
            showNotification("模型添加成功", "success");
        } else {
            showNotification("模型添加失败", "error");
        }
    });
}

function validateAddModelForm(): void {
    setDisabled("addModelBtn", !formValue("modelName").trim() || !formValue("modelId").trim());
}

function bindAPITestEvents(): void {
    document.addEventListener("click", (event) => {
        const button = (event.target as HTMLElement).closest<HTMLButtonElement>(".test-api-btn");
        if (!button) return;
        const platform = button.dataset.platform || "";
        if (platform) void testAPI(platform);
    });

    document.getElementById("reTestBtn")?.addEventListener("click", () => {
        const platform = window.currentTestingPlatform || "";
        if (platform) void testAPI(platform);
    });
}

function resetTestModal(): void {
    toggleClass("testLoading", "d-none", false);
    toggleClass("testStatus", "d-none", true);
    toggleClass("testResult", "d-none", true);
    toggleClass("testError", "d-none", true);
    toggleClass("testDetails", "d-none", true);
    const reTestBtn = document.getElementById("reTestBtn") as HTMLElement | null;
    if (reTestBtn) reTestBtn.style.display = "none";
    const testDetails = document.getElementById("testDetails");
    if (testDetails) testDetails.innerHTML = "";
}

async function testAPI(platform: string): Promise<void> {
    const platformConfig = aiPlatformManager.getPlatform(platform);
    if (!platformConfig) return;
    const model = platform === "lmstudio"
        ? { id: "local-model" }
        : platformConfig.models.find((item) => item.enabled) || platformConfig.models[0];
    if (model) await testModelAPI(platform, model.id);
}

async function testModelAPI(platform: string, modelId: string): Promise<void> {
    window.currentTestingPlatform = platform;
    const modalElement = document.getElementById("apiTestModal");
    if (modalElement) new bootstrap.Modal(modalElement, { backdrop: false }).show();
    resetTestModal();

    const result = await aiPlatformManager.testAPI(platform, modelId);
    toggleClass("testLoading", "d-none", true);
    const reTestBtn = document.getElementById("reTestBtn") as HTMLElement | null;
    if (reTestBtn) reTestBtn.style.display = "inline-block";

    if (result.success) {
        toggleClass("testResult", "d-none", false);
        toggleClass("testDetails", "d-none", false);
        fillTestDetails(result);
    } else {
        toggleClass("testError", "d-none", false);
        const errorMessage = document.getElementById("errorMessage");
        if (errorMessage) errorMessage.textContent = result.error || "测试失败";
    }
}

function fillTestDetails(result: AITestResult): void {
    const testDetails = document.getElementById("testDetails");
    if (!testDetails) return;
    testDetails.innerHTML = `
        <h6>测试详情</h6>
        <p><strong>测试时间：</strong>${platformEscapeHtml(result.time || "-")}</p>
        <p><strong>模型：</strong>${platformEscapeHtml(result.model || "-")}</p>
        <p><strong>平均速度：</strong>${platformEscapeHtml(result.speed || "-")}</p>
        <p><strong>消耗：</strong>${platformEscapeHtml(result.consumption || "-")}</p>
    `;
}

async function configModel(platform: string, modelId: string): Promise<void> {
    const platformConfig = aiPlatformManager.getPlatform(platform);
    const model = platformConfig?.models.find((item) => item.id === modelId);
    if (!platformConfig || !model) return;

    const modelRequestConfig = await loadModelRequestConfig(platform, modelId);
    const modalElement = document.createElement("div");
    modalElement.className = "modal fade";
    modalElement.id = "modelConfigModal";
    modalElement.tabIndex = -1;
    modalElement.innerHTML = `
        <div class="modal-dialog modal-lg">
            <div class="modal-content">
                <div class="modal-header">
                    <h5 class="modal-title">${platformEscapeHtml(model.name)} 配置</h5>
                    <button type="button" class="btn-close" data-bs-dismiss="modal" aria-label="Close"></button>
                </div>
                <div class="modal-body">
                    <textarea class="form-control" id="modelRequestConfig" rows="20">${platformEscapeHtml(modelRequestConfig)}</textarea>
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

    document.getElementById("saveModelConfigBtn")?.addEventListener("click", async () => {
        try {
            const textarea = document.getElementById("modelRequestConfig") as HTMLTextAreaElement | null;
            const requestConfig = JSON.parse(textarea?.value || "{}") as unknown;
            const { response } = await TrpgApi.requestWithResponse<ApiResponse>("/api/config/aimodel/save", {
                method: "POST",
                body: { platform, modelId, content: requestConfig },
            });
            if (!response.ok) throw new Error("保存 JSON 配置失败");
            modal.hide();
            alert("JSON 配置保存成功");
        } catch (error) {
            alert(`保存 JSON 配置失败: ${platformErrorMessage(error)}`);
        }
    });

    modalElement.addEventListener("hidden.bs.modal", () => {
        setTimeout(() => modalElement.remove(), 100);
    });
}

async function loadModelRequestConfig(platform: string, modelId: string): Promise<string> {
    try {
        const response = await fetch(`config/aimodel/${platform}/${modelId}.json`);
        if (response.ok) return JSON.stringify(await response.json(), null, 2);
        const fallback = await fetch("config/aiplatform/default-request.json");
        if (fallback.ok) {
            const config = await fallback.json() as Record<string, unknown>;
            config.model = modelId;
            return JSON.stringify(config, null, 2);
        }
    } catch (error) {
        console.error("加载模型请求配置失败:", error);
    }
    return "{}";
}

function showNotification(message: string, type = "info"): void {
    const container = document.querySelector(".notification-container");
    if (!container) return;
    const notification = document.createElement("div");
    notification.className = `notification notification-${type}`;
    notification.textContent = message;
    container.appendChild(notification);
    setTimeout(() => notification.remove(), 3000);
}

function normalizeChatCompletionsUrl(url: string): string {
    return url.endsWith("/v1/chat/completions") ? url : `${url.replace(/\/+$/, "")}/v1/chat/completions`;
}

function formValue(id: string): string {
    return (document.getElementById(id) as HTMLInputElement | HTMLTextAreaElement | null)?.value || "";
}

function setFormValue(id: string, value: string): void {
    const input = document.getElementById(id) as HTMLInputElement | HTMLTextAreaElement | null;
    if (input) input.value = value;
}

function setDisabled(id: string, disabled: boolean): void {
    const button = document.getElementById(id) as HTMLButtonElement | null;
    if (button) button.disabled = disabled;
}

function toggleClass(id: string, className: string, force: boolean): void {
    document.getElementById(id)?.classList.toggle(className, force);
}

function platformEscapeHtml(value: unknown): string {
    return String(value ?? "")
        .replace(/&/g, "&amp;")
        .replace(/</g, "&lt;")
        .replace(/>/g, "&gt;")
        .replace(/"/g, "&quot;")
        .replace(/'/g, "&#39;");
}

function platformErrorMessage(error: unknown): string {
    return error instanceof Error ? error.message : String(error);
}
