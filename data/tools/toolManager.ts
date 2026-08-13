type CheckDifficulty = "regular" | "hard" | "extreme";

type CheckCommandParseResult = {
    success: true;
    playerName: string;
    name: string;
    difficulty: CheckDifficulty;
    adjustment: number;
} | {
    success: false;
    error: string;
};

class ToolManager {
    private readonly tools: {
        dice: DiceTool;
    };

    private readonly commands: Record<string, (command: string) => Promise<string>>;

    constructor() {
        this.tools = {
            dice: new DiceTool(),
        };
        this.commands = {
            "/dice": async (command: string) => this.handleDiceCommand(command),
            "/check": this.handleCheckCommand.bind(this),
        };
    }

    handleDiceCommand(command: string): string {
        return this.tools.dice.handleDiceCommand(command);
    }

    async handleCheckCommand(command: string): Promise<string> {
        const parsed = this.parseCheckCommand(command);
        if (!parsed.success) {
            console.warn("Check command rejected:", parsed.error);
            return parsed.error;
        }

        const roomId = window.currentRoom?.id;
        if (!roomId) return "请先进入房间再使用 /check";

        try {
            const response = await fetch(`/api/rooms/${encodeURIComponent(roomId)}/tools/check`, {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({
                    player_name: parsed.playerName,
                    name: parsed.name,
                    difficulty: parsed.difficulty,
                    adjustment: parsed.adjustment ? `${parsed.adjustment > 0 ? "+" : ""}${parsed.adjustment}` : "",
                }),
            });
            const payload = await response.json() as ApiResponse<{ summary?: string }>;
            if (!response.ok || !payload.success) {
                return payload.error || payload.message || "检定失败";
            }
            return payload.data?.summary || "检定完成，但服务器未返回摘要";
        } catch (error) {
            console.warn("Check command request failed:", error);
            return "检定工具请求失败，请检查网络或后端服务";
        }
    }

    async handleCommand(command: string): Promise<string | null> {
        if (!command.startsWith("/")) {
            return null;
        }

        const commandName = (command.split(" ")[0] || "").toLowerCase();
        const handler = this.commands[commandName];
        return handler ? handler(command) : "未知命令，请查看可用命令列表";
    }

    getTools(): { dice: DiceTool } {
        return this.tools;
    }

    getCommands(): string[] {
        return Object.keys(this.commands);
    }

    recordCharacterChange(payload: Record<string, unknown>): Promise<unknown> {
        if (typeof window.recordCharacterChange === "function") {
            return window.recordCharacterChange(payload);
        }
        return Promise.resolve(null);
    }

    private parseCheckCommand(command: string): CheckCommandParseResult {
        const parts = command.trim().split(/\s+/).filter(Boolean);
        if ((parts[0] || "").toLowerCase() !== "/check") {
            return { success: false, error: "无效的属性鉴定命令" };
        }
        if (!parts[1]) {
            return { success: false, error: "缺少玩家名，格式：/check {*玩家名} {*技能/属性名} {困难/极难} {调整值}" };
        }
        if (!parts[2]) {
            return { success: false, error: "缺少技能/属性名，格式：/check {*玩家名} {*技能/属性名} {困难/极难} {调整值}" };
        }

        let difficulty: CheckDifficulty = "regular";
        let adjustmentText = "";
        for (const part of parts.slice(3)) {
            if (part === "困难") {
                difficulty = "hard";
                continue;
            }
            if (part === "极难") {
                difficulty = "extreme";
                continue;
            }
            if (/^[+-]\d+$/.test(part)) {
                adjustmentText = part;
                continue;
            }
            return { success: false, error: `无法识别的 /check 参数：${part}` };
        }

        return {
            success: true,
            playerName: parts[1],
            name: parts[2],
            difficulty,
            adjustment: adjustmentText ? Number.parseInt(adjustmentText, 10) : 0,
        };
    }

}

window.ToolManager = ToolManager;
