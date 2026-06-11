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
}

function isConfigObject(value: unknown): value is TomlConfig {
    return typeof value === "object" && value !== null && !Array.isArray(value);
}
