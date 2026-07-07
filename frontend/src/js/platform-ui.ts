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
        bindCustomProviderEvents();
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
    bindPlatformApiFormatToggle(platform.platform);
    bindPlatformSave(platform);

    new bootstrap.Modal(modalElement, { backdrop: false }).show();
}

function buildPlatformConfigHTML(platform: AIPlatformConfig): string {
    return `
        <div class="api-config">
            <div class="form-group">
                <label for="modal-api-format-${platformEscapeHtml(platform.platform)}">接口规范 ${helpIcon("选择这个提供商遵循的接口格式。AnythingLLM 使用 /api/v1/workspace/{slug}/chat。")}</label>
                <select class="form-select api-format-input" id="modal-api-format-${platformEscapeHtml(platform.platform)}">
                    ${buildApiFormatOptions(platform.api_format || "openai")}
                </select>
            </div>
            <h6>API 配置</h6>
            <div class="form-group">
                <label for="modal-api-key-${platformEscapeHtml(platform.platform)}">API Key ${helpIcon("填写服务商的访问令牌。AnythingLLM 可在实例的 API Key 设置中生成。")}</label>
                <div class="password-input-group">
                    <input type="password" class="form-control api-key-input" id="modal-api-key-${platformEscapeHtml(platform.platform)}" value="${platformEscapeHtml(platform.config.api_key || "")}" placeholder="填写服务商 API Key">
                    <span class="password-toggle" data-target="modal-api-key-${platformEscapeHtml(platform.platform)}"><i class="bi bi-eye"></i></span>
                </div>
            </div>
            <div class="form-group mt-2">
                <label for="modal-base-url-${platformEscapeHtml(platform.platform)}">Base URL ${helpIcon("填写接口根地址。AnythingLLM 填 http://localhost:3001/api/v1；OpenAI 兼容接口通常填 https://host/v1。")}</label>
                <input type="text" class="form-control base-url-input" id="modal-base-url-${platformEscapeHtml(platform.platform)}" value="${platformEscapeHtml(platform.config.base_url)}" placeholder="例如 http://localhost:3001/api/v1">
            </div>
            <div class="form-group mt-2">
                <label for="modal-endpoint-url-${platformEscapeHtml(platform.platform)}">完整 Endpoint URL ${helpIcon("通常留空。只有服务商不是标准路径时才填写完整请求地址。")}</label>
                <input type="text" class="form-control endpoint-url-input" id="modal-endpoint-url-${platformEscapeHtml(platform.platform)}" value="${platformEscapeHtml(platform.config.endpoint_url || "")}" placeholder="通常留空，按接口规范自动生成">
            </div>
            <div class="form-group mt-2 anythingllm-provider-config">
                <label for="modal-anythingllm-workspace-${platformEscapeHtml(platform.platform)}">AnythingLLM Workspace Slug ${helpIcon("填写 AnythingLLM 工作区 URL 里的 slug。例如工作区地址是 /workspace/my-room，则填写 my-room。")}</label>
                <input type="text" class="form-control anythingllm-workspace-input" id="modal-anythingllm-workspace-${platformEscapeHtml(platform.platform)}" value="${platformEscapeHtml(platform.config.workspace_slug || "")}" placeholder="例如 my-workspace">
            </div>
            <div class="form-group mt-2 anythingllm-provider-config">
                <label for="modal-anythingllm-mode-${platformEscapeHtml(platform.platform)}">AnythingLLM 对话模式 ${helpIcon("chat 使用工作区文档和滚动历史；query 只在检索到相关资料时回答；automatic 允许 AnythingLLM 自动选择能力。")}</label>
                <select class="form-select anythingllm-mode-input" id="modal-anythingllm-mode-${platformEscapeHtml(platform.platform)}">
                    ${buildAnythingLLMModeOptions(platform.config.anythingllm_mode || "chat")}
                </select>
            </div>
            <div class="form-group mt-2 anythingllm-provider-config">
                <label for="modal-anythingllm-session-${platformEscapeHtml(platform.platform)}">AnythingLLM Session ID ${helpIcon("可留空。填写后 AnythingLLM 会用它区分 API 会话历史，例如 room-1-kp。")}</label>
                <input type="text" class="form-control anythingllm-session-input" id="modal-anythingllm-session-${platformEscapeHtml(platform.platform)}" value="${platformEscapeHtml(platform.config.session_id || "")}" placeholder="可留空；例如 room-1-kp">
            </div>
            <div class="form-group mt-2 custom-provider-config">
                <label for="modal-custom-response-path-${platformEscapeHtml(platform.platform)}">自定义响应文本路径 ${helpIcon("填写响应 JSON 中助手文本的位置，例如 choices.0.message.content 或 textResponse。")}</label>
                <input type="text" class="form-control custom-response-path-input" id="modal-custom-response-path-${platformEscapeHtml(platform.platform)}" value="${platformEscapeHtml(platform.custom?.response_path || "")}" placeholder="choices.0.message.content">
            </div>
            <div class="form-group mt-2 custom-provider-config">
                <label for="modal-custom-request-template-${platformEscapeHtml(platform.platform)}">自定义请求 Body 模板 JSON ${helpIcon("填写请求体 JSON。支持 {{model}}、{{last_user_message}}、{{messages}} 占位符。")}</label>
                <textarea class="form-control provider-code-input custom-request-template-input" id="modal-custom-request-template-${platformEscapeHtml(platform.platform)}" rows="6" spellcheck="false">${platformEscapeHtml(JSON.stringify(platform.custom?.request_template || {}, null, 2))}</textarea>
            </div>
            <div class="form-group mt-2">
                <label for="modal-timeout-${platformEscapeHtml(platform.platform)}">超时设置 (${platform.config.timeout} 秒) ${helpIcon("请求等待秒数。网络慢或本地模型响应慢时可调大。")}</label>
                <input type="range" class="form-range timeout-slider" id="modal-timeout-${platformEscapeHtml(platform.platform)}" min="10" max="60" step="5" value="${platform.config.timeout}" data-platform="${platformEscapeHtml(platform.platform)}">
                <div class="timeout-value" id="modal-timeout-value-${platformEscapeHtml(platform.platform)}">${platform.config.timeout} 秒</div>
            </div>
        </div>
        ${platform.platform === "lmstudio" ? buildLMStudioHelp(platform) : buildModelList(platform)}
    `;
}

