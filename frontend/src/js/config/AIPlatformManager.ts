class AIPlatformManager {
    private readonly platforms: Record<string, AIPlatformConfig> = {};
    private readonly platformsPath = "config/aiplatform";

    async loadPlatforms(): Promise<AIPlatformConfig[]> {
        const platformIds = ["aliyun", "siliconflow", "deepseek", "openrouter", "lmstudio"];
        const results = await Promise.all(platformIds.map((platform) => this.loadPlatform(platform)));
        return results.filter((platform): platform is AIPlatformConfig => platform !== null);
    }

    getPlatform(platform: string): AIPlatformConfig | null {
        return this.platforms[platform] || null;
    }

    getAllPlatforms(): AIPlatformConfig[] {
        return Object.values(this.platforms);
    }

    async setPlatformEnabled(platform: string, enabled: boolean): Promise<boolean> {
        const config = this.getPlatform(platform);
        if (!config) return false;
        config.enabled = enabled;
        return this.updatePlatformConfig(platform, config);
    }

    async updatePlatformConfig(platform: string, config: AIPlatformConfig): Promise<boolean> {
        try {
            await this.savePlatformConfig(platform, config);
            this.platforms[platform] = config;
            return true;
        } catch (error) {
            console.error("更新平台配置失败:", error);
            return false;
        }
    }

    async savePlatformConfig(platform: string, config: AIPlatformConfig): Promise<boolean> {
        const { response, data } = await TrpgApi.requestWithResponse<ApiResponse>(`/api/config/aiplatform/${platform}`, {
            method: "POST",
            body: config,
        });

        if (!response.ok || !data.success) {
            throw new Error(data.message || data.error || "保存配置失败");
        }
        return true;
    }

    async addModel(
        platform: string,
        model: Pick<AIModelConfig, "id" | "name"> & Partial<Pick<AIModelConfig, "description">>,
    ): Promise<boolean> {
        try {
            const config = this.getPlatform(platform);
            if (!config) throw new Error("平台不存在");

            config.models.push({
                id: model.id,
                name: model.name,
                description: model.description || "",
                enabled: true,
                params: {
                    context_window: 8192,
                    temperature: 0.7,
                    top_p: 0.95,
                    max_tokens: 4096,
                },
            });

            await this.generateModelRequestConfig(platform, model.id);
            await this.savePlatformConfig(platform, config);
            this.platforms[platform] = config;
            return true;
        } catch (error) {
            console.error("添加模型失败:", error);
            return false;
        }
    }

    async removeModel(platform: string, modelId: string): Promise<boolean> {
        try {
            const config = this.getPlatform(platform);
            if (!config) throw new Error("平台不存在");

            const modelIndex = config.models.findIndex((model) => model.id === modelId);
            if (modelIndex === -1) throw new Error("模型不存在");

            config.models.splice(modelIndex, 1);
            await this.deleteModelRequestConfig(platform, modelId);
            await this.savePlatformConfig(platform, config);
            this.platforms[platform] = config;
            return true;
        } catch (error) {
            console.error("移除模型失败:", error);
            return false;
        }
    }

    async generateModelRequestConfig(platform: string, modelId: string): Promise<void> {
        const defaultConfig = await this.getDefaultRequestConfig();
        const requestConfig: Record<string, unknown> = {
            ...defaultConfig,
            model: modelId,
        };

        const { response } = await TrpgApi.requestWithResponse<ApiResponse>("/api/config/aimodel/save", {
            method: "POST",
            body: {
                platform,
                modelId,
                content: requestConfig,
            },
        });

        if (!response.ok) {
            throw new Error("保存模型请求配置失败");
        }
        console.log(`模型请求配置已生成: config/aimodel/${platform}/${modelId}.json`);
    }

    async deleteModelRequestConfig(platform: string, modelId: string): Promise<void> {
        try {
            const { response } = await TrpgApi.requestWithResponse<ApiResponse>("/api/config/aimodel/delete", {
                method: "POST",
                body: {
                    platform,
                    modelId,
                },
            });

            if (!response.ok) {
                throw new Error("删除模型请求配置失败");
            }
            console.log(`模型请求配置已删除: config/aimodel/${platform}/${modelId}.json`);
        } catch (error) {
            console.error("删除模型请求配置失败:", error);
        }
    }

    async getDefaultRequestConfig(): Promise<Record<string, unknown>> {
        try {
            const response = await fetch("config/aiplatform/default-request.json");
            if (!response.ok) throw new Error("无法加载默认模型请求配置");
            const parsed = await response.json() as unknown;
            return aiPlatformIsRecord(parsed) ? parsed : {};
        } catch (error) {
            console.error("获取默认模型请求配置失败:", error);
            return {};
        }
    }

    async testAPI(platform: string, modelId: string): Promise<AITestResult> {
        try {
            const config = this.getPlatform(platform);
            if (!config) throw new Error("平台配置不存在");
            if (!config.enabled) throw new Error("平台未启用");
            if (!config.config.api_key && platform !== "lmstudio") throw new Error("API Key 未设置");

            const model = config.models.find((item) => item.id === modelId);
            if (!model) throw new Error("模型不存在");

            const startTime = Date.now();
            const testRequest = {
                model: modelId,
                ...getTestRequestConfig(modelId),
            };

            console.log("API 测试请求:", testRequest);
            const { response, data } = await TrpgApi.requestWithResponse<AIPlatformTestResponse>(
                `/api/config/aiplatform/${platform}/test`,
                {
                    method: "POST",
                    body: testRequest,
                    timeout: config.config.timeout * 1000,
                },
            );

            const duration = (Date.now() - startTime) / 1000;
            if (!response.ok || !data.success) {
                throw new Error(data.error || data.message || `API 请求失败: ${response.status}`);
            }

            const result = data.response;
            const totalTokens = extractTotalTokens(result);
            const tokenSpeed = duration > 0 ? totalTokens / duration : 0;

            return {
                success: true,
                time: new Date().toLocaleString(),
                model: model.name,
                speed: `${tokenSpeed.toFixed(2)} token/s`,
                consumption: `${totalTokens} tokens`,
                duration: `${duration.toFixed(2)}s`,
                response: result,
            };
        } catch (error) {
            console.error("API 测试失败:", error);
            return {
                success: false,
                error: aiPlatformErrorMessage(error),
            };
        }
    }

    private async loadPlatform(platform: string): Promise<AIPlatformConfig | null> {
        try {
            const response = await fetch(`${this.platformsPath}/${platform}.json`);
            if (!response.ok) throw new Error(`无法加载平台配置: ${platform}`);
            const config = await response.json() as unknown;
            if (!isAIPlatformConfig(config)) throw new Error(`平台配置格式错误: ${platform}`);
            this.platforms[platform] = config;
            return config;
        } catch (error) {
            console.error(`加载平台 ${platform} 失败:`, error);
            return null;
        }
    }
}

