// 配置管理器模块
// 负责读取、解析和应用TOML格式的配置文件

class ConfigManager {
    constructor() {
        this.configs = {};
        this.configPath = 'config';
    }

    /**
     * 加载配置文件
     * @param {string} configName - 配置文件名称（不含扩展名）
     * @returns {Promise<Object>} 解析后的配置对象
     */
    async loadConfig(configName) {
        try {
            const response = await fetch(`${this.configPath}/${configName}.toml`);
            if (!response.ok) {
                throw new Error(`无法加载配置文件: ${configName}.toml`);
            }
            const tomlContent = await response.text();
            const config = this.parseTOML(tomlContent);
            this.configs[configName] = config;
            console.log(`配置文件 ${configName}.toml 加载成功`);
            return config;
        } catch (error) {
            console.error(`加载配置文件失败: ${error.message}`);
            return null;
        }
    }

    /**
     * 解析TOML格式的配置内容
     * @param {string} tomlContent - TOML格式的配置文本
     * @returns {Object} 解析后的配置对象
     */
    parseTOML(tomlContent) {
        const config = {};
        let currentSection = null;

        const lines = tomlContent.split('\n');
        
        for (let line of lines) {
            // 去除行尾注释
            const commentIndex = line.indexOf('#');
            if (commentIndex !== -1) {
                line = line.substring(0, commentIndex);
            }
            
            line = line.trim();
            
            // 跳过空行
            if (!line) continue;
            
            // 解析节（section）
            const sectionMatch = line.match(/^\[(.+)\]$/);
            if (sectionMatch) {
                currentSection = sectionMatch[1];
                config[currentSection] = {};
                continue;
            }
            
            // 解析键值对
            const keyValueMatch = line.match(/^([^=]+)=(.+)$/);
            if (keyValueMatch) {
                const key = keyValueMatch[1].trim();
                let value = keyValueMatch[2].trim();
                
                // 解析值类型
                value = this.parseValue(value);
                
                if (currentSection) {
                    config[currentSection][key] = value;
                } else {
                    config[key] = value;
                }
            }
        }
        
        return config;
    }

