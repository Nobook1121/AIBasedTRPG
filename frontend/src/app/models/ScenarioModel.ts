class ScenarioModel {
    scenarios: Scenario[] = [];
    apiBaseUrl = "/api";
    userId: string | number | null = null;
    isAuthenticated = false;

    getCurrentUserId(): string | number | null {
        return this.userId;
    }

    async checkAuthStatus(): Promise<boolean> {
        try {
            const { response, data } = await TrpgApi.requestWithResponse<ApiResponse<{ user_id: string | number }>>("/api/auth/status");
            if (response.ok && data.success && data.data) {
                this.userId = data.data.user_id;
                this.isAuthenticated = true;
                return true;
            }
        } catch (error) {
            console.error("检查认证状态失败:", error);
        }
        this.userId = null;
        this.isAuthenticated = false;
        return false;
    }

    async init(): Promise<Scenario[]> {
        await this.checkAuthStatus();
        return this.loadScenarios();
    }

    async loadScenarios(): Promise<Scenario[]> {
        this.scenarios = [];

        try {
            const { response, data } = await TrpgApi.requestWithResponse<ApiResponse<unknown>>(`${this.apiBaseUrl}/scenarios`);
            if (response.ok && data.success && Array.isArray(data.data)) {
                this.scenarios = data.data.filter(isScenario);
                this.saveScenarios();
                return this.scenarios;
            }
            console.warn("剧本 API 返回异常:", data.message || data.error || response.status);
        } catch (error) {
            console.warn("从 API 加载剧本失败，尝试使用本地缓存:", error);
        }

        this.scenarios = this.loadCachedScenarios();
        return this.scenarios;
    }

    async createScenario(scenarioData: ScenarioInput): Promise<Scenario> {
        if (!this.isAuthenticated) {
            await this.checkAuthStatus();
        }

        const { response, data } = await TrpgApi.requestWithResponse<ApiResponse<unknown>>(`${this.apiBaseUrl}/scenarios`, {
            method: "POST",
            body: {
                ...scenarioData,
                user_id: this.userId || "anonymous",
            },
        });

        if (!response.ok || !data.success || !isScenario(data.data)) {
            throw new Error(data.message || data.error || `API 请求失败: ${response.status}`);
        }

        this.scenarios.push(data.data);
        this.saveScenarios();
        return data.data;
    }

    async updateScenario(id: number, scenarioData: ScenarioInput): Promise<Scenario> {
        if (!this.isAuthenticated) {
            const authenticated = await this.checkAuthStatus();
            if (!authenticated) throw new Error("请先登录");
        }

        const { response, data } = await TrpgApi.requestWithResponse<ApiResponse<unknown>>(`${this.apiBaseUrl}/scenarios/${id}`, {
            method: "PUT",
            body: {
                ...scenarioData,
                user_id: this.userId,
            },
        });

        if (!response.ok || !data.success || !isScenario(data.data)) {
            throw new Error(data.message || data.error || `API 请求失败: ${response.status}`);
        }

        const index = this.scenarios.findIndex((scenario) => scenario.id === id);
        if (index === -1) throw new Error("剧本不存在");
        this.scenarios[index] = data.data;
        this.saveScenarios();
        return data.data;
    }

    async deleteScenario(id: number): Promise<boolean> {
        if (!this.isAuthenticated) {
            const authenticated = await this.checkAuthStatus();
            if (!authenticated) throw new Error("请先登录");
        }

        const { response, data } = await TrpgApi.requestWithResponse<ApiResponse>(`${this.apiBaseUrl}/scenarios/${id}`, {
            method: "DELETE",
            body: {
                user_id: this.userId,
            },
        });

        if (!response.ok || !data.success) {
            throw new Error(data.message || data.error || `API 请求失败: ${response.status}`);
        }

        const index = this.scenarios.findIndex((scenario) => scenario.id === id);
        if (index === -1) throw new Error("剧本不存在");
        this.scenarios.splice(index, 1);
        this.saveScenarios();
        return true;
    }

    getScenario(id: number): Scenario | undefined {
        return this.scenarios.find((scenario) => scenario.id === id);
    }

    getScenarios(): Scenario[] {
        return this.scenarios;
    }

    saveScenarios(): void {
        localStorage.setItem("trpg_scenarios", JSON.stringify(this.scenarios));
    }

    async importScenario(scenarioData: unknown): Promise<Scenario> {
        if (!this.validateScenarioData(scenarioData)) {
            throw new Error("剧本数据格式不正确");
        }

        const { id: _ignoredId, ...input } = scenarioData;
        void _ignoredId;
        return this.createScenario(input);
    }

    validateScenarioData(data: unknown): data is ScenarioInput {
        return isScenarioInput(data);
    }

    private loadCachedScenarios(): Scenario[] {
        const storedScenarios = localStorage.getItem("trpg_scenarios");
        if (!storedScenarios) return [];

        try {
            const parsed = JSON.parse(storedScenarios) as unknown;
            return Array.isArray(parsed) ? parsed.filter(isScenario) : [];
        } catch (error) {
            console.warn("本地剧本缓存解析失败:", error);
            return [];
        }
    }
}

function isRecord(value: unknown): value is Record<string, unknown> {
    return typeof value === "object" && value !== null;
}

function isScenarioSegment(value: unknown): value is ScenarioSegment {
    if (!isRecord(value)) return false;
    return typeof value.id === "number"
        && typeof value.content === "string"
        && typeof value.marker === "string";
}

function normalizeSegmentList(value: unknown): ScenarioSegment[] {
    if (!Array.isArray(value)) return [];
    return value.filter(isScenarioSegment);
}

function isScenarioInput(data: unknown): data is ScenarioInput {
    if (!isRecord(data)) return false;
    if (typeof data.title !== "string" || !data.title.trim()) return false;
    if (typeof data.author !== "string" || !data.author.trim()) return false;

    const playerCount = data.playerCount;
    if (typeof playerCount !== "number" || !Number.isFinite(playerCount)) return false;

    if (data.scenes !== undefined && !Array.isArray(data.scenes)) return false;
    if (data.endings !== undefined && !Array.isArray(data.endings)) return false;
    return true;
}

function isScenario(data: unknown): data is Scenario {
    if (!isScenarioInput(data) || !isRecord(data)) return false;
    if (typeof data.id !== "number") return false;

    const scenes = normalizeSegmentList(data.scenes);
    const endings = normalizeSegmentList(data.endings);
    if ((Array.isArray(data.scenes) && scenes.length !== data.scenes.length)
        || (Array.isArray(data.endings) && endings.length !== data.endings.length)) {
        return false;
    }
    return true;
}

window.ScenarioModel = ScenarioModel;
