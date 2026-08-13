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
    initCommandToolPanels();
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

function initCommandToolPanels(): void {
    document.getElementById("submitCocCheck")?.addEventListener("click", submitCocCheck);
    document.getElementById("refreshRoomSnapshot")?.addEventListener("click", renderRoomSnapshotTool);
    document.getElementById("submitScenarioContext")?.addEventListener("click", () => {
        void submitScenarioContext();
    });
    document.getElementById("refreshCharacterCards")?.addEventListener("click", renderCharacterCardsTool);
    document.getElementById("submitRememberFact")?.addEventListener("click", submitRememberFact);
}

function submitCocCheck(): void {
    const player = toolInputValue("cocCheckPlayer");
    const name = toolInputValue("cocCheckName");
    const difficulty = toolInputValue("cocCheckDifficulty");
    const adjustment = toolInputValue("cocCheckAdjustment");
    const command = ["/check", player, name, difficulty, adjustment].filter(Boolean).join(" ");
    const result = window.toolManager?.handleCommand(command) || "工具管理器尚未初始化";
    setToolOutput("cocCheckResult", result);
}

function renderRoomSnapshotTool(): void {
    const room = window.currentRoom;
    if (!room) {
        setToolOutput("roomSnapshotResult", "当前没有加入房间。");
        return;
    }

    const activeMembers = (room.members || []).filter((member) => member.is_active !== false && member.status !== "removed");
    setToolOutput("roomSnapshotResult", JSON.stringify({
        room: {
            id: room.id,
            name: room.name,
            code: room.room_code || room.code,
            scenario_id: room.scenario_id,
            scenario_title: room.scenario_title,
        },
        members: activeMembers.map((member) => ({
            username: member.username,
            role: member.room_role || member.role,
            character: member.character_card?.name || null,
            state: member.character_state || null,
        })),
        message_count: room.messages?.length || 0,
    }, null, 2));
}

async function submitScenarioContext(): Promise<void> {
    const room = window.currentRoom;
    if (!room?.scenario_id) {
        setToolOutput("scenarioContextResult", "当前房间未绑定剧本。");
        return;
    }

    try {
        const response = await TrpgApi.get<ApiResponse<Scenario[]>>("/api/scenarios");
        const scenario = response.data?.find((item) => String(item.id) === String(room.scenario_id));
        if (!response.success || !scenario) {
            setToolOutput("scenarioContextResult", "未找到当前房间绑定剧本。");
            return;
        }

        const query = toolInputValue("scenarioContextQuery").toLowerCase();
        const limit = Math.max(1, Math.min(20, Number.parseInt(toolInputValue("scenarioContextLimit") || "5", 10) || 5));
        const sections = [
            ...((scenario.scenes || []).map((item) => ({ section: "scenes", ...item }))),
            ...((scenario.endings || []).map((item) => ({ section: "endings", ...item }))),
        ];
        const matches = sections.filter((item) => {
            if (!query) return true;
            return JSON.stringify(item).toLowerCase().includes(query);
        }).slice(0, limit);
        setToolOutput("scenarioContextResult", JSON.stringify({
            scenario: {
                id: scenario.id,
                title: scenario.title,
                notes: scenario.notes,
                background: scenario.background,
            },
            matches,
        }, null, 2));
    } catch (error) {
        setToolOutput("scenarioContextResult", `剧本检索失败: ${toolErrorMessage(error)}`);
    }
}

function renderCharacterCardsTool(): void {
    const room = window.currentRoom;
    if (!room) {
        setToolOutput("characterCardsResult", "当前没有加入房间。");
        return;
    }

    const members = (room.members || []).map((member) => ({
        username: member.username,
        active: member.is_active !== false && member.status !== "removed",
        character_card: member.character_card || null,
        character_state: member.character_state || null,
    }));
    setToolOutput("characterCardsResult", JSON.stringify({ members }, null, 2));
}

function submitRememberFact(): void {
    const content = toolInputValue("memoryContent");
    if (!content) {
        setToolOutput("memoryToolResult", "请先填写需要记录的内容。");
        return;
    }

    const roomKey = window.currentRoom?.id || "global";
    const storageKey = `trpg_room_memory_${roomKey}`;
    const existing = readToolMemory(storageKey);
    const record = {
        kind: toolInputValue("memoryKind") || "fact",
        content,
        importance: Math.max(1, Math.min(5, Number.parseInt(toolInputValue("memoryImportance") || "3", 10) || 3)),
        created_at: new Date().toISOString(),
    };
    existing.unshift(record);
    localStorage.setItem(storageKey, JSON.stringify(existing.slice(0, 50)));
    setToolOutput("memoryToolResult", JSON.stringify({ saved: record, recent: existing.slice(0, 10) }, null, 2));
}

function readToolMemory(storageKey: string): Array<Record<string, unknown>> {
    try {
        const parsed = JSON.parse(localStorage.getItem(storageKey) || "[]");
        return Array.isArray(parsed) ? parsed : [];
    } catch {
        return [];
    }
}

function toolInputValue(id: string): string {
    const field = document.getElementById(id) as HTMLInputElement | HTMLSelectElement | HTMLTextAreaElement | null;
    return field?.value.trim() || "";
}

function setToolOutput(id: string, value: string): void {
    const target = document.getElementById(id);
    if (target) target.textContent = value;
}

function toolErrorMessage(error: unknown): string {
    return error instanceof Error ? error.message : String(error);
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
