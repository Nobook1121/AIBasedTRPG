type JsonPrimitive = string | number | boolean | null;
type JsonObject = { [key: string]: JsonValue };
type JsonArray = JsonValue[];
type JsonValue = JsonPrimitive | JsonObject | JsonArray;
type RequestBody = BodyInit | JsonValue | object | null;

interface TrpgRequestOptions extends Omit<RequestInit, "body"> {
    body?: RequestBody;
    method?: string;
    timeout?: number;
}

interface TrpgResponse<T = unknown> {
    response: Response;
    data: T;
}

interface ApiResponse<T = unknown> {
    success: boolean;
    message?: string;
    error?: string;
    data?: T;
}

interface TrpgApiClient {
    request<T = unknown>(url: string, options?: TrpgRequestOptions): Promise<T>;
    requestWithResponse<T = unknown>(url: string, options?: TrpgRequestOptions): Promise<TrpgResponse<T>>;
    get<T = unknown>(url: string, options?: TrpgRequestOptions): Promise<T>;
    post<T = unknown>(url: string, body?: RequestBody, options?: TrpgRequestOptions): Promise<T>;
    put<T = unknown>(url: string, body?: RequestBody, options?: TrpgRequestOptions): Promise<T>;
    del<T = unknown>(url: string, options?: TrpgRequestOptions): Promise<T>;
}

interface TrpgDomClient {
    byId<T extends HTMLElement = HTMLElement>(id: string): T | null;
    one<T extends Element = Element>(selector: string, root?: ParentNode): T | null;
    all<T extends Element = Element>(selector: string, root?: ParentNode): T[];
    on(
        target: EventTarget | null,
        eventName: string,
        handler: EventListenerOrEventListenerObject,
        options?: boolean | AddEventListenerOptions,
    ): () => void;
    setButtonDisclosure(button: HTMLElement | null, options: ButtonDisclosureOptions): void;
    removeModalBackdropsWhenIdle(): boolean;
}

interface ButtonDisclosureOptions {
    expanded: boolean;
    expandedLabel: string;
    collapsedLabel: string;
    expandedIconClass?: string;
    collapsedIconClass?: string;
}

interface TrpgNamespace {
    api?: TrpgApiClient;
    dom?: TrpgDomClient;
}

interface TrpgTemplateRenderer {
    render(templateId: string, values?: Record<string, unknown>): string;
    escapeHtml(value: unknown): string;
}

interface BootstrapModalInstance {
    show(): void;
    hide(): void;
}

interface BootstrapModalConstructor {
    new(element: Element, options?: { backdrop?: boolean | "static" }): BootstrapModalInstance;
    getInstance(element: Element | null): BootstrapModalInstance | null;
}

declare const bootstrap: {
    Modal: BootstrapModalConstructor;
};

interface ScenarioSegment {
    id: number;
    content: string;
    marker: string;
}

interface Scenario {
    id: number;
    title: string;
    author: string;
    playerCount: number;
    notes?: string;
    background?: string;
    preparation?: string;
    scenes: ScenarioSegment[];
    endings: ScenarioSegment[];
    cover?: string;
    owner_id?: string | number;
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
    validateScenarioData(data: unknown): data is ScenarioInput;
}

interface ScenarioViewHandlers {
    onCreateScenarioClick(): void;
    onSaveScenario(): Promise<void>;
    onPreviewScenario(id: number): void;
    onEditScenario(id: number): void;
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
    openCreateModal(): void;
    openEditModal(scenario: Scenario): void;
    closeModal(): void;
    previewScenario(scenario: Scenario): void;
    getFormData(): ScenarioInput;
    showMessage(message: string, isError?: boolean): void;
}

interface DiceParseSuccess {
    success: true;
    count: number;
    sides: number;
    results: number[];
    total: number;
}

interface DiceParseFailure {
    success: false;
    error: string;
}

type DiceParseResult = DiceParseSuccess | DiceParseFailure;

interface DiceToolConstructor {
    new(): DiceTool;
}

interface DiceTool {
    handleDiceCommand(command: string): string;
    parseDiceCommand(command: string): DiceParseResult;
}

interface ToolManagerConstructor {
    new(): ToolManager;
}

interface ToolManager {
    handleCommand(command: string): string | null;
    recordCharacterChange(payload: Record<string, unknown>): Promise<unknown>;
}

interface Window {
    TRPG?: TrpgNamespace;
    TrpgApi: TrpgApiClient;
    TrpgDom: TrpgDomClient;
    TrpgTemplates: TrpgTemplateRenderer;
    ScenarioModel: ScenarioModelConstructor;
    ScenarioView: ScenarioViewConstructor;
    ScenarioController: { new(): unknown };
    DiceTool: DiceToolConstructor;
    ToolManager: ToolManagerConstructor;
    toolManager?: ToolManager;
    currentRoom?: Room | null;
    uploadedCoverFile?: File;
    currentPlatform?: string;
    currentTestingPlatform?: string;
    loadAIRoles?: () => void;
    showNotification?: (message: string, type?: string) => void;
    recordCharacterChange?: (payload: Record<string, unknown>) => Promise<unknown>;
    TrpgCookies?: TrpgCookieClient;
    configManager: ConfigManager;
    aiPlatformManager: AIPlatformManager;
    testRequestConfigs: Record<string, TestRequestConfig>;
    getTestRequestConfig(modelId: string): TestRequestConfig;
    marked?: MarkedParser;
    renderChatMessages?: (messages: ChatMessage[]) => void;
    getCurrentChatMessages?: () => ChatMessage[];
    clearChatMessages?: () => void;
    joinSocketRoom?: (roomId: string) => void;
    leaveSocketRoom?: (roomId: string) => void;
    reconnectSocket?: () => void;
    disconnectSocket?: () => void;
    initRoomManagement?: () => void;
    autoLoadLastRoom?: () => Promise<void>;
    clearCurrentRoom?: () => void;
}

