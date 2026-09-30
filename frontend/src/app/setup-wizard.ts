namespace SetupWizard {
    interface SetupStatusData {
        setup_required?: boolean;
        owner_exists?: boolean;
        site_name?: string;
        site_domain?: string;
    }

    const TOTAL_STEPS = 5;
    const SKIPPABLE_STEPS = [1, 3];
    const DEFAULT_SITE_NAME = "AI TRPG";
    const DISMISS_STORAGE_KEY = "trpg_setup_dismissed";
    let currentStep = 1;
    let brandingName = "";
    let brandingBound = false;
    let wizardBound = false;
    let siteName = "";
    let siteDomain = "";
    let aiPlatform = "";
    let aiModel = "";
    let skipPromise: Promise<void> | null = null;
    let skipResolver: (() => void) | null = null;

    export async function init(): Promise<boolean> {
        try {
            const status = await TrpgApi.get<ApiResponse<SetupStatusData>>("/api/setup/status");
            const data = status.data;
            applySiteBranding(data?.site_name || "");
            // 已在本浏览器跳过引导时不再弹出（服务端状态未及时更新也能生效）。
            if (status.success && data && data.setup_required && !isDismissedLocally()) {
                startWizard();
                return true;
            }
        } catch (error) {
            console.error("[setup] 无法获取初始化状态", error);
        }
        return false;
    }

    function isDismissedLocally(): boolean {
        try {
            return localStorage.getItem(DISMISS_STORAGE_KEY) === "true";
        } catch {
            return false;
        }
    }

    function markDismissedLocally(): void {
        try {
            localStorage.setItem(DISMISS_STORAGE_KEY, "true");
        } catch {
            // 存储不可用时仍可通过服务端状态避免重复弹出。
        }
    }

    /** 用户点击“跳过全部引导”后完成，调用方据此继续初始化主应用。 */
    export function whenSkipped(): Promise<void> {
        if (!skipPromise) {
            skipPromise = new Promise<void>((resolve) => {
                skipResolver = resolve;
            });
        }
        return skipPromise;
    }

    export function applySiteBranding(name: string): void {
        brandingName = name || "";
        if (!brandingBound) {
            brandingBound = true;
            window.addEventListener("trpg:locale-changed", () => window.setTimeout(renderBranding, 0));
        }
        renderBranding();
    }

    function renderBranding(): void {
        if (!brandingName) return;
        document.title = brandingName;
        document.querySelectorAll<HTMLElement>("[data-i18n='app.title']").forEach((element) => {
            element.textContent = brandingName;
        });
    }

    function startWizard(): void {
        const wizard = document.getElementById("setupWizard");
        if (!wizard) {
            console.error("[setup] 未找到引导向导容器");
            return;
        }
        // 引导期间隐藏登录弹窗，避免登录流程与首次初始化冲突。
        const authModal = document.getElementById("auth-modal");
        if (authModal) authModal.style.display = "none";
        wizard.hidden = false;
        if (!wizardBound) {
            wizardBound = true;
            bindEvents();
        }
        prefillAiDefaults();
        prefillSiteName();
        renderStep(1);
    }

    /** 填入默认网站名称，用户直接点击“下一步”时即采用该名称。 */
    function prefillSiteName(): void {
        const field = byId<HTMLInputElement>("setupSiteName");
        if (field && !field.value.trim()) {
            field.value = DEFAULT_SITE_NAME;
        }
    }

    /** 跳过全部引导：关闭向导并让主应用继续初始化。 */
    function skipAll(): void {
        markDismissedLocally();
        // 通知服务端记录“已跳过”，避免刷新后再次弹出；失败也不影响本地跳过。
        void TrpgApi.post<ApiResponse>("/api/setup/dismiss", {}).catch(() => undefined);
        const wizard = document.getElementById("setupWizard");
        if (wizard) wizard.hidden = true;
        if (skipResolver) {
            const resolve = skipResolver;
            skipResolver = null;
            resolve();
        }
    }

    function bindEvents(): void {
        byId("setupPrevBtn")?.addEventListener("click", () => {
            if (currentStep > 1) renderStep(currentStep - 1);
        });
        byId("setupNextBtn")?.addEventListener("click", () => {
            void handleNext();
        });
        byId("setupSkipBtn")?.addEventListener("click", () => {
            handleSkip();
        });
        byId("setupFinishBtn")?.addEventListener("click", () => {
            window.location.reload();
        });
        byId("setupSkipAllBtn")?.addEventListener("click", () => {
            skipAll();
        });
        byId("setupAiTestBtn")?.addEventListener("click", () => {
            void testAiConnection();
        });
        byId("setupPlatform")?.addEventListener("change", prefillAiDefaults);
    }

    function prefillAiDefaults(): void {
        const select = byId("setupPlatform") as HTMLSelectElement | null;
        if (!select) return;
        const option = select.selectedOptions[0];
        if (!option) return;
        setValue("setupBaseUrl", option.dataset.baseUrl || "");
        setValue("setupModel", option.dataset.model || "");
    }

    function renderStep(step: number): void {
        currentStep = step;
        document.querySelectorAll<HTMLElement>(".setup-panel").forEach((panel) => {
            panel.classList.toggle("is-active", panel.dataset.setupStep === String(step));
        });
        document.querySelectorAll<HTMLElement>(".setup-progress-step").forEach((dot) => {
            const value = Number(dot.dataset.step || "0");
            dot.classList.toggle("is-done", value < step);
            dot.classList.toggle("is-active", value === step);
        });
        setHidden("setupPrevBtn", step <= 1);
        setHidden("setupNextBtn", step >= TOTAL_STEPS);
        setHidden("setupFinishBtn", step < TOTAL_STEPS);
        setHidden("setupSkipBtn", !SKIPPABLE_STEPS.includes(step));
        setMessage("");
        if (step === TOTAL_STEPS) renderSummary();
    }

    async function handleNext(): Promise<void> {
        try {
            if (currentStep === 1) {
                if (!(await saveAiStep())) return;
                renderStep(2);
            } else if (currentStep === 2) {
                if (!(await saveSiteStep())) return;
                renderStep(3);
            } else if (currentStep === 3) {
                if (!(await saveSiteStep())) return;
                renderStep(4);
            } else if (currentStep === 4) {
                if (!(await createOwnerStep())) return;
                renderStep(5);
            }
        } catch (error) {
            setMessage(errorMessage(error), "error");
        }
    }

    function handleSkip(): void {
        if (currentStep === 1) {
            renderStep(2);
            setMessage(msg("setup.msg.ai_skipped", "已跳过 AI 配置，可稍后在“设置 - 模型设置”中补充。"), "success");
            return;
        }
        if (currentStep === 3) {
            renderStep(4);
        }
    }

    async function saveAiStep(): Promise<boolean> {
        const platform = value("setupPlatform") || "custom";
        const baseUrl = value("setupBaseUrl").trim();
        const apiKey = value("setupApiKey").trim();
        const model = value("setupModel").trim();
        if (!baseUrl && !apiKey && !model) {
            return true;
        }
        if (!baseUrl || !model) {
            setMessage(msg("setup.error.ai_required", "请填写 API 地址和模型 ID。"), "error");
            return false;
        }
        if (!apiKey && platform !== "lmstudio") {
            setMessage(msg("setup.error.api_key_required", "请填写 API Key。"), "error");
            return false;
        }

        const response = await TrpgApi.post<ApiResponse<{ platform?: string; model?: string }>>("/api/setup/ai", {
            platform,
            base_url: baseUrl,
            api_key: apiKey,
            model,
        });
        if (!response.success) {
            setMessage(backendMessage(response.message || response.error || "", msg("setup.error.ai_save_failed", "保存 AI 配置失败")), "error");
            return false;
        }
        aiPlatform = platform;
        aiModel = model;
        return true;
    }

    async function saveSiteStep(): Promise<boolean> {
        const domain = value("setupSiteDomain").trim();
        const name = value("setupSiteName").trim() || DEFAULT_SITE_NAME;
        setValue("setupSiteName", name);

        const response = await TrpgApi.post<ApiResponse<{ name?: string; domain?: string }>>("/api/setup/site", {
            name,
            domain,
        });
        if (!response.success) {
            setMessage(backendMessage(response.message || response.error || "", msg("setup.error.site_save_failed", "保存网站信息失败")), "error");
            return false;
        }
        siteName = name;
        siteDomain = domain;
        return true;
    }

    async function createOwnerStep(): Promise<boolean> {
        const username = value("setupOwnerUsername").trim();
        const email = value("setupOwnerEmail").trim();
        const password = value("setupOwnerPassword");
        const confirm = value("setupOwnerConfirm");
        if (!username || !email || !password) {
            setMessage(msg("setup.error.owner_incomplete", "请完整填写 Owner 账号信息。"), "error");
            return false;
        }
        if (password !== confirm) {
            setMessage(msg("setup.error.password_mismatch", "两次输入的密码不一致。"), "error");
            return false;
        }

        const response = await TrpgApi.post<ApiResponse<{ username?: string }>>("/api/setup/owner", {
            username,
            email,
            password,
            confirm_password: confirm,
        });
        if (!response.success) {
            setMessage(backendMessage(response.message || response.error || "", msg("setup.error.owner_create_failed", "创建 Owner 账号失败")), "error");
            return false;
        }
        return true;
    }

    async function testAiConnection(): Promise<void> {
        const platform = value("setupPlatform") || "custom";
        const baseUrl = value("setupBaseUrl").trim();
        const apiKey = value("setupApiKey").trim();
        const model = value("setupModel").trim();
        if (!baseUrl || !model) {
            setMessage(msg("setup.test.required", "请先填写 API 地址和模型 ID。"), "error");
            return;
        }

        setMessage(msg("setup.test.testing", "正在测试连接…"), "");
        try {
            const response = await TrpgApi.post<ApiResponse>("/api/setup/ai/test", {
                platform,
                base_url: baseUrl,
                api_key: apiKey,
                model,
            });
            if (response.success) {
                setMessage(msg("setup.test.success", "连接成功。"), "success");
            } else {
                setMessage(backendMessage(response.error || response.message || "", msg("setup.test.failure", "连接失败，请检查配置。")), "error");
            }
        } catch (error) {
            setMessage(errorMessage(error), "error");
        }
    }

    function renderSummary(): void {
        const summary = byId("setupSummary");
        if (!summary) return;
        const rows: Array<[string, string]> = [
            [msg("setup.summary.platform", "AI 平台"), aiPlatform || msg("setup.summary.unset", "未配置")],
            [msg("setup.summary.model", "模型"), aiModel || msg("setup.summary.unset", "未配置")],
            [msg("setup.summary.site_name", "网站名称"), siteName || "-"],
            [msg("setup.summary.domain", "域名"), siteDomain || msg("setup.summary.domain_unbound", "未绑定")],
        ];
        summary.innerHTML = rows
            .map(([label, content]) => `<li><span>${escapeHtml(label)}</span><strong>${escapeHtml(content)}</strong></li>`)
            .join("");
    }

    function byId<T extends HTMLElement = HTMLElement>(id: string): T | null {
        return document.getElementById(id) as T | null;
    }

    function value(id: string): string {
        const element = document.getElementById(id) as HTMLInputElement | HTMLSelectElement | null;
        return element?.value || "";
    }

    function setValue(id: string, content: string): void {
        const element = document.getElementById(id) as HTMLInputElement | null;
        if (element && element.value !== content) element.value = content;
    }

    function setHidden(id: string, hidden: boolean): void {
        const element = document.getElementById(id);
        if (element) element.hidden = hidden;
    }

    function setMessage(content: string, kind: "" | "error" | "success" = ""): void {
        const element = document.getElementById("setupMessage");
        if (!element) return;
        element.textContent = content;
        element.className = `setup-message${kind ? ` is-${kind}` : ""}`;
    }

    function escapeHtml(content: string): string {
        const element = document.createElement("div");
        element.textContent = content;
        return element.innerHTML;
    }

    function msg(key: string, fallback: string): string {
        return window.TrpgI18n?.t(key, fallback) || fallback;
    }

    /** 引导相关后端提示（英文）到 i18n key 的映射。 */
    const SETUP_BACKEND_KEYS: Record<string, string> = {
        "Setup already completed": "setup.backend.locked",
        "Site name is required": "setup.backend.site_name_required",
        "Site name is too long": "setup.backend.site_name_too_long",
        "Domain is too long": "setup.backend.domain_too_long",
        "Base URL and model are required": "setup.backend.ai_incomplete",
        "Invalid platform id": "setup.backend.platform_invalid",
        "Failed to create owner account": "setup.backend.owner_create_failed",
    };

    /** 把后端返回的提示转换为当前语言；未知提示复用认证模块的映射，仍无法匹配则原样返回。 */
    function backendMessage(message: string, fallback: string): string {
        if (!message) {
            return fallback;
        }
        const key = SETUP_BACKEND_KEYS[message];
        if (key) {
            return msg(key, message);
        }
        return AuthModule.localizedAuthMessage({ success: false, message }, fallback);
    }

    function errorMessage(error: unknown): string {
        return error instanceof Error ? error.message : String(error);
    }
}