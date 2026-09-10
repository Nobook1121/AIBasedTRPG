let toolManager: ToolManager | null = null;

document.addEventListener("DOMContentLoaded", () => {
    void initializeApplication();
});

async function initializeApplication(): Promise<void> {
    const dom = window.TrpgDom;
    await window.TrpgI18n?.ready;
    window.TrpgI18n?.apply();

    toolManager = new ToolManager();
    window.toolManager = toolManager;

    initTabs();
    initDiceTool();
    initCommandToolPanels();
    initToolTabs();
    initSettingsTabs();

    await loadAndApplyConfigs();
    await initAIPlatforms();
    await initAuth();
    initScenarioManagement();
    initCharacterManagement();
    initChat();
    await initNetworkConfig();
    initRoomManagement();
    initSidebarToggle();
    await autoLoadLastRoom();

    dom.on(document, "hidden.bs.modal", () => {
        setTimeout(() => {
            dom.removeModalBackdropsWhenIdle();
        }, 100);
    });
}

async function loadAndApplyConfigs(): Promise<void> {
    try {
        await configManager.loadConfig("general");
        configManager.applyGeneralSettings();
        configManager.initThemeSystem();
    } catch (error) {
        console.error("failed to load config", error);
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
    const result = window.toolManager?.handleCommand(command) || "tool manager not ready";
    setToolOutput("cocCheckResult", result);
}

function renderRoomSnapshotTool(): void {
    const room = window.currentRoom;
    if (!room) {
        setToolOutput("roomSnapshotResult", "no room joined");
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
        setToolOutput("scenarioContextResult", "no scenario bound");
        return;
    }

    try {
        const response = await TrpgApi.get<ApiResponse<Scenario[]>>("/api/scenarios");
        const scenario = response.data?.find((item) => String(item.id) === String(room.scenario_id));
        if (!response.success || !scenario) {
            setToolOutput("scenarioContextResult", "scenario not found");
            return;
        }

        const query = toolInputValue("scenarioContextQuery").toLowerCase();
        const limit = Math.max(1, Math.min(20, Number.parseInt(toolInputValue("scenarioContextLimit") || "5", 10) || 5));
        const modules = normalizeScenarioModulesForTool(scenario);
        const matches = modules.filter((item) => {
            if (!query) return true;
            return JSON.stringify(item).toLowerCase().includes(query);
        }).slice(0, limit);

        setToolOutput("scenarioContextResult", JSON.stringify({
            scenario: {
                id: scenario.id,
                title: scenario.title,
                notes: scenario.notes,
                allow_open_ending: scenario.allow_open_ending,
                module_count: modules.length,
            },
            matches,
        }, null, 2));
    } catch (error) {
        setToolOutput("scenarioContextResult", `scenario lookup failed: ${toolErrorMessage(error)}`);
    }
}

function renderCharacterCardsTool(): void {
    const room = window.currentRoom;
    if (!room) {
        setToolOutput("characterCardsResult", "no room joined");
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
        setToolOutput("memoryToolResult", "fill memory content first");
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

function normalizeScenarioModulesForTool(scenario: Scenario): Array<Record<string, unknown>> {
    const modules: Array<Record<string, unknown>> = Array.isArray(scenario.modules)
        ? (scenario.modules as unknown as Array<Record<string, unknown>>)
        : [];

    return modules.map((module, index) => {
        const record = module as Record<string, unknown>;
        return {
            id: record.id || `module-${index + 1}`,
            module_type: record.module_type,
            title: record.title,
            summary: record.summary,
            content: record.content,
            code: record.code,
            open_ending: record.open_ending,
            triggers: record.triggers,
        };
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
            expandedLabel: "Collapse sidebar",
            collapsedLabel: "Expand sidebar",
            expandedIconClass: "fa fa-angle-double-left",
            collapsedIconClass: "fa fa-angle-double-right",
        });
    }

    dom.on(toggleBtn, "click", () => {
        const isCollapsed = sidebar.classList.contains("sidebar-collapsed");
        setSidebarExpanded(isCollapsed);
    });
}
