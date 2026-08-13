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

function updateNavigationState(activeLink: HTMLAnchorElement | null, navLinks: HTMLAnchorElement[]): void {
    navLinks.forEach((link) => {
        if (link === activeLink) {
            link.setAttribute("aria-current", "page");
        } else {
            link.removeAttribute("aria-current");
        }
    });
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
        themeSelect.addEventListener("change", async () => {
            const generalConfig = configManager.getConfig("general");
            const appearance = isConfigObject(generalConfig.appearance) ? generalConfig.appearance : {};
            appearance.theme = themeSelect.value;
            generalConfig.appearance = appearance;
            await configManager.saveConfig("general", generalConfig);
            configManager.applyTheme();
        });
    }

    bindGeneralCheckboxSetting("streamOutput", "ai", "stream_output");
    document.getElementById("savePermissionConfig")?.addEventListener("click", () => {
        void savePermissionConfig();
    });
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
