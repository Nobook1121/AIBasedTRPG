let toolManager: ToolManager | null = null;

document.addEventListener("DOMContentLoaded", () => {
    void initializeApplication();
});

async function initializeApplication(): Promise<void> {
    const dom = window.TrpgDom;
    window.TrpgI18n?.apply();

    toolManager = new ToolManager();
    window.toolManager = toolManager;

    initTabs();
    initScenarioManagement();
    initDiceTool();
    initToolTabs();
    initSettingsTabs();

    await loadAndApplyConfigs();

    await initAIPlatforms();
    await initAuth();
    initCharacterManagement();
    initChat();
    await initNetworkConfig();
    initRoomManagement();
    initSidebarToggle();

    await autoLoadLastRoom();

    dom.on(document, "hidden.bs.modal", () => {
        setTimeout(() => {
            if (dom.removeModalBackdropsWhenIdle()) {
                console.log("所有模态框已关闭，已移除所有遮罩层");
            } else {
                console.log("还有其他模态框打开，保留遮罩层");
            }
        }, 100);
    });
}

async function loadAndApplyConfigs(): Promise<void> {
    try {
        await configManager.loadConfig("general");
        configManager.applyGeneralSettings();
        configManager.initThemeSystem();
        console.log("配置文件加载和应用完成");
    } catch (error) {
        console.error("加载配置文件时出错:", error);
    }
}

function initCharacterManagement(): void {
    window.COC7CharacterSheet?.initCharacterSheet();
}

function initDiceTool(): void {
    const rollDiceBtn = document.getElementById("rollDice");
    const diceType = document.getElementById("diceType") as HTMLSelectElement | null;
    const diceResult = document.getElementById("diceResult");
    if (!rollDiceBtn || !diceType || !diceResult) return;

    rollDiceBtn.addEventListener("click", () => {
        const sides = Number.parseInt(diceType.value.replace("d", ""), 10);
        if (!Number.isFinite(sides) || sides <= 0) return;
        const result = Math.floor(Math.random() * sides) + 1;
        diceResult.textContent = `结果: ${result}`;
    });
}

function initSidebarToggle(): void {
    const dom = window.TrpgDom;
    const toggleBtn = dom.byId("sidebarToggle");
    const sidebar = dom.byId("sidebar");
    const mainContent = dom.byId("mainContent");

    if (!toggleBtn || !sidebar || !mainContent) return;

    function setSidebarExpanded(isExpanded: boolean): void {
        sidebar?.classList.toggle("sidebar-expanded", isExpanded);
        sidebar?.classList.toggle("sidebar-collapsed", !isExpanded);
        mainContent?.classList.toggle("sidebar-collapsed-content", !isExpanded);
        dom.setButtonDisclosure(toggleBtn, {
            expanded: isExpanded,
            expandedLabel: "收起侧边栏",
            collapsedLabel: "展开侧边栏",
            expandedIconClass: "fa fa-angle-double-left",
            collapsedIconClass: "fa fa-angle-double-right",
        });
    }

    dom.on(toggleBtn, "click", () => {
        const isCollapsed = sidebar.classList.contains("sidebar-collapsed");
        setSidebarExpanded(isCollapsed);
    });
}
