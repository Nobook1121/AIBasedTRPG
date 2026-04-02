// 工具管理器模块
import DiceTool from './diceTool.js';

class ToolManager {
    constructor() {
        this.tools = {
            dice: new DiceTool()
        };
        this.commands = {
            '/dice': this.handleDiceCommand.bind(this)
        };
    }

    /**
     * 处理骰子命令
     * @param {string} command - 完整的命令，如 '/dice 1d6'
     * @returns {string} 命令执行结果
     */
    handleDiceCommand(command) {
        return this.tools.dice.handleDiceCommand(command);
    }

    /**
     * 处理命令
     * @param {string} command - 完整的命令
     * @returns {string|null} 命令执行结果，如果不是命令则返回 null
     */
    handleCommand(command) {
        // 检查是否是命令格式
        if (!command.startsWith('/')) {
            return null;
        }

        // 提取命令名称
        const commandName = command.split(' ')[0].toLowerCase();

        // 检查是否是已注册的命令
        if (this.commands[commandName]) {
            return this.commands[commandName](command);
        }

        return '未知命令，请查看可用命令列表';
    }

    /**
     * 获取所有工具
     * @returns {Object} 工具对象
     */
    getTools() {
        return this.tools;
    }

    /**
     * 获取所有命令
     * @returns {Array} 命令列表
     */
    getCommands() {
        return Object.keys(this.commands);
    }
}

export default ToolManager;