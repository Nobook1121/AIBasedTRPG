interface AdminUserRecord {
    id: number;
    username: string;
    email: string;
    role: string;
    status: string;
    is_online?: boolean;
    presence?: string;
    created_at?: string;
    last_login?: string;
}

function initTabs(): void {
    try {
        const navLinks = Array.from(document.querySelectorAll<HTMLAnchorElement>("#sidebar .nav-link"));
        const tabContents = Array.from(document.querySelectorAll<HTMLElement>(".tab-content"));

        if (navLinks.length === 0 || tabContents.length === 0) {
            console.error("无法找到导航链接或标签内容");
            return;
        }

        updateNavigationState(document.querySelector<HTMLAnchorElement>("#sidebar .nav-link.active"), navLinks);

        navLinks.forEach((link) => {
            link.addEventListener("click", (event) => {
                event.preventDefault();
                handleMainNavigationClick(link, navLinks, tabContents);
            });
        });

        bindDropdownButtons();
        refreshAdminNavigation();
        console.log("标签切换初始化成功");
    } catch (error) {
        console.error("初始化标签切换时出错:", error);
    }
}

function handleMainNavigationClick(
    link: HTMLAnchorElement,
    navLinks: HTMLAnchorElement[],
    tabContents: HTMLElement[],
): void {
    const isInDropdown = Boolean(link.closest(".dropdown-container"));
    if (!isInDropdown) {
        closeDropdownButtons();
    }

    navLinks.forEach((item) => item.classList.remove("active"));
    tabContents.forEach((tab) => tab.classList.remove("active"));

    link.classList.add("active");
    updateNavigationState(link, navLinks);

    const tabId = link.dataset.tab;
    if (!tabId) {
        console.error("导航链接缺少 data-tab 属性");
        return;
    }

    const targetTab = document.getElementById(tabId);
    if (!targetTab) {
        console.error(`找不到 id 为 ${tabId} 的标签内容`);
        return;
    }

    targetTab.classList.add("active");
    console.log(`切换到标签页: ${tabId}`);

    if (tabId === "settings") {
        const settingsTab = link.hash.replace("#", "").replace("settings-", "");
        if (settingsTab) switchSettingsTab(settingsTab);
    }

    if (tabId === "tools") {
        const toolsTab = link.hash.replace("#", "");
        if (toolsTab === "tools-dice") switchToolTab("dice");
    }
}

function switchMainTab(tabId: string, options: { clearNav?: boolean } = {}): void {
    const navLinks = Array.from(document.querySelectorAll<HTMLAnchorElement>("#sidebar .nav-link"));
    const tabContents = Array.from(document.querySelectorAll<HTMLElement>(".tab-content"));
    tabContents.forEach((tab) => tab.classList.remove("active"));
    const targetTab = document.getElementById(tabId);
    if (!targetTab) {
        console.error(`找不到 id 为 ${tabId} 的标签内容`);
        return;
    }
    targetTab.classList.add("active");

    navLinks.forEach((item) => item.classList.remove("active"));
    if (!options.clearNav) {
        const activeLink = navLinks.find((link) => link.dataset.tab === tabId);
        activeLink?.classList.add("active");
        updateNavigationState(activeLink || null, navLinks);
    } else {
        updateNavigationState(null, navLinks);
    }
    refreshMainTabData(tabId);
}

function refreshAdminNavigation(): void {
    const role = window.currentUser?.role || "USER";
    const canSeeAdmin = role === "ADMIN" || role === "OWNER";
    document.querySelectorAll<HTMLElement>("[data-admin-only='true']").forEach((element) => {
        element.hidden = !canSeeAdmin;
    });
}

function updateNavigationState(activeLink: HTMLAnchorElement | null, navLinks: HTMLAnchorElement[]): void {
    navLinks.forEach((link) => {
        if (link === activeLink) {
            link.setAttribute("aria-current", "page");
        } else {
            link.removeAttribute("aria-current");
        }
    });
}

function refreshMainTabData(tabId: string): void {
    if (tabId === "save") {
        void window.loadRoomsList?.();
    }
}

