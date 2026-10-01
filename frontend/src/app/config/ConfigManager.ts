class ConfigManager {
    private readonly configs: Record<string, TomlConfig> = {};
    private readonly configPath = "config";
    private themeInitialized = false;
    private themeTransitionTimer: number | null = null;

    async loadConfig(configName: string): Promise<TomlConfig | null> {
        try {
            const response = await fetch(`${this.configPath}/${configName}.toml`);
            if (!response.ok) {
                throw new Error(`无法加载配置文件: ${configName}.toml`);
            }
            const config = this.parseTOML(await response.text());
            this.configs[configName] = config;
            console.log(`配置文件 ${configName}.toml 加载成功`);
            return config;
        } catch (error) {
            console.error(`加载配置文件失败: ${configErrorMessage(error)}`);
            return null;
        }
    }

    parseTOML(tomlContent: string): TomlConfig {
        const config: TomlConfig = {};
        let currentSection: string | null = null;

        for (let line of tomlContent.split("\n")) {
            const commentIndex = line.indexOf("#");
            if (commentIndex !== -1) {
                line = line.substring(0, commentIndex);
            }
            line = line.trim();
            if (!line) continue;

            const sectionMatch = line.match(/^\[(.+)\]$/);
            if (sectionMatch) {
                currentSection = normalizeTomlKey(sectionMatch[1] || "");
                config[currentSection] = {};
                continue;
            }

            const keyValueMatch = line.match(/^([^=]+)=(.+)$/);
            if (!keyValueMatch) continue;

            const key = normalizeTomlKey(keyValueMatch[1] || "");
            const value = this.parseValue((keyValueMatch[2] || "").trim());
            if (currentSection) {
                const section = config[currentSection];
                if (isTomlConfig(section)) section[key] = value;
            } else {
                config[key] = value;
            }
        }

        return config;
    }

    parseValue(value: string): TomlConfigValue {
        if ((value.startsWith('"') && value.endsWith('"')) || (value.startsWith("'") && value.endsWith("'"))) {
            return value.slice(1, -1);
        }
        if (value === "true") return true;
        if (value === "false") return false;
        if (/^-?\d+$/.test(value)) return Number.parseInt(value, 10);
        if (/^-?\d+\.\d+$/.test(value)) return Number.parseFloat(value);

        if (value.startsWith("[") && value.endsWith("]")) {
            try {
                const parsed = JSON.parse(value.replace(/'/g, '"')) as unknown;
                if (Array.isArray(parsed)) {
                    return parsed.filter(isTomlScalar);
                }
            } catch {
                return value.slice(1, -1).split(",").map((item) => String(this.parseValue(item.trim())));
            }
        }

        return value;
    }

    get<T = unknown>(configName: string, section: string | null, key: string, defaultValue?: T): T {
        const config = this.configs[configName];
        if (!config) return defaultValue as T;

        const source = section ? config[section] : config;
        if (!isTomlConfig(source)) return defaultValue as T;

        return source[key] !== undefined ? source[key] as T : defaultValue as T;
    }

    getSection(configName: string, section: string): TomlConfig | null {
        const value = this.configs[configName]?.[section];
        return isTomlConfig(value) ? value : null;
    }

    getConfig(configName: string): TomlConfig {
        return this.configs[configName] || {};
    }

    applyGeneralSettings(): void {
        const generalConfig = this.configs.general;
        if (!generalConfig) {
            console.warn("常规设置配置未加载");
            return;
        }

        configSetSelectValue("themeSelect", this.get("general", "appearance", "theme", "light"));
        this.applyTheme();
        const language = this.get("general", "language", "language", "zh-CN");
        configSetSelectValue("languageSelect", language);
        void window.TrpgI18n?.setLocale(language);
        configSetCheckboxValue("enableSound", this.get("general", "notification", "enable_sound", true));
        configSetCheckboxValue("enableNotification", this.get("general", "notification", "enable_desktop_notification", false));
        configSetCheckboxValue("enableAutosave", this.get("general", "autosave", "enabled", true));
        configSetInputValue("autosaveInterval", this.get("general", "autosave", "interval", 300));
        configSetInputValue("autosaveMaxNodes", this.get("general", "autosave", "max_nodes", 3));
        configSetInputValue("triggerMaxFileSize", this.get("general", "scenario", "trigger_max_file_size", 5242880));
        configSetCheckboxValue("showTimestamp", this.get("general", "chat", "show_timestamp", true));
        configSetCheckboxValue("streamOutput", this.get("general", "ai", "stream_output", false));
        configSetCheckboxValue("showAIHints", this.get("general", "ai", "show_ai_hints", true));
        configSetInputValue("messageFontSize", this.get("general", "chat", "message_font_size", 14));
        // KP 请求限制（达到后自动收尾并提示，不静默无响应）
        configSetInputValue("maxToolRounds", this.get("general", "ai", "max_tool_rounds", 8));
        configSetInputValue("aiRequestTimeout", this.get("general", "ai", "ai_request_timeout", 300));
        // 骰娘默认阈值（房间规则未单独设置时生效）
        configSetInputValue("diceCriticalThresholdDefault", this.get("general", "ai", "dice_critical_threshold", 1));
        configSetInputValue("diceFumbleThresholdDefault", this.get("general", "ai", "dice_fumble_threshold", 96));

        console.log("常规设置已应用到 UI");
    }

    getEffectiveTheme(): string {
        const personalTheme = getPersonalThemeCookie();
        return personalTheme || this.get<string>("general", "appearance", "theme", "light");
    }

    applyTheme(): void {
        const theme = this.getEffectiveTheme();
        const themeClassNames = ["theme-light", "theme-dark", "theme-cyber-2", "theme-tome", "light-theme", "dark-theme"];
        const body = document.body;
        body.classList.remove(...themeClassNames);

        // 仅在运行时切换主题时启用过渡，避免首屏加载出现闪烁
        if (this.themeInitialized) this.startThemeTransition();

        if (theme === "pattern_cyber_2") {
            body.classList.add("theme-cyber-2");
        } else if (theme === "pattern_tome") {
            body.classList.add("theme-tome");
        } else if (theme === "dark") {
            body.classList.add("theme-dark", "dark-theme");
        } else if (theme === "system" && window.matchMedia("(prefers-color-scheme: dark)").matches) {
            body.classList.add("theme-dark", "dark-theme");
        } else {
            body.classList.add("theme-light", "light-theme");
        }

        this.themeInitialized = true;
        console.log(`主题已应用: ${theme}`);
    }

    private startThemeTransition(): void {
        document.body.classList.add("theme-transition");
        if (this.themeTransitionTimer !== null) {
            window.clearTimeout(this.themeTransitionTimer);
        }
        this.themeTransitionTimer = window.setTimeout(() => {
            document.body.classList.remove("theme-transition");
            this.themeTransitionTimer = null;
        }, 420);
    }

    initThemeSystem(): void {
        this.applyTheme();
        this.applyAdminNameGradient();
        const mediaQuery = window.matchMedia("(prefers-color-scheme: dark)");
        mediaQuery.addEventListener("change", () => {
            const theme = this.get<string>("general", "appearance", "theme", "light");
            if (theme === "system") {
                this.applyTheme();
            }
        });
    }

    applyAdminNameGradient(): void {
        const { from, to } = getAdminNameGradientCookie();
        const root = document.documentElement;
        root.style.setProperty("--admin-name-from", from || DEFAULT_ADMIN_NAME_FROM);
        root.style.setProperty("--admin-name-to", to || DEFAULT_ADMIN_NAME_TO);
    }

    async saveConfig(configName: string, settings: TomlConfig): Promise<boolean> {
        try {
            const { response, data } = await TrpgApi.requestWithResponse<ApiResponse>(`/api/config/${configName}`, {
                method: "POST",
                body: settings,
            });

            if (!response.ok || !data.success) {
                throw new Error(data.message || data.error || "保存配置失败");
            }

            this.configs[configName] = settings;
            console.log(`配置 ${configName} 保存成功`);
            return true;
        } catch (error) {
            console.error(`保存配置失败: ${configErrorMessage(error)}`);
            return false;
        }
    }
}

function isTomlScalar(value: unknown): value is string | number | boolean {
    return ["string", "number", "boolean"].includes(typeof value);
}

function isTomlConfig(value: unknown): value is TomlConfig {
    return typeof value === "object" && value !== null && !Array.isArray(value);
}

/**
 * 还原 TOML 段名 / 键名的外层引号，例如 ["ai.small_models"] 应解析为 ai.small_models。
 * 若不去引号，保存回写时引号会被再次转义，反复保存会不断叠加转义。
 */
function normalizeTomlKey(raw: string): string {
    const text = raw.trim();
    if (text.length >= 2 && text.startsWith('"') && text.endsWith('"')) {
        try {
            const parsed = JSON.parse(text) as unknown;
            if (typeof parsed === "string") return parsed;
        } catch {
            // 非合法 JSON 字符串时按字面量处理
        }
        return text.slice(1, -1);
    }
    if (text.length >= 2 && text.startsWith("'") && text.endsWith("'")) {
        return text.slice(1, -1);
    }
    return text;
}

function configSetSelectValue(id: string, value: unknown): void {
    const select = document.getElementById(id) as HTMLSelectElement | null;
    if (select) select.value = String(value ?? "");
}

function configSetInputValue(id: string, value: unknown): void {
    const input = document.getElementById(id) as HTMLInputElement | null;
    if (input) input.value = String(value ?? "");
}

function configSetCheckboxValue(id: string, value: unknown): void {
    const checkbox = document.getElementById(id) as HTMLInputElement | null;
    if (checkbox) checkbox.checked = Boolean(value);
}

function configErrorMessage(error: unknown): string {
    return error instanceof Error ? error.message : String(error);
}

const configManager = new ConfigManager();
window.configManager = configManager;

function getPersonalThemeCookie(): string {
    const prefix = "trpg_user_theme=";
    const item = document.cookie
        .split(";")
        .map((part) => part.trim())
        .find((part) => part.startsWith(prefix));
    return item ? decodeURIComponent(item.slice(prefix.length)) : "";
}

const DEFAULT_ADMIN_NAME_FROM = "#84ff42";
const DEFAULT_ADMIN_NAME_TO = "#0ebeff";
const HEX_COLOR_PATTERN = /^#[0-9a-fA-F]{6}$/;

function getAdminNameGradientCookie(): { from: string; to: string } {
    const prefix = "trpg_admin_name_gradient=";
    const item = document.cookie
        .split(";")
        .map((part) => part.trim())
        .find((part) => part.startsWith(prefix));
    if (!item) return { from: "", to: "" };
    const [rawFrom = "", rawTo = ""] = decodeURIComponent(item.slice(prefix.length)).split(",");
    return {
        from: HEX_COLOR_PATTERN.test(rawFrom) ? rawFrom : "",
        to: HEX_COLOR_PATTERN.test(rawTo) ? rawTo : "",
    };
}
