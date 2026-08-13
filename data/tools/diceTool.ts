class DiceTool {
    private readonly diceTypes: Record<string, number> = {
        d4: 4,
        d6: 6,
        d8: 8,
        d10: 10,
        d12: 12,
        d20: 20,
        d100: 100,
    };

    rollSingleDice(diceType: string): number {
        const sides = this.diceTypes[diceType] || 6;
        return Math.floor(Math.random() * sides) + 1;
    }

    parseDiceCommand(command: string): DiceParseResult {
        const match = command.match(/^(\d+)d(\d+)$/i);
        if (!match) {
            return {
                success: false,
                error: '无效的骰子命令格式，请使用类似 "1d6" 的格式',
            };
        }

        const count = Number.parseInt(match[1] || "", 10);
        const sides = Number.parseInt(match[2] || "", 10);
        if (!Number.isFinite(count) || count < 1 || count > 100) {
            return {
                success: false,
                error: "骰子数量必须在 1-100 之间",
            };
        }

        if (!Number.isFinite(sides) || sides < 2 || sides > 100) {
            return {
                success: false,
                error: "骰子面数必须在 2-100 之间",
            };
        }

        const results: number[] = [];
        let total = 0;
        for (let index = 0; index < count; index += 1) {
            const result = Math.floor(Math.random() * sides) + 1;
            results.push(result);
            total += result;
        }

        return {
            success: true,
            count,
            sides,
            results,
            total,
        };
    }

    handleDiceCommand(command: string): string {
        const diceCommand = command.replace(/^\/dice\s+/i, "").trim();
        const result = this.parseDiceCommand(diceCommand);

        if (!result.success) {
            return result.error;
        }

        let message = `投掷 ${result.count}d${result.sides}：`;
        message += result.results.join(" + ");
        if (result.count > 1) {
            message += ` = ${result.total}`;
        }
        return message;
    }
}

window.DiceTool = DiceTool;
