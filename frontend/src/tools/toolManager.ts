class ToolManager {
    private readonly tools: {
        dice: DiceTool;
        check: CheckTool;
    };

    private readonly commands: Record<string, (command: string) => string>;

    constructor() {
        const dice = new DiceTool();
        this.tools = {
            dice,
            check: new CheckTool(dice),
        };
        this.commands = {
            "/dice": this.handleDiceCommand.bind(this),
            "/check": this.handleCheckCommand.bind(this),
            "/sc": this.handleSanityCommand.bind(this),
        };
    }

    handleDiceCommand(command: string): string {
        return this.tools.dice.handleDiceCommand(command);
    }

    handleCheckCommand(command: string): string {
        return this.tools.check.handleCheckCommand(command);
    }

    handleSanityCommand(command: string): string {
        const parts = command.trim().split(/\s+/).filter(Boolean);
        if (!parts[1] || !parts[2] || !parts[2].includes("/")) return "格式：/sc 玩家名 成功变化/失败变化";
        const username = parts[1] || "";
        const member = (window.currentRoom?.members || []).find((item) => String(item.username || "").toLowerCase() === username.toLowerCase());
        const card = member?.character_card;
        if (!card) return `未找到玩家 ${parts[1]} 的角色卡`;
        const san = Number(member?.character_state?.current_san ?? card.currentSan ?? card.maxSan ?? 0);
        const roll = Math.floor(Math.random() * 100) + 1;
        const success = roll <= san;
        const expression = (success ? parts[2].split("/")[0] : parts[2].split("/")[1]) || "0";
        return `${parts[1]} 理智检定：1d100=[${roll}] / 当前 SAN ${san}，${success ? "成功" : "失败"}；结算 ${expression}（请由 KP Function 同步角色 SAN）。`;
    }

    handleCommand(command: string): string | null {
        if (!command.startsWith("/")) return null;
        const commandName = (command.split(" ")[0] || "").toLowerCase();
        const handler = this.commands[commandName];
        return handler ? handler(command) : "\u672a\u77e5\u547d\u4ee4\uff0c\u8bf7\u67e5\u770b\u53ef\u7528\u547d\u4ee4\u5217\u8868";
    }

    getTools(): { dice: DiceTool; check: CheckTool } {
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
}

window.ToolManager = ToolManager;
