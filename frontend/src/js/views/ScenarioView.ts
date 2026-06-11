class ScenarioView {
    scenarioList: HTMLElement;
    saveScenarioHandler: () => Promise<void>;
    private handlers: ScenarioViewHandlers | null = null;

    constructor() {
        const scenarioList = document.getElementById("scenarioList");
        if (!scenarioList) throw new Error("缺少 scenarioList 容器");
        this.scenarioList = scenarioList;
        this.saveScenarioHandler = async () => {
            await this.handlers?.onSaveScenario();
        };
        this.initEventListeners();
        this.bindScenarioActions();
    }

    setEventHandlers(handlers: ScenarioViewHandlers): void {
        this.handlers = handlers;
    }

    renderScenarioList(scenarios: Scenario[]): void {
        this.scenarioList.innerHTML = "";

        scenarios.forEach((scenario) => {
            const card = document.createElement("div");
            card.className = "scenario-card";
            const coverPath = safeScenarioCover(scenario.cover);

            card.innerHTML = `
                <img src="${scenarioEscapeHtml(coverPath)}" alt="${scenarioEscapeHtml(scenario.title)}" onerror="this.src='${DEFAULT_SCENARIO_COVER}'">
                <div class="scenario-card-body">
                    <div class="scenario-card-title">${scenarioEscapeHtml(scenario.title)}</div>
                    <p>作者: ${scenarioEscapeHtml(scenario.author)}</p>
                    <p>推荐人数: ${scenario.playerCount}</p>
                    <div class="scenario-card-actions">
                        <button class="btn btn-sm btn-primary preview-scenario" data-id="${scenario.id}">预览</button>
                        <button class="btn btn-sm btn-secondary edit-scenario" data-id="${scenario.id}">编辑</button>
                        <button class="btn btn-sm btn-danger delete-scenario" data-id="${scenario.id}">删除</button>
                    </div>
                </div>
            `;
            this.scenarioList.appendChild(card);
        });
    }

    openCreateModal(): void {
        const modalElement = requiredElement("scenarioModal");
        this.resetScenarioForm();
        this.bindRemoveEvents();
        new bootstrap.Modal(modalElement).show();
    }

    openEditModal(scenario: Scenario): void {
        const modalElement = requiredElement("scenarioModal");
        this.fillScenarioForm(scenario);
        this.bindRemoveEvents();
        new bootstrap.Modal(modalElement).show();
    }

    closeModal(): void {
        bootstrap.Modal.getInstance(document.getElementById("scenarioModal"))?.hide();
    }

    previewScenario(scenario: Scenario): void {
        let previewContent = `
            <h3>${scenarioEscapeHtml(scenario.title)}</h3>
            <p><strong>作者:</strong> ${scenarioEscapeHtml(scenario.author)}</p>
            <p><strong>推荐人数:</strong> ${scenario.playerCount}</p>
            <p><strong>备注:</strong> ${scenarioEscapeHtml(scenario.notes || "无")}</p>
            <p><strong>背景/引入:</strong> ${scenarioEscapeHtml(scenario.background || "无")}</p>
            <p><strong>游戏准备:</strong> ${scenarioEscapeHtml(scenario.preparation || "无")}</p>
            <h4>场景</h4>
        `;

        scenario.scenes.forEach((scene) => {
            previewContent += `
                <div class="mb-3">
                    <h5>场景 ${scene.id}</h5>
                    <p>${scenarioEscapeHtml(scene.content)}</p>
                    ${scene.marker ? `<p><strong>标记:</strong> ${scenarioEscapeHtml(scene.marker)}</p>` : ""}
                </div>
            `;
        });

        previewContent += "<h4>结局</h4>";

        scenario.endings.forEach((ending) => {
            previewContent += `
                <div class="mb-3">
                    <h5>结局 ${ending.id}</h5>
                    <p>${scenarioEscapeHtml(ending.content)}</p>
                    ${ending.marker ? `<p><strong>标记:</strong> ${scenarioEscapeHtml(ending.marker)}</p>` : ""}
                </div>
            `;
        });

        const modal = document.createElement("div");
        modal.className = "modal fade";
        modal.id = "previewModal";
        modal.tabIndex = -1;
        modal.innerHTML = `
            <div class="modal-dialog modal-lg">
                <div class="modal-content">
                    <div class="modal-header">
                        <h5 class="modal-title">剧本预览</h5>
                        <button type="button" class="btn-close" data-bs-dismiss="modal" aria-label="Close"></button>
                    </div>
                    <div class="modal-body">${previewContent}</div>
                    <div class="modal-footer">
                        <button type="button" class="btn btn-secondary" data-bs-dismiss="modal">关闭</button>
                    </div>
                </div>
            </div>
        `;

        document.body.appendChild(modal);
        new bootstrap.Modal(modal).show();
        modal.addEventListener("hidden.bs.modal", () => modal.remove());
    }

    getFormData(): ScenarioInput {
        const title = input("scenarioTitle").value.trim();
        const author = input("scenarioAuthor").value.trim();
        const playerCountRaw = input("scenarioPlayerCount").value;
        const playerCount = Number.parseInt(playerCountRaw, 10);

        if (!title || !author || !Number.isFinite(playerCount)) {
            throw new Error("请填写所有必填项");
        }

        return {
            title,
            author,
            playerCount,
            notes: textarea("scenarioNotes").value,
            background: textarea("scenarioBackground").value,
            preparation: textarea("scenarioPreparation").value,
            scenes: collectSegments(".scene-item"),
            endings: collectSegments(".ending-item"),
            cover: input("scenarioCoverUrl").value,
        };
    }

    showMessage(message: string, isError = false): void {
        const notification = document.createElement("div");
        notification.className = `notification ${isError ? "notification-error" : "notification-success"}`;
        notification.textContent = message;

        const container = document.querySelector(".notification-container");
        if (!container) return;
        container.appendChild(notification);

        setTimeout(() => notification.remove(), 3000);
    }

    private initEventListeners(): void {
        document.getElementById("createScenario")?.addEventListener("click", () => {
            this.handlers?.onCreateScenarioClick();
        });

        document.getElementById("importScenario")?.addEventListener("click", () => {
            input("importScenarioFile").click();
        });

        input("importScenarioFile").addEventListener("change", async (event) => {
            const target = event.target as HTMLInputElement;
            await this.handlers?.onImportScenario(target.files);
            target.value = "";
        });

        document.getElementById("saveScenario")?.addEventListener("click", this.saveScenarioHandler);
        document.getElementById("addScene")?.addEventListener("click", () => this.addScene());
        document.getElementById("addEnding")?.addEventListener("click", () => this.addEnding());
    }

    private bindScenarioActions(): void {
        this.scenarioList.addEventListener("click", async (event) => {
            const button = (event.target as HTMLElement).closest<HTMLButtonElement>("button");
            if (!button) return;

            const id = Number.parseInt(button.getAttribute("data-id") || "", 10);
            if (!Number.isFinite(id)) return;

            if (button.classList.contains("preview-scenario")) {
                this.handlers?.onPreviewScenario(id);
            } else if (button.classList.contains("edit-scenario")) {
                this.handlers?.onEditScenario(id);
            } else if (button.classList.contains("delete-scenario")) {
                await this.handlers?.onDeleteScenario(id);
            }
        });
    }

    private resetScenarioForm(): void {
        input("scenarioTitle").value = "";
        input("scenarioAuthor").value = "";
        input("scenarioPlayerCount").value = "0";
        textarea("scenarioNotes").value = "";
        textarea("scenarioBackground").value = "";
        textarea("scenarioPreparation").value = "";
        input("scenarioCoverUrl").value = "";
        image("coverPreview").src = DEFAULT_SCENARIO_COVER;
        requiredElement("scenarioScenes").innerHTML = segmentTemplate("scene", 1);
        requiredElement("scenarioEndings").innerHTML = segmentTemplate("ending", 1);
    }

    private fillScenarioForm(scenario: Scenario): void {
        input("scenarioTitle").value = scenario.title;
        input("scenarioAuthor").value = scenario.author;
        input("scenarioPlayerCount").value = String(scenario.playerCount);
        textarea("scenarioNotes").value = scenario.notes || "";
        textarea("scenarioBackground").value = scenario.background || "";
        textarea("scenarioPreparation").value = scenario.preparation || "";
        input("scenarioCoverUrl").value = scenario.cover || "";
        image("coverPreview").src = safeScenarioCover(scenario.cover);

        const scenesContainer = requiredElement("scenarioScenes");
        scenesContainer.innerHTML = "";
        scenario.scenes.forEach((scene, index) => {
            scenesContainer.insertAdjacentHTML("beforeend", segmentTemplate("scene", index + 1, scene));
        });

        const endingsContainer = requiredElement("scenarioEndings");
        endingsContainer.innerHTML = "";
        scenario.endings.forEach((ending, index) => {
            endingsContainer.insertAdjacentHTML("beforeend", segmentTemplate("ending", index + 1, ending));
        });
    }

    private bindRemoveEvents(): void {
        document.querySelectorAll<HTMLButtonElement>(".remove-scene").forEach((button) => {
            button.addEventListener("click", () => {
                button.closest(".scene-item")?.remove();
                this.updateSegmentNumbers(".scene-item", "场景");
            });
        });

        document.querySelectorAll<HTMLButtonElement>(".remove-ending").forEach((button) => {
            button.addEventListener("click", () => {
                button.closest(".ending-item")?.remove();
                this.updateSegmentNumbers(".ending-item", "结局");
            });
        });
    }

    private addScene(): void {
        const container = requiredElement("scenarioScenes");
        const count = container.querySelectorAll(".scene-item").length + 1;
        container.insertAdjacentHTML("beforeend", segmentTemplate("scene", count));
        this.bindRemoveEvents();
    }

    private addEnding(): void {
        const container = requiredElement("scenarioEndings");
        const count = container.querySelectorAll(".ending-item").length + 1;
        container.insertAdjacentHTML("beforeend", segmentTemplate("ending", count));
        this.bindRemoveEvents();
    }

    private updateSegmentNumbers(selector: string, label: string): void {
        document.querySelectorAll<HTMLElement>(selector).forEach((segment, index) => {
            const heading = segment.querySelector("h6");
            if (heading) heading.textContent = `${label} ${index + 1}`;
        });
    }
}

