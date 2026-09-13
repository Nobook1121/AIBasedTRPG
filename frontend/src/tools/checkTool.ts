type CheckDifficulty = "regular" | "hard" | "extreme";
type CheckCommandParseResult = { success: true; playerName: string; name: string; difficulty: CheckDifficulty; adjustment: number; bonusDice: number; penaltyDice: number } | { success: false; error: string };
const CHECK_ATTRIBUTE_ALIASES: Record<string, COC7AttributeKey> = { STR: "STR", "力量": "STR", CON: "CON", "体质": "CON", SIZ: "SIZ", "体型": "SIZ", DEX: "DEX", "敏捷": "DEX", APP: "APP", "外貌": "APP", INT: "INT", "智力": "INT", POW: "POW", "意志": "POW", EDU: "EDU", "教育": "EDU", LUC: "LUC", "幸运": "LUC", AGE: "AGE", "年龄": "AGE" };
class CheckTool {
    constructor(private readonly dice: DiceTool) {}
    handleCheckCommand(command: string): string {
        const parsed = this.parseCheckCommand(command); if (!parsed.success) return parsed.error;
        const member = this.findRoomMember(parsed.playerName); if (!member) return `未在当前房间找到玩家 ${parsed.playerName}`;
        if (!member.character_card) return `玩家 ${parsed.playerName} 未绑定角色卡`;
        const baseTarget = this.findCheckValue(member.character_card, parsed.name); if (baseTarget === null) return `玩家 ${parsed.playerName} 的角色卡中未找到 ${parsed.name}`;
        const target = this.applyDifficulty(baseTarget, parsed.difficulty) + parsed.adjustment;
        let rollResult: { result: number; rolls: number[] }; try { rollResult = this.dice.rollPercentile(parsed.bonusDice, parsed.penaltyDice); } catch (error) { return error instanceof Error ? error.message : String(error); }
        const difficultyLabel = parsed.difficulty === "hard" ? "困难" : parsed.difficulty === "extreme" ? "极难" : "";
        let output = `${difficultyLabel}${parsed.name} d%: [${rollResult.result}] = ${rollResult.result} / ${target} ${rollResult.result <= target ? "成功" : "失败"}`;
        if (parsed.bonusDice || parsed.penaltyDice) output += ` ${parsed.bonusDice ? "奖励骰" : "惩罚骰"}（${rollResult.rolls.join(", ")}），取${rollResult.result}`;
        return output;
    }
    private parseCheckCommand(command: string): CheckCommandParseResult {
        const parts = command.trim().split(/\s+/).filter(Boolean); if ((parts[0] || "").toLowerCase() !== "/check") return { success: false, error: "无效的属性鉴定命令" };
        if (!parts[1] || !parts[2]) return { success: false, error: "格式：/check 玩家名 技能/属性名 困难/极难 +/-调整值 [奖励骰|惩罚骰]" };
        let difficulty: CheckDifficulty = "regular", adjustmentText = "", bonusDice = 0, penaltyDice = 0;
        for (const part of parts.slice(3)) {
            if (part === "困难") difficulty = "hard"; else if (part === "极难") difficulty = "extreme"; else if (/^[+-]\d+$/.test(part)) adjustmentText = part;
            else if (/^(奖励骰|bonus)(?::\d+)?$/i.test(part)) bonusDice = Number.parseInt(part.split(":")[1] || "1", 10);
            else if (/^(惩罚骰|penalty)(?::\d+)?$/i.test(part)) penaltyDice = Number.parseInt(part.split(":")[1] || "1", 10);
            else return { success: false, error: `无法识别的 /check 参数：${part}` };
        }
        if (bonusDice && penaltyDice) return { success: false, error: "奖励骰和惩罚骰不能同时使用" };
        return { success: true, playerName: parts[1], name: parts[2], difficulty, adjustment: adjustmentText ? Number.parseInt(adjustmentText, 10) : 0, bonusDice, penaltyDice };
    }
    private findRoomMember(playerName: string): RoomMember | null { const expected = playerName.toLowerCase(); return (window.currentRoom?.members || []).find((member) => member.is_active !== false && member.status !== "removed" && String(member.username || "").toLowerCase() === expected) || null; }
    private findCheckValue(card: Partial<COC7CharacterCard>, name: string): number | null {
        const key = CHECK_ATTRIBUTE_ALIASES[name] || CHECK_ATTRIBUTE_ALIASES[name.toUpperCase()]; const value = key ? card.attributes?.[key] : undefined;
        if (typeof value === "number" && Number.isFinite(value)) return value;
        const expected = name.toLowerCase(); const skill = (card.skills || []).find((item) => [item.name, item.skillKey, item.id].some((candidate) => String(candidate || "").toLowerCase() === expected));
        return skill && typeof skill.value === "number" && Number.isFinite(skill.value) ? skill.value : null;
    }
    private applyDifficulty(target: number, difficulty: CheckDifficulty): number { return difficulty === "hard" ? Math.floor(target / 2) : difficulty === "extreme" ? Math.floor(target / 5) : target; }
}
window.CheckTool = CheckTool;
