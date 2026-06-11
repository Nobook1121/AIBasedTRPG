"use strict";
class ToolManager {
    tools;
    commands;
    constructor() {
        this.tools = {
            dice: new DiceTool(),
        };
        this.commands = {
            "/dice": this.handleDiceCommand.bind(this),
        };
    }
    handleDiceCommand(command) {
        return this.tools.dice.handleDiceCommand(command);
    }
    handleCommand(command) {
        if (!command.startsWith("/")) {
            return null;
        }
        const commandName = (command.split(" ")[0] || "").toLowerCase();
        const handler = this.commands[commandName];
        return handler ? handler(command) : "未知命令，请查看可用命令列表";
    }
    getTools() {
        return this.tools;
    }
    getCommands() {
        return Object.keys(this.commands);
    }
    recordCharacterChange(payload) {
        if (typeof window.recordCharacterChange === "function") {
            return window.recordCharacterChange(payload);
        }
        return Promise.resolve(null);
    }
}
window.ToolManager = ToolManager;