function bindDropdownButtons(): void {
    document.querySelectorAll<HTMLElement>(".dropdown-btn").forEach((button) => {
        button.setAttribute("aria-expanded", button.classList.contains("active") ? "true" : "false");
        button.addEventListener("click", () => {
            const dropdownContent = button.nextElementSibling as HTMLElement | null;
            if (!dropdownContent) return;

            const isExpanded = dropdownContent.style.display !== "block";
            button.classList.toggle("active", isExpanded);
            button.setAttribute("aria-expanded", String(isExpanded));
            dropdownContent.style.display = isExpanded ? "block" : "none";

            document.querySelectorAll<HTMLElement>(".dropdown-btn").forEach((otherButton) => {
                if (otherButton === button) return;
                otherButton.classList.remove("active");
                otherButton.setAttribute("aria-expanded", "false");
                const otherContent = otherButton.nextElementSibling as HTMLElement | null;
                if (otherContent) otherContent.style.display = "none";
            });
        });
    });
}

function closeDropdownButtons(): void {
    document.querySelectorAll<HTMLElement>(".dropdown-btn").forEach((button) => {
        button.classList.remove("active");
        const dropdownContent = button.nextElementSibling as HTMLElement | null;
        if (dropdownContent) dropdownContent.style.display = "none";
    });
}

function switchSettingsTab(tabName: string): void {
    const settingsTabs = document.querySelectorAll<HTMLElement>(".settings-tab");
    const settingsContents = document.querySelectorAll<HTMLElement>(".settings-content");

    settingsTabs.forEach((tab) => {
        tab.classList.remove("active");
        tab.setAttribute("aria-selected", "false");
    });
    settingsContents.forEach((content) => content.classList.remove("active"));

    const targetTab = document.querySelector<HTMLElement>(`.settings-tab[data-settings="${CSS.escape(tabName)}"]`);
    const targetContent = document.getElementById(`${tabName}-settings-content`);
    targetTab?.classList.add("active");
    targetTab?.setAttribute("aria-selected", "true");
    targetContent?.classList.add("active");
    if (tabName === "permissions") {
        void loadPermissionConfig();
    }
    if (tabName === "users") {
        void loadUserManagement();
    }
}

function switchToolTab(toolName: string): void {
    const toolTabs = document.querySelectorAll<HTMLElement>(".tool-tab");
    const toolContents = document.querySelectorAll<HTMLElement>(".tool-content");

    toolTabs.forEach((tab) => {
        tab.classList.remove("active");
        tab.setAttribute("aria-selected", "false");
    });
    toolContents.forEach((content) => content.classList.remove("active"));

    const targetTab = document.querySelector<HTMLElement>(`.tool-tab[data-tool="${CSS.escape(toolName)}"]`);
    const targetContent = document.getElementById(`${toolName}-tool-content`);
    targetTab?.classList.add("active");
    targetTab?.setAttribute("aria-selected", "true");
    targetContent?.classList.add("active");
}

function initToolTabs(): void {
    const toolTabs = document.querySelectorAll<HTMLElement>(".tool-tab");
    const toolContents = document.querySelectorAll<HTMLElement>(".tool-content");
    if (toolTabs.length === 0 || toolContents.length === 0) {
        console.error("无法找到工具标签或工具内容");
        return;
    }

    toolTabs.forEach((tab) => {
        tab.setAttribute("role", "tab");
        tab.setAttribute("aria-selected", tab.classList.contains("active") ? "true" : "false");
        tab.addEventListener("click", () => switchToolTab(tab.dataset.tool || ""));
    });
}