function buildApiFormatOptions(selectedFormat: string): string {
    return [
        ["openai", "OpenAI"],
        ["anthropic", "Anthropic"],
        ["anythingllm", "AnythingLLM"],
        ["custom", "自定义请求"],
    ].map(([value, label]) => {
        const selected = value === selectedFormat ? "selected" : "";
        return `<option value="${value}" ${selected}>${label}</option>`;
    }).join("");
}

function buildAnythingLLMModeOptions(selectedMode: string): string {
    return ["chat", "query", "automatic"].map((mode) => {
        const selected = mode === selectedMode ? "selected" : "";
        return `<option value="${mode}" ${selected}>${mode}</option>`;
    }).join("");
}

function helpIcon(text: string): string {
    return `<span class="field-help" tabindex="0" title="${platformEscapeHtml(text)}">?</span>`;
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

function bindPlatformApiFormatToggle(platformName: string): void {
    const select = document.getElementById(`modal-api-format-${platformName}`) as HTMLSelectElement | null;
    const sync = () => {
        const isCustom = select?.value === "custom";
        const isAnythingLLM = select?.value === "anythingllm";
        document.querySelectorAll<HTMLElement>(".custom-provider-config").forEach((element) => {
            element.classList.toggle("d-none", !isCustom);
        });
        document.querySelectorAll<HTMLElement>(".anythingllm-provider-config").forEach((element) => {
            element.classList.toggle("d-none", !isAnythingLLM);
        });
    };
    select?.addEventListener("change", sync);
    sync();
}

function bindPlatformSave(platform: AIPlatformConfig): void {
    const saveButton = document.getElementById("savePlatformConfigBtn");
    if (!saveButton) return;
    saveButton.onclick = async () => {
        const apiFormat = document.getElementById(`modal-api-format-${platform.platform}`) as HTMLSelectElement | null;
        const apiKey = document.getElementById(`modal-api-key-${platform.platform}`) as HTMLInputElement | null;
        const baseUrl = document.getElementById(`modal-base-url-${platform.platform}`) as HTMLInputElement | null;
        const endpointUrl = document.getElementById(`modal-endpoint-url-${platform.platform}`) as HTMLInputElement | null;
        const anythingllmWorkspace = document.getElementById(`modal-anythingllm-workspace-${platform.platform}`) as HTMLInputElement | null;
        const anythingllmMode = document.getElementById(`modal-anythingllm-mode-${platform.platform}`) as HTMLSelectElement | null;
        const anythingllmSession = document.getElementById(`modal-anythingllm-session-${platform.platform}`) as HTMLInputElement | null;
        const responsePath = document.getElementById(`modal-custom-response-path-${platform.platform}`) as HTMLInputElement | null;
        const requestTemplate = document.getElementById(`modal-custom-request-template-${platform.platform}`) as HTMLTextAreaElement | null;
        const timeout = document.getElementById(`modal-timeout-${platform.platform}`) as HTMLInputElement | null;
        if (!apiFormat || !apiKey || !baseUrl || !endpointUrl || !timeout) return;

        platform.api_format = apiFormat.value as NonNullable<AIPlatformConfig["api_format"]>;
        platform.config.api_key = apiKey.value.trim();
        platform.config.base_url = baseUrl.value.trim();
        if (endpointUrl.value.trim()) {
            platform.config.endpoint_url = endpointUrl.value.trim();
        } else {
            delete platform.config.endpoint_url;
        }
        platform.config.timeout = Number.parseInt(timeout.value, 10);
        if (platform.api_format === "custom") {
            try {
                platform.custom = {
                    request_template: parseOptionalJsonObject(requestTemplate?.value || "{}"),
                    response_path: responsePath?.value.trim() || "choices.0.message.content",
                };
            } catch (error) {
                alert(`自定义请求 JSON 无效: ${platformErrorMessage(error)}`);
                return;
            }
        }
        if (platform.api_format === "anythingllm") {
            platform.config.workspace_slug = anythingllmWorkspace?.value.trim() || "";
            platform.config.anythingllm_mode = anythingllmMode?.value || "chat";
            platform.config.session_id = anythingllmSession?.value.trim() || "";
        }
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

function bindCustomProviderEvents(): void {
    const openButton = document.getElementById("addProviderOpenBtn") as HTMLButtonElement | null;
    if (openButton && openButton.dataset.bound !== "true") {
        openButton.dataset.bound = "true";
        openButton.addEventListener("click", () => {
            resetAddProviderForm();
            const modalElement = document.getElementById("addProviderModal");
            if (modalElement) new bootstrap.Modal(modalElement).show();
        });
    }

    ["providerName", "providerId", "providerBaseUrl", "providerModelName", "providerModelId", "providerWorkspaceSlug", "providerResponsePath"].forEach((id) => {
        document.getElementById(id)?.addEventListener("input", validateAddProviderForm);
    });

    document.getElementById("providerName")?.addEventListener("input", () => {
        const idInput = document.getElementById("providerId") as HTMLInputElement | null;
        if (idInput && !idInput.value.trim()) idInput.value = slugifyProviderId(formValue("providerName"));
        validateAddProviderForm();
    });

    document.getElementById("providerApiFormat")?.addEventListener("change", () => {
        syncProviderCustomFields();
        validateAddProviderForm();
    });

    const addButton = document.getElementById("addProviderBtn") as HTMLButtonElement | null;
    if (addButton && addButton.dataset.bound !== "true") {
        addButton.dataset.bound = "true";
        addButton.addEventListener("click", async () => {
            try {
                const provider = buildCustomProviderConfig();
                const success = await aiPlatformManager.savePlatformConfig(provider.platform, provider);
                if (!success) {
                    setAddProviderMessage("提供商保存失败", true);
                    return;
                }
                bootstrap.Modal.getInstance(document.getElementById("addProviderModal"))?.hide();
                renderPlatforms(await aiPlatformManager.loadPlatforms());
                await loadRoleConfigs();
                showNotification("大模型提供商已添加", "success");
            } catch (error) {
                setAddProviderMessage(platformErrorMessage(error), true);
            }
        });
    }
}

function resetAddProviderForm(): void {
    [
        "providerName",
        "providerId",
        "providerApiKey",
        "providerBaseUrl",
        "providerEndpointUrl",
        "providerModelName",
        "providerModelId",
        "providerWorkspaceSlug",
        "providerHeadersJson",
        "providerRequestTemplate",
        "providerResponsePath",
    ].forEach((id) => setFormValue(id, ""));
    setFormValue("providerTimeout", "30");
    const apiFormat = document.getElementById("providerApiFormat") as HTMLSelectElement | null;
    if (apiFormat) apiFormat.value = "openai";
    setAddProviderMessage("");
    syncProviderCustomFields();
    validateAddProviderForm();
}

function syncProviderCustomFields(): void {
    const isCustom = formValue("providerApiFormat") === "custom";
    const isAnythingLLM = formValue("providerApiFormat") === "anythingllm";
    document.querySelectorAll<HTMLElement>(".provider-custom-field").forEach((element) => {
        element.classList.toggle("d-none", !isCustom);
    });
    document.querySelectorAll<HTMLElement>(".provider-anythingllm-field").forEach((element) => {
        element.classList.toggle("d-none", !isAnythingLLM);
    });
    if (isCustom && !formValue("providerRequestTemplate").trim()) {
        setFormValue("providerRequestTemplate", JSON.stringify({
            model: "{{model}}",
            prompt: "{{last_user_message}}",
            messages: "{{messages}}",
        }, null, 2));
        setFormValue("providerResponsePath", "choices.0.message.content");
    }
}

function validateAddProviderForm(): void {
    const required = [
        formValue("providerName").trim(),
        formValue("providerId").trim(),
        formValue("providerBaseUrl").trim(),
        formValue("providerModelName").trim(),
        formValue("providerModelId").trim(),
    ];
    const isCustom = formValue("providerApiFormat") === "custom";
    const isAnythingLLM = formValue("providerApiFormat") === "anythingllm";
    const customReady = !isCustom || Boolean(formValue("providerRequestTemplate").trim() && formValue("providerResponsePath").trim());
    const anythingllmReady = !isAnythingLLM || Boolean(formValue("providerWorkspaceSlug").trim());
    setDisabled("addProviderBtn", required.some((value) => !value) || !customReady || !anythingllmReady);
}

function buildCustomProviderConfig(): AIPlatformConfig {
    const platformId = slugifyProviderId(formValue("providerId"));
    if (!platformId) throw new Error("提供商 ID 不能为空");
    const apiFormat = (formValue("providerApiFormat") || "openai") as NonNullable<AIPlatformConfig["api_format"]>;
    const headers = parseOptionalJsonObject(formValue("providerHeadersJson") || "{}") as Record<string, string>;
    const config: AIPlatformConfig = {
        platform: platformId,
        name: formValue("providerName").trim(),
        description: apiFormat === "anythingllm" ? "AnythingLLM 原生 Workspace Chat API" : "用户自定义大模型提供商",
        icon: apiFormat === "anythingllm" ? "/assets/aiplatform/anythingllm.png" : "/assets/aiplatform/lmstudio.png",
        enabled: true,
        api_format: apiFormat,
        config: {
            api_key: formValue("providerApiKey").trim(),
            base_url: formValue("providerBaseUrl").trim(),
            timeout: Number.parseInt(formValue("providerTimeout") || "30", 10),
            headers,
        },
        models: [
            {
                id: formValue("providerModelId").trim(),
                name: formValue("providerModelName").trim(),
                description: "默认模型",
                enabled: true,
                params: {
                    context_window: 8192,
                    temperature: 0.7,
                    top_p: 0.95,
                    max_tokens: 4096,
                },
            },
        ],
    };
    const endpointUrl = formValue("providerEndpointUrl").trim();
    if (endpointUrl) config.config.endpoint_url = endpointUrl;

    if (apiFormat === "anthropic") {
        config.config.anthropic_version = "2023-06-01";
    }
    if (apiFormat === "anythingllm") {
        config.config.workspace_slug = formValue("providerWorkspaceSlug").trim();
        config.config.anythingllm_mode = "chat";
        config.config.session_id = "";
    }
    if (apiFormat === "custom") {
        config.custom = {
            request_template: parseOptionalJsonObject(formValue("providerRequestTemplate")),
            response_path: formValue("providerResponsePath").trim(),
        };
    }
    return config;
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

function setAddProviderMessage(message: string, isError = false): void {
    const element = document.getElementById("addProviderMessage");
    if (!element) return;
    element.textContent = message;
    element.classList.toggle("error", isError);
    element.classList.toggle("success", Boolean(message && !isError));
}

function slugifyProviderId(value: string): string {
    return value
        .trim()
        .toLowerCase()
        .replace(/[^a-z0-9_-]+/g, "-")
        .replace(/^-+|-+$/g, "");
}

function parseOptionalJsonObject(value: string): Record<string, unknown> {
    const text = value.trim();
    if (!text) return {};
    const parsed = JSON.parse(text) as unknown;
    if (!parsed || typeof parsed !== "object" || Array.isArray(parsed)) {
        throw new Error("JSON 必须是对象");
    }
    return parsed as Record<string, unknown>;
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