declare function showNotification(message: string, type?: string): void;
declare function showAuthModal(): void;
declare const TrpgCookies: TrpgCookieClient;
declare function initAuth(): Promise<boolean>;
declare const TrpgApi: TrpgApiClient;
declare const TrpgDom: TrpgDomClient;

interface TrpgCookieClient {
    get(name: string): string;
    set(name: string, value: string, days?: number): void;
    remove(name: string): void;
    hasConsent(): boolean;
    showCookieConsentBanner(): void;
}

interface ConfigManager {
    loadConfig(configName: string): Promise<TomlConfig | null>;
    saveConfig(configName: string, settings: TomlConfig): Promise<boolean>;
    getConfig(configName: string): TomlConfig;
    get<T = unknown>(configName: string, section: string | null, key: string, defaultValue?: T): T;
    getSection(configName: string, section: string): TomlConfig | null;
    applyGeneralSettings(): void;
    initThemeSystem(): void;
    applyTheme(): void;
}

type TomlConfigValue = string | number | boolean | Array<string | number | boolean> | TomlConfig;
interface TomlConfig {
    [key: string]: TomlConfigValue;
}

interface AIModelConfig {
    id: string;
    name: string;
    description: string;
    enabled: boolean;
    params?: Record<string, unknown>;
}

interface AIPlatformConfig {
    platform: string;
    name: string;
    description: string;
    icon: string;
    enabled: boolean;
    config: {
        api_key?: string;
        base_url: string;
        timeout: number;
    };
    models: AIModelConfig[];
}

interface AIPlatformManager {
    loadPlatforms(): Promise<AIPlatformConfig[]>;
    getPlatform(platform: string): AIPlatformConfig | null;
    getAllPlatforms(): AIPlatformConfig[];
    setPlatformEnabled(platform: string, enabled: boolean): Promise<boolean>;
    updatePlatformConfig(platform: string, config: AIPlatformConfig): Promise<boolean>;
    savePlatformConfig(platform: string, config: AIPlatformConfig): Promise<boolean>;
    addModel(platform: string, model: Pick<AIModelConfig, "id" | "name"> & Partial<Pick<AIModelConfig, "description">>): Promise<boolean>;
    removeModel(platform: string, modelId: string): Promise<boolean>;
    testAPI(platform: string, modelId: string): Promise<AITestResult>;
}

interface AITestResult {
    success: boolean;
    time?: string;
    model?: string;
    speed?: string;
    consumption?: string;
    duration?: string;
    response?: unknown;
    error?: string;
}

interface TestRequestConfig {
    messages: Array<{ role: string; content: string }>;
    temperature: number;
    max_tokens: number;
    stop: string[];
    extra_body?: Record<string, unknown>;
}

interface MarkedParser {
    (content: string, options?: Record<string, unknown>): string;
    parse(content: string): string;
    setOptions(options: Record<string, unknown>): void;
}

declare const marked: MarkedParser;

interface SocketLike {
    connected: boolean;
    on(eventName: string, handler: (payload: unknown) => void): void;
    emit(eventName: string, payload?: unknown): void;
    disconnect(): void;
}

declare function io(options?: Record<string, unknown>): SocketLike;

interface RoomMember {
    user_id?: string | number;
    username?: string;
    role?: string;
    character_card?: Partial<COC7CharacterCard>;
    character_state?: CharacterRuntimeState;
}

interface CharacterRuntimeRecord {
    id: string;
    type: "damage" | "san";
    value: number;
    reason: string;
    created_at?: string;
    created_by?: string | number;
}

interface CharacterRuntimeState {
    current_hp?: number;
    max_hp?: number;
    current_san?: number;
    max_san?: number;
    injury_records?: CharacterRuntimeRecord[];
    sanity_records?: CharacterRuntimeRecord[];
    records?: CharacterRuntimeRecord[];
}

interface Room {
    id: string;
    code?: string;
    room_code?: string;
    name: string;
    created_at?: string;
    owner_id?: string | number;
    scenario_id?: number;
    scenario_title?: string;
    members?: RoomMember[];
    messages?: ChatMessage[];
    saves?: Array<{ filename: string; title?: string; created_at?: string }>;
}

interface ChatMessage {
    id?: string;
    role?: string;
    type?: string;
    content: string;
    sender?: string;
    sender_id?: string | number | null;
    sender_name?: string;
    senderName?: string;
    avatar?: string;
    timestamp?: string;
    time?: string;
    processing_time?: number;
    token_count?: number;
    metadata?: Record<string, unknown>;
}

interface CharacterRecordPayload extends Record<string, unknown> {
    roomId?: string;
    roomName?: string;
    username?: string;
    type?: "damage" | "san";
    value?: number;
    reason?: string;
}
