type ScenarioTriggerContentMode = "text" | "richtext" | "image" | "file";
type ScenarioModuleType = "opening" | "background" | "public_info" | "preparation" | "timeline" | "scene" | "ending" | "monster" | "npc" | "custom";

interface ScenarioModuleTimelineEntry {
    id: string;
    time_point: string;
    event: string;
}

interface ScenarioModuleInputItem {
    id: string;
    label: string;
    value: string;
    send_to_ai: boolean;
}

interface ScenarioModuleWeaponRow {
    name: string;
    skill: string;
    damage: string;
    range: string;
    attacks: string;
    ammo: string;
    malfunction: string;
    note: string;
}

interface ScenarioModuleSkillRow {
    name: string;
    base: string;
}

interface ScenarioTrigger {
    id: number;
    display_name: string;
    keyword: string;
    condition: string;
    content_mode: ScenarioTriggerContentMode;
    content?: string | undefined;
    asset_name?: string | undefined;
    asset_mime?: string | undefined;
    asset_size?: number | undefined;
    asset_path?: string | undefined;
    asset_url?: string | undefined;
    asset_data_url?: string | undefined;
}

interface ScenarioModule {
    id: string;
    module_type: ScenarioModuleType;
    title: string;
    summary: string;
    content?: string | undefined;
    notes?: string | undefined;
    visibility?: "public" | "kp" | undefined;
    send_to_ai?: boolean | undefined;
    code?: string | undefined;
    scene_id?: number | undefined;
    ending_id?: number | undefined;
    triggers?: ScenarioTrigger[] | undefined;
    timeline_entries?: ScenarioModuleTimelineEntry[] | undefined;
    open_ending?: boolean | undefined;
    fixed_opening?: boolean | undefined;
    inputs?: ScenarioModuleInputItem[] | undefined;
    attributes?: Record<string, string> | undefined;
    battle?: Record<string, string> | undefined;
    skills?: ScenarioModuleSkillRow[] | undefined;
    weapons?: ScenarioModuleWeaponRow[] | undefined;
}

interface Scenario {
    id: number;
    scenario_version?: string;
    title: string;
    author: string;
    playerCount: number;
    notes?: string;
    allow_open_ending?: boolean;
    modules?: ScenarioModule[];
    cover?: string;
    owner_id?: string | number;
    public_id?: string;
    creator_username?: string;
    createdAt?: string;
    updatedAt?: string;
    user_id?: string | number;
}

type ScenarioInput = Omit<Scenario, "id" | "createdAt" | "updatedAt" | "owner_id"> & {
    id?: number;
};

interface ScenarioModelConstructor {
    new(): ScenarioModel;
}

interface ScenarioModel {
    scenarios: Scenario[];
    apiBaseUrl: string;
    userId: string | number | null;
    isAuthenticated: boolean;
    getCurrentUserId(): string | number | null;
    checkAuthStatus(): Promise<boolean>;
    init(): Promise<Scenario[]>;
    loadScenarios(): Promise<Scenario[]>;
    createScenario(scenarioData: ScenarioInput): Promise<Scenario>;
    updateScenario(id: number, scenarioData: ScenarioInput): Promise<Scenario>;
    deleteScenario(id: number): Promise<boolean>;
    getScenario(id: number): Scenario | undefined;
    getScenarios(): Scenario[];
    saveScenarios(): void;
    importScenario(scenarioData: unknown): Promise<Scenario>;
    convertScript(text: string, title?: string): Promise<ScenarioInput>;
    convertScriptFile(file: File, title?: string): Promise<ScenarioInput>;
    loadDraft(): Promise<ScenarioInput | null>;
    saveDraft(scenarioData: ScenarioInput): Promise<ScenarioInput>;
    discardDraft(): Promise<void>;
    validateScenarioData(data: unknown): data is ScenarioInput;
}

interface ScenarioViewHandlers {
    onCreateScenarioClick(): void;
    onImportScenarioDocumentClick(): Promise<void>;
    onImportScenarioDocument(file: File): Promise<void>;
    onSaveScenario(): Promise<void>;
    onSaveDraft(): Promise<void>;
    onPreviewScenario(id: number): void;
    onEditScenario(id: number): void;
    onPlayScenario(id: number): void;
    onDeleteScenario(id: number): Promise<void>;
    onImportScenario(files: FileList | null): Promise<void>;
}

interface ScenarioViewConstructor {
    new(): ScenarioView;
}

interface ScenarioView {
    scenarioList: HTMLElement;
    saveScenarioHandler: () => Promise<void>;
    setEventHandlers(handlers: ScenarioViewHandlers): void;
    renderScenarioList(scenarios: Scenario[]): void;
    openCreateModal(): Promise<void>;
    openEditModal(scenario: Scenario): void;
    fillDraftData(draft: ScenarioInput): void;
    showDraftPrompt(): Promise<"continue" | "discard" | "cancel">;
    closeModal(): void;
    previewScenario(scenario: Scenario): void;
    getFormData(): ScenarioInput;
    showMessage(message: string, isError?: boolean): void;
    showConversionProgress(fileName: string): void;
    updateConversionProgress(stage: number, state: "pending" | "active" | "complete" | "error", detail?: string): void;
    closeConversionProgress(): void;
}
