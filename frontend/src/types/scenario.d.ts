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
