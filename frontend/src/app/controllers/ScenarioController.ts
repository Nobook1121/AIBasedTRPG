class ScenarioController {
    private readonly model: ScenarioModel;
    private readonly view: ScenarioView;

    constructor() {
        this.model = new ScenarioModel();
        this.view = new ScenarioView();
        this.bindEventHandlers();
        void this.init();
    }

    private async init(): Promise<void> {
        try {
            await this.model.init();
            this.renderScenarioList();
        } catch (error) {
            console.error("初始化剧本控制器时出错:", error);
            this.view.showMessage(`初始化失败: ${scenarioErrorMessage(error)}`, true);
        }
    }

    private bindEventHandlers(): void {
        this.view.setEventHandlers({
            onCreateScenarioClick: () => this.onCreateScenarioClick(),
            onImportScenarioDocumentClick: () => this.onImportScenarioDocumentClick(),
            onImportScenarioDocument: (file) => this.onImportScenarioDocument(file),
            onSaveScenario: () => this.onSaveScenario(),
            onSaveDraft: () => this.onSaveDraft(),
            onPreviewScenario: (id) => this.onPreviewScenario(id),
            onEditScenario: (id) => this.onEditScenario(id),
            onPlayScenario: (id) => this.onPlayScenario(id),
            onDeleteScenario: (id) => this.onDeleteScenario(id),
            onImportScenario: (files) => this.onImportScenario(files),
        });
    }

    private renderScenarioList(): void {
        this.view.renderScenarioList(this.model.getScenarios());
    }

    refresh(): void {
        this.renderScenarioList();
    }

    private async onCreateScenarioClick(): Promise<void> {
        window.setCurrentEditingScenarioId?.(null);
        try {
            const draft = await this.model.loadDraft();
            if (draft) {
                const draftAction = await this.view.showDraftPrompt();
                if (draftAction === "cancel") return;
                this.view.openCreateModal();
                if (draftAction === "continue") {
                    this.view.fillDraftData?.(draft);
                } else if (draftAction === "discard") {
                    await this.model.discardDraft();
                }
                return;
            }
        } catch (error) {
            console.warn("加载剧本草稿失败", error);
        }
        this.view.openCreateModal();
    }

    private async onImportScenarioDocumentClick(): Promise<void> {
        window.setCurrentEditingScenarioId?.(null);
        try {
            const draft = await this.model.loadDraft();
            if (draft) {
                const draftAction = await this.view.showDraftPrompt();
                if (draftAction === "cancel") return;
                if (draftAction === "continue") {
                    this.view.openCreateModal();
                    this.view.fillDraftData?.(draft);
                    this.view.showMessage("请先完成或舍弃当前草稿，再导入新的剧本文档");
                    return;
                }
                await this.model.discardDraft();
            }
        } catch (error) {
            console.warn("加载剧本草稿失败", error);
        }
        inputElement("importScenarioDocumentFile")?.click();
    }

    private async onImportScenarioDocument(file: File): Promise<void> {
        const extension = file.name.toLowerCase().split(".").pop() || "";
        if (!["doc", "docx", "txt", "md", "markdown", "text"].includes(extension)) {
            this.view.showMessage("仅支持 doc、docx、txt、md 文档", true);
            return;
        }
        this.view.showConversionProgress(file.name);
        this.view.updateConversionProgress(0, "active");
        try {
            await new Promise((resolve) => window.setTimeout(resolve, 120));
            this.view.updateConversionProgress(0, "complete");
            this.view.updateConversionProgress(1, "active");
            const title = file.name.replace(/\.[^.]+$/, "") || "Imported scenario";
            const converted = await this.model.convertScriptFile(file, title);
            this.view.updateConversionProgress(1, "complete");
            this.view.updateConversionProgress(2, "active");
            await new Promise((resolve) => window.setTimeout(resolve, 120));
            this.view.updateConversionProgress(2, "complete");
            this.view.updateConversionProgress(3, "active");
            await new Promise((resolve) => window.setTimeout(resolve, 120));
            this.view.updateConversionProgress(3, "complete");
            await new Promise((resolve) => window.setTimeout(resolve, 180));
            this.view.closeConversionProgress();
            await this.view.openCreateModal();
            this.view.fillDraftData(converted);
            const conversionStatus = (converted as ScenarioInput & { conversion?: { ai?: { status?: string } } }).conversion?.ai?.status;
            this.view.showMessage(conversionStatus === "fallback"
                ? "AI 转换暂时超时，已使用本地结构化结果填入创建剧本窗口，请检查后发布"
                : "文档转换完成，已填入创建剧本窗口，请检查后发布");
        } catch (error) {
            this.view.updateConversionProgress(1, "error", scenarioErrorMessage(error));
            await new Promise((resolve) => window.setTimeout(resolve, 500));
            this.view.closeConversionProgress();
            this.view.showMessage(`剧本文档转换失败：${scenarioErrorMessage(error)}`, true);
        }
    }

    private async onSaveDraft(): Promise<void> {
        try { await this.model.saveDraft(this.view.getDraftData()); this.view.showMessage("剧本草稿已保存"); }
        catch (error) { this.view.showMessage(scenarioErrorMessage(error), true); }
    }

    private async onSaveScenario(): Promise<void> {
        try {
            const scenarioData = this.view.getFormData();
            const scenario = await this.model.createScenario(scenarioData);
            await this.model.discardDraft().catch(() => undefined);

            const coverUrl = inputValue("scenarioCoverUrl");
            await this.renameScenarioCover(scenario, coverUrl);
            scenarioData.cover = scenario.cover || DEFAULT_SCENARIO_COVER;
            const savedScenario = await this.model.updateScenario(scenario.id, {
                ...scenarioData,
                id: scenario.id,
            });

            const scenarioIndex = this.model.scenarios.findIndex((item) => item.id === scenario.id);
            if (scenarioIndex !== -1) {
                this.model.scenarios[scenarioIndex] = savedScenario;
                this.model.saveScenarios();
            }

            this.renderScenarioList();
            this.view.closeModal();
            this.view.showMessage("剧本保存成功");

            setTimeout(() => {
                location.reload();
            }, 1000);
        } catch (error) {
            console.error("保存剧本时出错:", error);
            this.view.showMessage(scenarioErrorMessage(error), true);
        }
    }

    private onPreviewScenario(id: number): void {
        const scenario = this.model.getScenario(id);
        if (scenario) {
            this.view.previewScenario(scenario);
        } else {
            this.view.showMessage("剧本不存在", true);
        }
    }

    private onEditScenario(id: number): void {
        const scenario = this.model.getScenario(id);
        if (!scenario) {
            this.view.showMessage("剧本不存在", true);
            return;
        }

        window.setCurrentEditingScenarioId?.(id);
        this.view.openEditModal(scenario);

        const saveButton = document.getElementById("saveScenario");
        if (!saveButton) return;

        saveButton.removeEventListener("click", this.view.saveScenarioHandler);
        saveButton.onclick = async () => {
            try {
                const scenarioData = this.view.getFormData();
                const tempScenario: Pick<Scenario, "id" | "cover" | "title"> = {
                    id,
                    title: scenarioData.title,
                    cover: scenarioData.cover || DEFAULT_SCENARIO_COVER,
                };
                await this.renameScenarioCover(tempScenario, scenarioData.cover || "");
                scenarioData.cover = tempScenario.cover || DEFAULT_SCENARIO_COVER;

                const updatedScenario = await this.model.updateScenario(id, scenarioData);
                void updatedScenario;

                saveButton.addEventListener("click", this.view.saveScenarioHandler);
                this.renderScenarioList();
                this.view.closeModal();
                this.view.showMessage("剧本更新成功");
            } catch (error) {
                console.error("更新剧本时出错:", error);
                this.view.showMessage(scenarioErrorMessage(error), true);
                saveButton.addEventListener("click", this.view.saveScenarioHandler);
            }
        };
    }

    private onPlayScenario(id: number): void {
        window.switchMainTab?.("save");
        void window.openCreateRoomWithScenario?.(id);
    }

    private async onDeleteScenario(id: number): Promise<void> {
        if (!confirm("确定要删除这个剧本吗？")) return;

        try {
            await this.model.deleteScenario(id);
            this.renderScenarioList();
            this.view.showMessage("剧本删除成功");
        } catch (error) {
            console.error("删除剧本时出错:", error);
            this.view.showMessage(`删除剧本失败: ${scenarioErrorMessage(error)}`, true);
        }
    }

    private async onImportScenario(files: FileList | null): Promise<void> {
        if (!files || files.length === 0) return;

        let successCount = 0;
        let errorCount = 0;
        const errors: string[] = [];

        for (const file of Array.from(files)) {
            try {
                const content = await this.readFile(file);
                await this.model.importScenario(JSON.parse(content) as unknown);
                successCount += 1;
            } catch (error) {
                errorCount += 1;
                errors.push(`"${file.name}": ${scenarioErrorMessage(error)}`);
                console.error(`导入文件 "${file.name}" 失败:`, error);
            }
        }

        this.renderScenarioList();

        if (successCount > 0 && errorCount === 0) {
            this.view.showMessage(`成功导入 ${successCount} 个剧本`);
        } else if (successCount > 0) {
            this.view.showMessage(`成功导入 ${successCount} 个剧本，${errorCount} 个失败。\n\n失败详情:\n${errors.join("\n")}`);
        } else {
            this.view.showMessage(`导入失败：\n\n错误详情:\n${errors.join("\n")}`, true);
        }
    }

    private readFile(file: File): Promise<string> {
        return new Promise((resolve, reject) => {
            const reader = new FileReader();
            reader.onload = () => resolve(String(reader.result || ""));
            reader.onerror = () => reject(new Error("文件读取失败"));
            reader.readAsText(file);
        });
    }

    async renameScenarioCover<T extends Pick<Scenario, "id" | "cover"> & Partial<Pick<Scenario, "title">>>(
        scenario: T,
        coverUrl: string,
    ): Promise<T> {
        if (!coverUrl || coverUrl === DEFAULT_SCENARIO_COVER) {
            scenario.cover = DEFAULT_SCENARIO_COVER;
            return scenario;
        }

        if (!coverUrl.startsWith("/assets/scenarios/") && !coverUrl.startsWith("/assets/scenario_covers/")) {
            scenario.cover = DEFAULT_SCENARIO_COVER;
            return scenario;
        }

        try {
            const oldCoverPath = coverUrl.startsWith("/assets/scenarios/")
                ? coverUrl.replace("/assets/scenarios/", "")
                : coverUrl.replace("/assets/scenario_covers/", "scenario-covers/");
            if (!oldCoverPath) {
                scenario.cover = DEFAULT_SCENARIO_COVER;
                return scenario;
            }

            const newCoverPath = `scenario-${scenario.id}/cover.png`;

            if (oldCoverPath === newCoverPath) {
                scenario.cover = `/assets/scenarios/${newCoverPath}`;
                return scenario;
            }

            const data = await TrpgApi.post<ApiResponse>("/api/scenarios/cover/rename", {
                old_path: oldCoverPath,
                new_path: newCoverPath,
            });

            scenario.cover = data.success
                ? `/assets/scenarios/${newCoverPath}`
                : DEFAULT_SCENARIO_COVER;
        } catch (error) {
            console.error("重命名封面文件时出错:", error);
            scenario.cover = DEFAULT_SCENARIO_COVER;
        }

        return scenario;
    }
}

const DEFAULT_SCENARIO_COVER = "/assets/scenario_covers/default_cover.png";

function inputValue(id: string): string {
    return (document.getElementById(id) as HTMLInputElement | HTMLTextAreaElement | null)?.value || "";
}

function inputElement(id: string): HTMLInputElement | null {
    const element = document.getElementById(id);
    return element instanceof HTMLInputElement ? element : null;
}

function scenarioErrorMessage(error: unknown): string {
    return error instanceof Error ? error.message : String(error);
}

window.ScenarioController = ScenarioController;
