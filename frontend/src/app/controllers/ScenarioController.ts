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
            onSaveScenario: () => this.onSaveScenario(),
            onPreviewScenario: (id) => this.onPreviewScenario(id),
            onEditScenario: (id) => this.onEditScenario(id),
            onDeleteScenario: (id) => this.onDeleteScenario(id),
            onImportScenario: (files) => this.onImportScenario(files),
        });
    }

    private renderScenarioList(): void {
        this.view.renderScenarioList(this.model.getScenarios());
    }

    private onCreateScenarioClick(): void {
        window.setCurrentEditingScenarioId?.(null);
        this.view.openCreateModal();
    }

    private async onSaveScenario(): Promise<void> {
        try {
            const scenarioData = this.view.getFormData();
            const scenario = await this.model.createScenario(scenarioData);

            const coverUrl = inputValue("scenarioCoverUrl");
            await this.renameScenarioCover(scenario, coverUrl, "title");

            const scenarioIndex = this.model.scenarios.findIndex((item) => item.id === scenario.id);
            if (scenarioIndex !== -1) {
                this.model.scenarios[scenarioIndex] = scenario;
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
                await this.renameScenarioCover(tempScenario, scenarioData.cover || "", "id");
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

    private async onDeleteScenario(id: number): Promise<void> {
        if (!confirm("确定要删除这个剧本吗？")) return;

        try {
            const scenario = this.model.getScenario(id);
            if (scenario) {
                const coverPath = scenario.cover || DEFAULT_SCENARIO_COVER;
                try {
                    await TrpgApi.del<ApiResponse>("/api/scenarios/cover", {
                        body: {
                            cover_path: coverPath,
                        },
                    });
                } catch (coverError) {
                    console.error("删除封面时出错:", coverError);
                }
            }

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
        namingStrategy: "title" | "id" = "title",
    ): Promise<T> {
        if (!coverUrl || coverUrl === DEFAULT_SCENARIO_COVER) {
            scenario.cover = DEFAULT_SCENARIO_COVER;
            return scenario;
        }

        if (!coverUrl.startsWith("/assets/scenario_covers/")) {
            scenario.cover = DEFAULT_SCENARIO_COVER;
            return scenario;
        }

        try {
            const oldCoverFilename = coverUrl.split("/").pop();
            if (!oldCoverFilename) {
                scenario.cover = DEFAULT_SCENARIO_COVER;
                return scenario;
            }

            const newCoverFilename = namingStrategy === "title"
                ? `${String(scenario.title || "").replace(/[\/\\]/g, "_")}.png`
                : `${scenario.id}.png`;

            if (oldCoverFilename === newCoverFilename) {
                scenario.cover = `/assets/scenario_covers/${newCoverFilename}`;
                return scenario;
            }

            const data = await TrpgApi.post<ApiResponse>("/api/scenarios/cover/rename", {
                old_filename: oldCoverFilename,
                new_filename: newCoverFilename,
            });

            scenario.cover = data.success
                ? `/assets/scenario_covers/${newCoverFilename}`
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

function scenarioErrorMessage(error: unknown): string {
    return error instanceof Error ? error.message : String(error);
}

window.ScenarioController = ScenarioController;