function segmentTemplate(type: "scene" | "ending", index: number, segment?: ScenarioSegment): string {
    const label = type === "scene" ? "场景" : "结局";
    const className = type === "scene" ? "scene-item" : "ending-item";
    const removeClass = type === "scene" ? "remove-scene" : "remove-ending";
    return `
        <div class="${className} mb-3 p-3 border rounded">
            <div class="d-flex justify-content-between align-items-center mb-2">
                <h6>${label} ${index}</h6>
                <button type="button" class="btn btn-sm btn-danger ${removeClass}">删除</button>
            </div>
            <div class="form-group">
                <label>${label}内容</label>
                <textarea class="form-control" rows="3">${scenarioEscapeHtml(segment?.content || "")}</textarea>
            </div>
            <div class="form-group mt-2">
                <label>${label}标记</label>
                <textarea class="form-control" rows="2" placeholder="AI总结内容将显示在这里">${scenarioEscapeHtml(segment?.marker || "")}</textarea>
            </div>
        </div>
    `;
}

function collectSegments(selector: ".scene-item" | ".ending-item"): ScenarioSegment[] {
    return Array.from(document.querySelectorAll<HTMLElement>(selector)).map((segment, index) => {
        const textareas = segment.querySelectorAll<HTMLTextAreaElement>("textarea");
        return {
            id: index + 1,
            content: textareas[0]?.value || "",
            marker: textareas[1]?.value || "",
        };
    });
}

function safeScenarioCover(cover?: string): string {
    return cover && cover.startsWith("/assets/scenario_covers/") ? cover : DEFAULT_SCENARIO_COVER;
}

function input(id: string): HTMLInputElement {
    return requiredElement(id) as HTMLInputElement;
}

function textarea(id: string): HTMLTextAreaElement {
    return requiredElement(id) as HTMLTextAreaElement;
}

function image(id: string): HTMLImageElement {
    return requiredElement(id) as HTMLImageElement;
}

function requiredElement(id: string): HTMLElement {
    const element = document.getElementById(id);
    if (!element) throw new Error(`缺少 DOM 元素: ${id}`);
    return element;
}

function scenarioEscapeHtml(value: unknown): string {
    return String(value ?? "")
        .replace(/&/g, "&amp;")
        .replace(/</g, "&lt;")
        .replace(/>/g, "&gt;")
        .replace(/"/g, "&quot;")
        .replace(/'/g, "&#039;");
}

window.ScenarioView = ScenarioView;