function initSettingsTabs(): void {
    const settingsTabs = document.querySelectorAll<HTMLElement>(".settings-tab");
    const settingsContents = document.querySelectorAll<HTMLElement>(".settings-content");
    if (settingsTabs.length === 0 || settingsContents.length === 0) {
        console.error("无法找到设置标签或设置内容");
        return;
    }

    settingsTabs.forEach((tab) => {
        tab.setAttribute("role", "tab");
        tab.setAttribute("aria-selected", tab.classList.contains("active") ? "true" : "false");
        tab.addEventListener("click", () => switchSettingsTab(tab.dataset.settings || ""));
    });

    const temperatureSlider = document.getElementById("temperature") as HTMLInputElement | null;
    const temperatureValue = document.getElementById("temperatureValue");
    if (temperatureSlider && temperatureValue) {
        temperatureSlider.addEventListener("input", () => {
            temperatureValue.textContent = temperatureSlider.value;
        });
    }

    const themeSelect = document.getElementById("themeSelect") as HTMLSelectElement | null;
    if (themeSelect) {
        themeSelect.dataset.savedValue = themeSelect.value;
        themeSelect.addEventListener("change", () => updateDefaultThemePendingState());
    }
    document.getElementById("saveDefaultThemeChange")?.addEventListener("click", () => {
        void saveDefaultThemeChange();
    });
    document.getElementById("cancelDefaultThemeChange")?.addEventListener("click", cancelDefaultThemeChange);
    window.addEventListener("trpg:locale-changed", () => {
        const generalConfig = configManager.getConfig("general");
        const language = isConfigObject(generalConfig.language) ? generalConfig.language : {};
        language.language = window.TrpgI18n?.getLocale() === "en_us" ? "en-US" : "zh-CN";
        generalConfig.language = language;
        void configManager.saveConfig("general", generalConfig);
    });

    bindGeneralCheckboxSetting("streamOutput", "ai", "stream_output");
    bindGeneralCheckboxSetting("scenarioImportStreamOutput", "scenario_import", "stream_output");
    bindGeneralCheckboxSetting("debugMode", "ai", "debug_mode");
    bindGeneralCheckboxSetting("showAIHints", "ai", "show_ai_hints");
    bindGeneralNumberSetting("autosaveInterval", "autosave", "interval", 30, 3600);
    bindGeneralNumberSetting("autosaveMaxNodes", "autosave", "max_nodes", 1, 50);
    bindGeneralNumberSetting("triggerMaxFileSize", "scenario", "trigger_max_file_size", 1024, 52428800);
    document.getElementById("savePermissionConfig")?.addEventListener("click", () => {
        void savePermissionConfig();
    });
    document.getElementById("refreshUserManagement")?.addEventListener("click", () => {
        void loadUserManagement(true);
    });
    document.getElementById("refreshAITokenDashboard")?.addEventListener("click", () => {
        void loadAITokenDashboard();
    });
    void loadAITokenDashboard();
}

async function loadAITokenDashboard(): Promise<void> {
    const body = document.getElementById("aiTokenDashboardBody");
    const dateLabel = document.getElementById("aiTokenDashboardDate");
    if (!body) return;
    try {
        const response = await TrpgApi.get<ApiResponse<{ day: string; roles: Record<string, { request_count?: number; prompt_tokens?: number; completion_tokens?: number; total_tokens?: number; cache_hit_rate?: number }> }>>("/api/telemetry/ai/daily");
        if (!response.success || !response.data) throw new Error(response.message || "无法加载 Token 用量");
        if (dateLabel) dateLabel.textContent = `日期：${response.data.day}`;
        const entries = Object.entries(response.data.roles || {});
        body.innerHTML = entries.length ? entries.map(([role, usage]) => `<tr><td>${settingsEscapeHtml(role)}</td><td>${usage.request_count || 0}</td><td>${usage.prompt_tokens || 0}</td><td>${usage.completion_tokens || 0}</td><td>${usage.total_tokens || 0}</td><td>${usage.cache_hit_rate || 0}%</td></tr>`).join("") : '<tr><td colspan="6" class="text-muted">暂无用量记录</td></tr>';
    } catch (error) {
        body.innerHTML = `<tr><td colspan="6" class="text-danger">${settingsEscapeHtml(settingsErrorMessage(error))}</td></tr>`;
    }
}

function bindGeneralCheckboxSetting(elementId: string, sectionName: string, key: string): void {
    const input = document.getElementById(elementId) as HTMLInputElement | null;
    if (!input) return;
    input.addEventListener("change", async () => {
        const generalConfig = configManager.getConfig("general");
        const section = isConfigObject(generalConfig[sectionName]) ? generalConfig[sectionName] : {};
        section[key] = input.checked;
        generalConfig[sectionName] = section;
        await configManager.saveConfig("general", generalConfig);
    });
}

function isConfigObject(value: unknown): value is TomlConfig {
    return typeof value === "object" && value !== null && !Array.isArray(value);
}

function bindGeneralNumberSetting(elementId: string, sectionName: string, key: string, minimum: number, maximum: number): void {
    const input = document.getElementById(elementId) as HTMLInputElement | null;
    if (!input) return;
    input.addEventListener("change", async () => {
        const value = Math.max(minimum, Math.min(maximum, Number.parseInt(input.value || "0", 10) || minimum));
        input.value = String(value);
        const generalConfig = configManager.getConfig("general");
        const section = isConfigObject(generalConfig[sectionName]) ? generalConfig[sectionName] : {};
        section[key] = value;
        generalConfig[sectionName] = section;
        await configManager.saveConfig("general", generalConfig);
    });
}

