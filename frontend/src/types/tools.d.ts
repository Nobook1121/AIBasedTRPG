interface DiceParseSuccess {
    success: true;
    count: number;
    sides: number;
    results: number[];
    total: number;
}

interface DiceParseFailure {
    success: false;
    error: string;
}

type DiceParseResult = DiceParseSuccess | DiceParseFailure;

interface DiceToolConstructor {
    new(): DiceTool;
}

interface DiceTool {
    handleDiceCommand(command: string): string;
    parseDiceCommand(command: string): DiceParseResult;
}

interface ToolManagerConstructor {
    new(): ToolManager;
}

interface ToolManager {
    handleCommand(command: string): string | null;
    handleCheckCommand(command: string): string;
    recordCharacterChange(payload: Record<string, unknown>): Promise<unknown>;
}
