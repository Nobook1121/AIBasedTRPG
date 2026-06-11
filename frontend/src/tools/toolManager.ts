class ToolManager {
    private readonly tools: {
        dice: DiceTool;
    };

    private readonly commands: Record<string, (command: string) => string>;

    constructor() {
        this.tools = {
            dice: new DiceTool(),
        };
        this.commands = {
            "/dice": this.handleDiceCommand.bind(this),
        };
    }

    handleDiceCommand(command: string): string {
        return this.tools.dice.handleDiceCommand(command);
    }

    handleCommand(command: string): string | null {
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
}

window.ToolManager = ToolManager;
