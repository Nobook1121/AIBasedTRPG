// AI平台管理模块
// 负责加载、管理和配置AI平台

import { getTestRequestConfig } from './TestRequestConfig.js';

class AIPlatformManager {
    constructor() {
        this.platforms = {};
        this.platformsPath = 'config/aiplatform';
        this.currentPlatform = null;
    }

    /**
     * 加载所有AI平台配置
     * @returns {Promise<Array>} 平台列表
     */
    async loadPlatforms() {
        try {
            const platforms = ['aliyun', 'siliconflow', 'deepseek', 'openrouter'];
            const platformPromises = platforms.map(async (platform) => {
                try {
                    const response = await fetch(`${this.platformsPath}/${platform}.json`);
                    if (!response.ok) {
                        throw new Error(`无法加载平台配置: ${platform}`);
                    }
                    const config = await response.json();
                    this.platforms[platform] = config;
                    return config;
                } catch (error) {
                    console.error(`加载平台 ${platform} 失败:`, error);
                    return null;
                }
            });

            const results = await Promise.all(platformPromises);
            return results.filter(Boolean);
        } catch (error) {
            console.error('加载平台配置失败:', error);
            return [];
        }
    }

    /**
     * 获取平台配置
     * @param {string} platform - 平台名称
     * @returns {Object|null} 平台配置
     */
    getPlatform(platform) {
        return this.platforms[platform] || null;
    }

    /**
     * 获取所有平台
     * @returns {Array} 平台列表
     */
    getAllPlatforms() {
        return Object.values(this.platforms);
    }

    /**
     * 启用/禁用平台
     * @param {string} platform - 平台名称
     * @param {boolean} enabled - 是否启用
     * @returns {Promise<boolean>} 是否成功
     */
    async setPlatformEnabled(platform, enabled) {
        try {
            const config = this.platforms[platform];
            if (!config) {
                throw new Error('平台不存在');
            }

            config.enabled = enabled;
            await this.savePlatformConfig(platform, config);
            this.platforms[platform] = config;
            return true;
        } catch (error) {
            console.error('设置平台状态失败:', error);
            return false;
        }
    }

    /**
     * 更新平台配置
     * @param {string} platform - 平台名称
     * @param {Object} config - 配置对象
     * @returns {Promise<boolean>} 是否成功
     */
    async updatePlatformConfig(platform, config) {
        try {
            await this.savePlatformConfig(platform, config);
            this.platforms[platform] = config;
            return true;
        } catch (error) {
            console.error('更新平台配置失败:', error);
            return false;
        }
    }

    /**
     * 保存平台配置
     * @param {string} platform - 平台名称
     * @param {Object} config - 配置对象
     * @returns {Promise<void>}
     */
    async savePlatformConfig(platform, config) {
        try {
            const response = await fetch(`/api/config/aiplatform/${platform}`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify(config)
            });

            if (!response.ok) {
                throw new Error('保存配置失败');
            }

            const result = await response.json();
            if (!result.success) {
                throw new Error(result.message || '保存配置失败');
            }
            
            return true;
        } catch (error) {
            console.error('保存平台配置失败:', error);
            throw error;
        }
    }

    /**
     * 添加模型
     * @param {string} platform - 平台名称
     * @param {Object} model - 模型对象
     * @returns {Promise<boolean>} 是否成功
     */
    async addModel(platform, model) {
        try {
            const config = this.platforms[platform];
            if (!config) {
                throw new Error('平台不存在');
            }

            config.models.push({
                id: model.id,
                name: model.name,
                description: model.description || '',
                enabled: true,
                params: {
                    context_window: 8192,
                    temperature: 0.7,
                    top_p: 0.95,
                    max_tokens: 4096
                }
            });

            await this.savePlatformConfig(platform, config);
            this.platforms[platform] = config;
            return true;
        } catch (error) {
            console.error('添加模型失败:', error);
            return false;
        }
    }

    /**
     * 移除模型
     * @param {string} platform - 平台名称
     * @param {string} modelId - 模型ID
     * @returns {Promise<boolean>} 是否成功
     */
    async removeModel(platform, modelId) {
        try {
            const config = this.platforms[platform];
            if (!config) {
                throw new Error('平台不存在');
            }

            const modelIndex = config.models.findIndex(m => m.id === modelId);
            if (modelIndex === -1) {
                throw new Error('模型不存在');
            }

            config.models.splice(modelIndex, 1);
            await this.savePlatformConfig(platform, config);
            this.platforms[platform] = config;
            return true;
        } catch (error) {
            console.error('移除模型失败:', error);
            return false;
        }
    }

    /**
     * 测试API连接
     * @param {string} platform - 平台名称
     * @param {string} modelId - 模型ID
     * @returns {Promise<Object>} 测试结果
     */
    async testAPI(platform, modelId) {
        try {
            const config = this.platforms[platform];
            if (!config) {
                throw new Error('平台不存在');
            }

            if (!config.enabled) {
                throw new Error('平台未启用');
            }

            if (!config.config.api_key) {
                throw new Error('API Key未设置');
            }

            const model = config.models.find(m => m.id === modelId);
            if (!model) {
                throw new Error('模型不存在');
            }

            // 记录测试开始时间
            const startTime = Date.now();

            // 从配置文件中获取测试请求配置
            const testConfig = getTestRequestConfig(modelId);
            
            // 构建测试请求
            const testRequest = {
                model: modelId,
                ...testConfig
            };

            // 在控制台输出请求的消息
            console.log('API测试请求:', testRequest);

            // 发送测试请求到服务器端，由服务器端转发并记录日志
            const response = await fetch(`/api/config/aiplatform/${platform}/test`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify(testRequest),
                timeout: config.config.timeout * 1000
            });

            // 记录测试结束时间
            const endTime = Date.now();
            const duration = (endTime - startTime) / 1000;

            if (!response.ok) {
                const errorData = await response.json().catch(() => ({}));
                throw new Error(errorData.error || `API请求失败: ${response.status}`);
            }

            const serverResponse = await response.json();

            // 在控制台输出模型回复的消息
            console.log('API测试响应:', serverResponse);

            // 处理服务器端返回的响应格式
            if (!serverResponse.success) {
                throw new Error(serverResponse.error || 'API测试失败');
            }

            const result = serverResponse.response;

            // 处理阿里云百炼API的响应格式
            let totalTokens = 0;
            if (result.usage) {
                totalTokens = result.usage.total_tokens || 0;
            } else if (result.output && result.output.usage) {
                totalTokens = result.output.usage.total_tokens || 0;
            }
            const tokenSpeed = totalTokens / duration;

            return {
                success: true,
                time: new Date().toLocaleString(),
                model: model.name,
                speed: `${tokenSpeed.toFixed(2)} token/s`,
                consumption: `${totalTokens} tokens`,
                duration: `${duration.toFixed(2)}s`,
                response: result
            };
        } catch (error) {
            console.error('API测试失败:', error);
            return {
                success: false,
                error: error.message
            };
        }
    }

}


// 创建全局AI平台管理器实例
const aiPlatformManager = new AIPlatformManager();

export default aiPlatformManager;
