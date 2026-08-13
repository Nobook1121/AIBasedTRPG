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

interface PermissionNode {
    id: string;
    label: string;
    description?: string;
}

interface PermissionGroup {
    id: string;
    label: string;
    description?: string;
    nodes: PermissionNode[];
}

interface PermissionConfig {
    roles: string[];
    groups: PermissionGroup[];
    matrix: Record<string, string[]>;
}