interface AIPlatformTestResponse extends ApiResponse {
    response?: unknown;
}

function aiPlatformIsRecord(value: unknown): value is Record<string, unknown> {
    return typeof value === "object" && value !== null;
}

function isAIPlatformConfig(value: unknown): value is AIPlatformConfig {
    if (!aiPlatformIsRecord(value)) return false;
    return typeof value.platform === "string"
        && typeof value.name === "string"
        && typeof value.description === "string"
        && typeof value.icon === "string"
        && typeof value.enabled === "boolean"
        && aiPlatformIsRecord(value.config)
        && typeof value.config.base_url === "string"
        && typeof value.config.timeout === "number"
        && Array.isArray(value.models)
        && value.models.every(isAIModelConfig);
}

function isAIModelConfig(value: unknown): value is AIModelConfig {
    if (!aiPlatformIsRecord(value)) return false;
    return typeof value.id === "string"
        && typeof value.name === "string"
        && typeof value.description === "string"
        && typeof value.enabled === "boolean";
}

function extractTotalTokens(result: unknown): number {
    if (!aiPlatformIsRecord(result)) return 0;
    const usage = aiPlatformIsRecord(result.usage) ? result.usage : null;
    if (usage && typeof usage.total_tokens === "number") return usage.total_tokens;

    const output = aiPlatformIsRecord(result.output) ? result.output : null;
    const outputUsage = output && aiPlatformIsRecord(output.usage) ? output.usage : null;
    return outputUsage && typeof outputUsage.total_tokens === "number" ? outputUsage.total_tokens : 0;
}

function aiPlatformErrorMessage(error: unknown): string {
    return error instanceof Error ? error.message : String(error);
}

const aiPlatformManager = new AIPlatformManager();
window.aiPlatformManager = aiPlatformManager;
