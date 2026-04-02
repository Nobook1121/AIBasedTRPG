// 骰子工具模块
class DiceTool {
    constructor() {
        this.diceTypes = {
            d4: 4,
            d6: 6,
            d8: 8,
            d10: 10,
            d12: 12,
            d20: 20,
            d100: 100
        };
    }

    /**
     * 投掷单个骰子
     * @param {string} diceType - 骰子类型，如 'd6'
     * @returns {number} 骰子结果
     */
    rollSingleDice(diceType) {
        const sides = this.diceTypes[diceType] || 6;
        return Math.floor(Math.random() * sides) + 1;
    }

    /**
     * 解析骰子命令
     * @param {string} command - 骰子命令，如 '1d6'
     * @returns {Object} 解析结果和投掷结果
     */
    parseDiceCommand(command) {
        // 匹配格式：数字+d+数字，如 1d6, 2d10 等
        const regex = /^(\d+)d(\d+)$/i;
        const match = command.match(regex);

        if (!match) {
            return {
                success: false,
                error: '无效的骰子命令格式，请使用类似 "1d6" 的格式'
            };
        }

        const count = parseInt(match[1]);
        const sides = parseInt(match[2]);

        // 限制骰子数量和面数
        if (count < 1 || count > 100) {
            return {
                success: false,
                error: '骰子数量必须在 1-100 之间'
            };
        }

        if (sides < 2 || sides > 100) {
            return {
                success: false,
                error: '骰子面数必须在 2-100 之间'
            };
        }

        // 执行投掷
        const results = [];
        let total = 0;

        for (let i = 0; i < count; i++) {
            const result = Math.floor(Math.random() * sides) + 1;
            results.push(result);
            total += result;
        }

        return {
            success: true,
            count,
            sides,
            results,
            total
        };
    }

    /**
     * 处理骰子命令
     * @param {string} command - 完整的命令，如 '/dice 1d6'
     * @returns {string} 命令执行结果
     */
    handleDiceCommand(command) {
        // 移除命令前缀 '/dice '
        const diceCommand = command.replace(/^\/dice\s+/i, '').trim();
        
        const result = this.parseDiceCommand(diceCommand);

        if (!result.success) {
            return result.error;
        }

        // 构建结果消息
        let message = `投掷 ${result.count}d${result.sides}：`;
        message += result.results.join(' + ');
        if (result.count > 1) {
            message += ` = ${result.total}`;
        }

        return message;
    }
}

export default DiceTool;