    /**
     * 解析配置值，自动识别类型
     * @param {string} value - 配置值的字符串表示
     * @returns {*} 解析后的值
     */
    parseValue(value) {
        // 去除引号
        if ((value.startsWith('"') && value.endsWith('"')) || 
            (value.startsWith("'") && value.endsWith("'"))) {
            return value.slice(1, -1);
        }
        
        // 布尔值
        if (value === 'true') return true;
        if (value === 'false') return false;
        
        // 数字
        if (/^-?\d+$/.test(value)) {
            return parseInt(value, 10);
        }
        if (/^-?\d+\.\d+$/.test(value)) {
            return parseFloat(value);
        }
        
        // 数组
        if (value.startsWith('[') && value.endsWith(']')) {
            try {
                return JSON.parse(value.replace(/'/g, '"'));
            } catch {
                return value.slice(1, -1).split(',').map(v => this.parseValue(v.trim()));
            }
        }
        
        // 默认返回字符串
        return value;
    }

    /**
     * 获取配置值
     * @param {string} configName - 配置文件名称
     * @param {string} section - 配置节名称
     * @param {string} key - 配置键名称
     * @param {*} defaultValue - 默认值
     * @returns {*} 配置值
     */
    get(configName, section, key, defaultValue = null) {
        const config = this.configs[configName];
        if (!config) return defaultValue;
        
        if (section) {
            const sectionConfig = config[section];
            if (!sectionConfig) return defaultValue;
            return sectionConfig[key] !== undefined ? sectionConfig[key] : defaultValue;
        }
        
        return config[key] !== undefined ? config[key] : defaultValue;
    }

    /**
     * 获取整个配置节
     * @param {string} configName - 配置文件名称
     * @param {string} section - 配置节名称
     * @returns {Object|null} 配置节对象
     */
    getSection(configName, section) {
        const config = this.configs[configName];
        if (!config) return null;
        return config[section] || null;
    }
    
    /**
     * 获取完整的配置对象
     * @param {string} configName - 配置文件名称
     * @returns {Object} 配置对象
     */
    getConfig(configName) {
        return this.configs[configName] || {};
    }

    /**
     * 应用常规设置到UI
     */
    applyGeneralSettings() {
        const generalConfig = this.configs['general'];
        if (!generalConfig) {
            console.warn('常规设置配置未加载');
            return;
        }

        // 应用主题设置
        const theme = this.get('general', 'appearance', 'theme', 'light');
        const themeSelect = document.getElementById('themeSelect');
        if (themeSelect) {
            themeSelect.value = theme;
        }
        
        // 应用主题到页面
        this.applyTheme();

        // 应用语言设置
        const language = this.get('general', 'language', 'language', 'zh-CN');
        const languageSelect = document.getElementById('languageSelect');
        if (languageSelect) {
            languageSelect.value = language;
        }

        // 应用通知设置
        const enableSound = this.get('general', 'notification', 'enable_sound', true);
        const enableSoundCheckbox = document.getElementById('enableSound');
        if (enableSoundCheckbox) {
            enableSoundCheckbox.checked = enableSound;
        }

        const enableNotification = this.get('general', 'notification', 'enable_desktop_notification', false);
        const enableNotificationCheckbox = document.getElementById('enableNotification');
        if (enableNotificationCheckbox) {
            enableNotificationCheckbox.checked = enableNotification;
        }

        // 应用自动保存设置
        const enableAutosave = this.get('general', 'autosave', 'enabled', true);
        const enableAutosaveCheckbox = document.getElementById('enableAutosave');
        if (enableAutosaveCheckbox) {
            enableAutosaveCheckbox.checked = enableAutosave;
        }

        const autosaveInterval = this.get('general', 'autosave', 'interval', 300);
        const autosaveIntervalInput = document.getElementById('autosaveInterval');
        if (autosaveIntervalInput) {
            autosaveIntervalInput.value = autosaveInterval;
        }

        // 应用聊天设置
        const showTimestamp = this.get('general', 'chat', 'show_timestamp', true);
        const showTimestampCheckbox = document.getElementById('showTimestamp');
        if (showTimestampCheckbox) {
            showTimestampCheckbox.checked = showTimestamp;
        }

        const messageFontSize = this.get('general', 'chat', 'message_font_size', 14);
        const messageFontSizeInput = document.getElementById('messageFontSize');
        if (messageFontSizeInput) {
            messageFontSizeInput.value = messageFontSize;
        }

        console.log('常规设置已应用到UI');
    }

    /**
     * 应用主题到页面
     */
    applyTheme() {
        const theme = this.get('general', 'appearance', 'theme', 'light');
        
        // 移除所有主题类
        document.body.classList.remove('dark-theme', 'light-theme');
        
        if (theme === 'dark') {
            // 应用暗色主题
            document.body.classList.add('dark-theme');
        } else if (theme === 'light') {
            // 应用浅色主题
            document.body.classList.add('light-theme');
        } else if (theme === 'system') {
            // 跟随系统主题
            const prefersDarkScheme = window.matchMedia('(prefers-color-scheme: dark)').matches;
            if (prefersDarkScheme) {
                document.body.classList.add('dark-theme');
            } else {
                document.body.classList.add('light-theme');
            }
        }
        
        console.log(`主题已应用: ${theme}`);
    }
    
    /**
     * 初始化主题系统
     */
    initThemeSystem() {
        // 应用初始主题
        this.applyTheme();
        
        // 监听系统主题变化
        if (window.matchMedia) {
            const mediaQuery = window.matchMedia('(prefers-color-scheme: dark)');
            mediaQuery.addEventListener('change', () => {
                // 只有在跟随系统主题时才响应变化
                const theme = this.get('general', 'appearance', 'theme', 'light');
                if (theme === 'system') {
                    this.applyTheme();
                }
            });
        }
    }

    /**
     * 保存设置到配置文件（通过后端API）
     * @param {string} configName - 配置文件名称
     * @param {Object} settings - 设置对象
     * @returns {Promise<boolean>} 是否保存成功
     */
    async saveConfig(configName, settings) {
        try {
            const response = await fetch(`/api/config/${configName}`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify(settings)
            });
            
            if (!response.ok) {
                throw new Error('保存配置失败');
            }
            
            const result = await response.json();
            if (result.success) {
                // 更新本地缓存
                this.configs[configName] = settings;
                console.log(`配置 ${configName} 保存成功`);
                return true;
            } else {
                throw new Error(result.message || '保存配置失败');
            }
        } catch (error) {
            console.error(`保存配置失败: ${error.message}`);
            return false;
        }
    }
}

// 创建全局配置管理器实例
const configManager = new ConfigManager();

export default configManager;
