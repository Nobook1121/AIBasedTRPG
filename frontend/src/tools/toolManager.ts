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

const ATTRIBUTE_ALIASES: Record<string, COC7AttributeKey> = {
    STR: "STR",
    力量: "STR",
    CON: "CON",
    体质: "CON",
    SIZ: "SIZ",
    体型: "SIZ",
    DEX: "DEX",
    敏捷: "DEX",
    APP: "APP",
    外貌: "APP",
    INT: "INT",
    智力: "INT",
    POW: "POW",
    意志: "POW",
    EDU: "EDU",
    教育: "EDU",
    LUC: "LUC",
    幸运: "LUC",
    AGE: "AGE",
    年龄: "AGE",
};

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
            "/check": this.handleCheckCommand.bind(this),
        };
    }

    handleDiceCommand(command: string): string {
        return this.tools.dice.handleDiceCommand(command);
    }

    handleCheckCommand(command: string): string {
        const parsed = this.parseCheckCommand(command);
        if (!parsed.success) {
            console.warn("Check command rejected:", parsed.error);
            return parsed.error;
        }

        const member = this.findRoomMember(parsed.playerName);
        if (!member) {
            const error = `未在当前房间找到玩家 ${parsed.playerName}`;
            console.warn("Check command member not found:", { playerName: parsed.playerName });
            return error;
        }
        const card = member.character_card;
        if (!card) {
            const error = `玩家 ${parsed.playerName} 未绑定角色卡`;
            console.warn("Check command character card missing:", { playerName: parsed.playerName });
            return error;
        }

        const baseTarget = this.findCheckValue(card, parsed.name);
        if (baseTarget === null) {
            const error = `玩家 ${parsed.playerName} 的角色卡中未找到 ${parsed.name}`;
            console.warn("Check command value not found:", { playerName: parsed.playerName, name: parsed.name });
            return error;
        }

        const difficultyTarget = this.applyDifficulty(baseTarget, parsed.difficulty);
        const target = difficultyTarget + parsed.adjustment;
        const rollResult = this.tools.dice.parseDiceCommand("1d100");
        if (!rollResult.success) return rollResult.error;
        const roll = rollResult.total;
        const success = roll <= target;
        const difficultyLabel = parsed.difficulty === "hard" ? "困难" : parsed.difficulty === "extreme" ? "极难" : "";
        const result = `${difficultyLabel}${parsed.name} d%: [${roll}] = ${roll} / ${target} ${success ? "成功" : "失败"}`;
        console.info("Check command rolled:", {
            playerName: parsed.playerName,
            name: parsed.name,
            difficulty: parsed.difficulty,
            baseTarget,
            adjustment: parsed.adjustment,
            target,
            roll,
            success,
        });
        return result;
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

    private findRoomMember(playerName: string): RoomMember | null {
        const expected = playerName.toLowerCase();
        const members = window.currentRoom?.members || [];
        return members.find((member) => {
            const active = member.is_active !== false && member.status !== "removed";
            return active && String(member.username || "").toLowerCase() === expected;
        }) || null;
    }

    private findCheckValue(card: Partial<COC7CharacterCard>, name: string): number | null {
        const attributeKey = ATTRIBUTE_ALIASES[name] || ATTRIBUTE_ALIASES[name.toUpperCase()];
        if (attributeKey) {
            const value = card.attributes?.[attributeKey];
            if (typeof value === "number" && Number.isFinite(value)) return value;
        }

        const expected = name.toLowerCase();
        const skill = (card.skills || []).find((item) => {
            const candidates = [item.name, item.skillKey, item.id];
            return candidates.some((candidate) => String(candidate || "").toLowerCase() === expected);
        });
        if (!skill) return null;
        return typeof skill.value === "number" && Number.isFinite(skill.value) ? skill.value : null;
    }

    private applyDifficulty(target: number, difficulty: CheckDifficulty): number {
        if (difficulty === "hard") return Math.floor(target / 2);
        if (difficulty === "extreme") return Math.floor(target / 5);
        return target;
    }
}

window.ToolManager = ToolManager;