function updateDefaultThemePendingState(): void {
    const themeSelect = document.getElementById("themeSelect") as HTMLSelectElement | null;
    const pendingBar = document.getElementById("defaultThemePendingSaveBar");
    const count = document.getElementById("defaultThemePendingChangeCount");
    const themeSetting = themeSelect?.closest<HTMLElement>(".form-group");
    if (!themeSelect || !pendingBar || !count) return;

    const isDirty = themeSelect.value !== (themeSelect.dataset.savedValue || "");
    pendingBar.hidden = !isDirty;
    count.textContent = isDirty ? "1" : "0";
    themeSetting?.classList.toggle("setting-dirty", isDirty);
}

async function saveDefaultThemeChange(): Promise<void> {
    const themeSelect = document.getElementById("themeSelect") as HTMLSelectElement | null;
    if (!themeSelect) return;

    const generalConfig = configManager.getConfig("general");
    const appearance = isConfigObject(generalConfig.appearance) ? generalConfig.appearance : {};
    appearance.theme = themeSelect.value;
    generalConfig.appearance = appearance;
    if (await configManager.saveConfig("general", generalConfig)) {
        themeSelect.dataset.savedValue = themeSelect.value;
        updateDefaultThemePendingState();
        configManager.applyTheme();
    }
}

function cancelDefaultThemeChange(): void {
    const themeSelect = document.getElementById("themeSelect") as HTMLSelectElement | null;
    if (!themeSelect) return;
    themeSelect.value = themeSelect.dataset.savedValue || "light";
    updateDefaultThemePendingState();
}

async function loadPermissionConfig(): Promise<void> {
    const matrix = document.getElementById("permissionMatrix");
    if (!matrix || matrix.dataset.loaded === "true") return;
    matrix.textContent = "正在加载权限配置...";

    try {
        const response = await TrpgApi.get<ApiResponse<PermissionConfig>>("/api/config/permissions");
        if (!response.success || !response.data) {
            throw new Error(response.message || response.error || "权限配置加载失败");
        }
        renderPermissionMatrix(response.data);
    } catch (error) {
        matrix.textContent = settingsErrorMessage(error);
    }
}

async function loadUserManagement(forceReload = false): Promise<void> {
    const list = document.getElementById("userManagementList");
    const message = document.getElementById("userManagementMessage");
    if (!list) return;
    if (!forceReload && list.dataset.loaded === "true") return;

    list.innerHTML = `<tr><td colspan="8" class="text-muted">正在加载用户信息...</td></tr>`;
    if (message) {
        message.textContent = "";
        message.className = "settings-message";
    }

    try {
        const response = await TrpgApi.get<ApiResponse<AdminUserRecord[]>>("/api/users");
        if (!response.success || !response.data) {
            throw new Error(response.message || response.error || "用户信息加载失败");
        }
        renderUserManagementList(response.data);
        list.dataset.loaded = "true";
        if (message) {
            message.textContent = `已加载 ${response.data.length} 名用户`;
            message.className = "settings-message success";
        }
    } catch (error) {
        list.innerHTML = `<tr><td colspan="8" class="text-muted">${settingsEscapeHtml(settingsErrorMessage(error))}</td></tr>`;
        if (message) {
            message.textContent = settingsErrorMessage(error);
            message.className = "settings-message error";
        }
    }
}

function renderUserManagementList(users: AdminUserRecord[]): void {
    const list = document.getElementById("userManagementList");
    if (!list) return;
    if (!users.length) {
        list.innerHTML = `<tr><td colspan="8" class="text-muted">暂无用户</td></tr>`;
        return;
    }

    list.innerHTML = users.map((user) => renderUserManagementRow(user)).join("");
    list.querySelectorAll<HTMLButtonElement>("[data-impersonate-user-id]").forEach((button) => {
        button.addEventListener("click", () => void startImpersonation(Number.parseInt(button.dataset.impersonateUserId || "", 10)));
    });
}

function renderUserManagementRow(user: AdminUserRecord): string {
    const currentUserId = window.currentUser?.user_id;
    const isCurrentUser = String(currentUserId) === String(user.id);
    const canImpersonate = user.status === "active" && !isCurrentUser;
    return `
        <tr>
            <td>${settingsEscapeHtml(user.username)}</td>
            <td>${settingsEscapeHtml(user.email)}</td>
            <td>${settingsEscapeHtml(user.role)}</td>
            <td>${settingsEscapeHtml(user.status)}</td>
            <td>${settingsEscapeHtml(formatOnlineState(user.is_online))}</td>
            <td>${settingsEscapeHtml(formatTimestamp(user.created_at))}</td>
            <td>${settingsEscapeHtml(formatTimestamp(user.last_login))}</td>
            <td class="text-end">
                <div class="user-management-actions">
                    <button type="button" class="btn btn-sm btn-outline-primary" data-impersonate-user-id="${user.id}" ${canImpersonate ? "" : "disabled"}>
                        <i class="fa fa-user-secret" aria-hidden="true"></i> 模拟
                    </button>
                </div>
            </td>
        </tr>
    `;
}

