class ConfigManager {
    private readonly configs: Record<string, TomlConfig> = {};
    private readonly configPath = "config";

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
                currentSection = sectionMatch[1] || "";
                config[currentSection] = {};
                continue;
            }

            const keyValueMatch = line.match(/^([^=]+)=(.+)$/);
            if (!keyValueMatch) continue;

            const key = (keyValueMatch[1] || "").trim();
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
        configSetSelectValue("languageSelect", this.get("general", "language", "language", "zh-CN"));
        configSetCheckboxValue("enableSound", this.get("general", "notification", "enable_sound", true));
        configSetCheckboxValue("enableNotification", this.get("general", "notification", "enable_desktop_notification", false));
        configSetCheckboxValue("enableAutosave", this.get("general", "autosave", "enabled", true));
        configSetInputValue("autosaveInterval", this.get("general", "autosave", "interval", 300));
        configSetCheckboxValue("showTimestamp", this.get("general", "chat", "show_timestamp", true));
        configSetInputValue("messageFontSize", this.get("general", "chat", "message_font_size", 14));

        console.log("常规设置已应用到 UI");
    }

    applyTheme(): void {
        const theme = this.get<string>("general", "appearance", "theme", "light");
        document.body.classList.remove("dark-theme", "light-theme");

        if (theme === "dark") {
            document.body.classList.add("dark-theme");
        } else if (theme === "system" && window.matchMedia("(prefers-color-scheme: dark)").matches) {
            document.body.classList.add("dark-theme");
        } else {
            document.body.classList.add("light-theme");
        }

        console.log(`主题已应用: ${theme}`);
    }

    initThemeSystem(): void {
        this.applyTheme();
        const mediaQuery = window.matchMedia("(prefers-color-scheme: dark)");
        mediaQuery.addEventListener("change", () => {
            const theme = this.get<string>("general", "appearance", "theme", "light");
            if (theme === "system") {
                this.applyTheme();
            }
        });
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