async function startImpersonation(userId: number): Promise<void> {
    if (!Number.isFinite(userId)) return;
    try {
        const response = await TrpgApi.post<ApiResponse<unknown>>("/api/auth/impersonation/start", { user_id: userId });
        if (!response.success) {
            throw new Error(response.message || response.error || "模拟登录失败");
        }
        window.location.reload();
    } catch (error) {
        const message = settingsErrorMessage(error);
        const statusMessage = document.getElementById("userManagementMessage");
        if (statusMessage) {
            statusMessage.textContent = message;
            statusMessage.className = "settings-message error";
        }
    }
}

function formatOnlineState(isOnline?: boolean): string {
    return isOnline ? "在线" : "离线";
}

function formatTimestamp(value?: string): string {
    if (!value) return "-";
    const date = new Date(value);
    return Number.isNaN(date.getTime()) ? value : date.toLocaleString("zh-CN", { hour12: false });
}

function renderPermissionMatrix(config: PermissionConfig): void {
    const matrix = document.getElementById("permissionMatrix");
    if (!matrix) return;
    matrix.dataset.loaded = "true";
    matrix.dataset.roles = JSON.stringify(config.roles);
    matrix.innerHTML = config.groups.map((group) => renderPermissionGroup(group, config)).join("");
}

function renderPermissionGroup(group: PermissionGroup, config: PermissionConfig): string {
    const nodes = group.nodes.map((node) => renderPermissionNode(node, config)).join("");
    return `
        <section class="permission-group" data-permission-group="${settingsEscapeHtml(group.id)}">
            <div class="permission-group-header">
                <h5>${settingsEscapeHtml(group.label)}</h5>
                <p>${settingsEscapeHtml(group.description || "")}</p>
            </div>
            <div class="permission-node-list">${nodes}</div>
        </section>
    `;
}

function renderPermissionNode(node: PermissionNode, config: PermissionConfig): string {
    const allowedRoles = new Set(config.matrix[node.id] || []);
    const roleToggles = config.roles.map((role) => `
        <label class="permission-role-toggle">
            <input type="checkbox" data-permission-node="${settingsEscapeHtml(node.id)}" data-permission-role="${settingsEscapeHtml(role)}" ${allowedRoles.has(role) ? "checked" : ""}>
            <span>${settingsEscapeHtml(role)}</span>
        </label>
    `).join("");
    return `
        <article class="permission-node-card">
            <div>
                <strong>${settingsEscapeHtml(node.label)}</strong>
                <p>${settingsEscapeHtml(node.description || node.id)}</p>
            </div>
            <div class="permission-role-list">${roleToggles}</div>
        </article>
    `;
}

async function savePermissionConfig(): Promise<void> {
    const matrix = document.getElementById("permissionMatrix");
    const message = document.getElementById("permissionConfigMessage");
    if (!matrix) return;

    const nextMatrix: Record<string, string[]> = {};
    matrix.querySelectorAll<HTMLInputElement>("[data-permission-node][data-permission-role]").forEach((input) => {
        const node = input.dataset.permissionNode || "";
        const role = input.dataset.permissionRole || "";
        if (!node || !role || !input.checked) return;
        nextMatrix[node] = nextMatrix[node] || [];
        nextMatrix[node].push(role);
    });

    try {
        const response = await TrpgApi.post<ApiResponse<PermissionConfig>>("/api/config/permissions", { matrix: nextMatrix });
        if (!response.success || !response.data) {
            throw new Error(response.message || response.error || "权限配置保存失败");
        }
        renderPermissionMatrix(response.data);
        if (message) {
            message.textContent = "权限配置已保存";
            message.className = "settings-message success";
        }
    } catch (error) {
        if (message) {
            message.textContent = settingsErrorMessage(error);
            message.className = "settings-message error";
        }
    }
}

function settingsEscapeHtml(value: unknown): string {
    const element = document.createElement("div");
    element.textContent = String(value ?? "");
    return element.innerHTML;
}

function settingsErrorMessage(error: unknown): string {
    return error instanceof Error ? error.message : String(error);
}

window.switchMainTab = switchMainTab;
window.refreshAdminNavigation = refreshAdminNavigation;
