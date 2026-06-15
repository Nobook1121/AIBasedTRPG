type COC7CoreAttributeKey = "STR" | "DEX" | "SIZ" | "APP" | "CON" | "INT" | "POW" | "EDU" | "LUC";
type COC7AttributeKey = COC7CoreAttributeKey | "AGE";
type SkillRank = "新手" | "学习" | "熟修" | "主修";
type SkillCategory = "探索" | "社交" | "知识" | "战斗" | "行动" | "神话";
type InvestigatorGender = "male" | "female" | "unknown";
type NameRegion = "china" | "japan" | "korea" | "western" | "russia" | "india" | "france" | "germany" | "spain" | "italy";

interface COC7Attributes {
    STR: number;
    CON: number;
    SIZ: number;
    DEX: number;
    APP: number;
    INT: number;
    POW: number;
    EDU: number;
    LUC: number;
    AGE: number;
}

interface LegacyAttributesInput extends Partial<COC7Attributes> {
    LUK?: number;
}

interface COC7Skill {
    id: string;
    name: string;
    value: number;
    base: number;
    category: SkillCategory | string;
    checked: boolean;
    occupation?: boolean;
    specialty?: string;
    rank?: SkillRank;
}

interface OccupationPointFormulaTerm {
    attribute: COC7AttributeKey;
    multiplier: number;
}

interface SkillSuccessLimits {
    occupation: number;
    other: number;
}

type OccupationPointFormula = Array<COC7AttributeKey | OccupationPointFormulaTerm>;

type OccupationSkillEntry = {
    skillKey?: string;
    specialtyKey?: string;
    chooseOne?: OccupationSkillEntry[];
    freeChoice?: string;
};

interface COC7EquipmentItem {
    name: string;
    quantity: number;
    weight: number;
    volume?: number;
    notes?: string;
}

interface COC7Weapon {
    name: string;
    skill: string;
    damage: string;
    range: string;
    attacks: number;
    ammo: number;
    malfunction: number;
}

interface COC7Assets {
    cash: number;
    spendingLevel: number;
    assetsText: string;
}

interface COC7Relationship {
    name: string;
    description: string;
}

interface COC7Background {
    appearance: string;
    ideology: string;
    significantPeople: string;
    meaningfulLocations: string;
    treasuredPossessions: string;
    traits: string;
    injuriesScars: string;
    phobiasManias: string;
    arcaneTomes: string;
    encounters: string;
    story: string;
    education: string;
    raceType: string;
}

interface COC7Occupation {
    id: string;
    name: string;
    nameKey?: string;
    creditRating: [number, number];
    occupationSkills: string[];
    pointsFormula: OccupationPointFormula;
    occupationSkillEntries?: OccupationSkillEntry[];
    occupationSkillLabels?: string[];
    skillBonuses: Record<string, number>;
    specialties: string[];
    passiveEffects: string[];
}

interface OccupationCatalogPayload {
    id: string;
    nameKey?: string;
    creditRating?: { min?: number; max?: number };
    occupationSkillPoints?: {
        formula?: string;
        terms?: OccupationPointFormulaTerm[];
    };
    occupationSkills?: OccupationSkillEntry[];
}

interface COC7HalfAndFifth {
    half: number;
    fifth: number;
}

interface AttributeDisplayValues {
    half: number;
    ratio: number;
}

interface AttributeRollFormula {
    dice: number;
    sides: number;
    bonus: number;
    multiplier: number;
}

type AttributeRollFormulaMap = Record<COC7CoreAttributeKey, string>;

interface CharacterRuleSettings {
    attributeRatioPercent: number;
    maxCardsPerUser: number;
    attributeRolls: AttributeRollFormulaMap;
}

interface CharacterRuleSettingsInput {
    attributeRatioPercent?: unknown;
    maxCardsPerUser?: unknown;
    attributeRolls?: Partial<Record<COC7CoreAttributeKey, string>>;
}

interface CharacterAssignableUser {
    id: string | number;
    username: string;
    role?: string;
    status?: string;
}

interface CharacterStatusFlags {
    majorWound: boolean;
    unconscious: boolean;
    dead: boolean;
    temporaryInsanity: boolean;
    permanentInsanity: boolean;
    indefiniteInsanity: boolean;
}

interface COC7SkillAllocationSummary {
    selectedOccupationSkills: number;
    requiredOccupationSkills: number;
    creditRatingValid: boolean;
    occupationPoints: number;
    personalInterestPoints: number;
}

interface COC7CharacterCard {
    id: string;
    name: string;
    playerId: string;
    era: string;
    gender: string;
    age: number;
    avatar: string;
    occupationId: string;
    occupationName: string;
    creditRating: number;
    residence: string;
    birthplace: string;
    attributes: COC7Attributes;
    maxHp: number;
    currentHp: number;
    maxSan: number;
    initialSan: number;
    currentSan: number;
    magicPoints: number;
    currentMp: number;
    maxMp: number;
    status: CharacterStatusFlags;
    occupationSkillPoints: number;
    personalInterestPoints: number;
    skillSuccessLimits: SkillSuccessLimits;
    mov: number;
    build: number;
    damageBonus: string;
    skills: COC7Skill[];
    weapons: COC7Weapon[];
    equipment: COC7EquipmentItem[];
    assets: COC7Assets;
    background: COC7Background;
    relationships: COC7Relationship[];
    createdAt: string;
    updatedAt: string;
}

type COC7CharacterCardInput = Partial<Omit<COC7CharacterCard, "attributes" | "gender">> & {
    attributes?: LegacyAttributesInput;
    gender?: string;
};

interface AttributeCheckResult {
    roll: number;
    target: number;
    success: boolean;
    level: string;
}

interface CharacterApi {
    ATTRIBUTE_KEYS: COC7CoreAttributeKey[];
    SKILL_RANKS: SkillRank[];
    BASE_SKILLS: COC7Skill[];
    PRESET_OCCUPATIONS: COC7Occupation[];
    calculateHalfAndFifth: (value: number) => COC7HalfAndFifth;
    calculateAttributeDisplayValues: (value: number, ratioPercent?: number) => AttributeDisplayValues;
    calculateMaxHp: (attributes: COC7Attributes) => number;
    calculateMaxSan: (attributes: COC7Attributes) => number;
    calculateMaxMp: (attributes: COC7Attributes) => number;
    calculateMov: (attributes: COC7Attributes) => number;
    calculateOccupationSkillPoints: (attributes: COC7Attributes, occupationId: string) => number;
    calculatePersonalInterestPoints: (attributes: COC7Attributes) => number;
    calculateBuildAndDamageBonus: (attributes: Pick<COC7Attributes, "STR" | "SIZ">) => { build: number; damageBonus: string };
    calculateEquipmentLoad: (equipment: COC7EquipmentItem[]) => { totalWeight: number; totalVolume: number };
    groupSkillsByCategory: (skills: COC7Skill[]) => Record<string, number>;
    countSkillsByRank: (skills: COC7Skill[]) => Record<SkillRank, number>;
    countSelectedOccupationSkills: (skills: COC7Skill[]) => number;
    validateOccupationSkillSelection: (card: COC7CharacterCard) => COC7SkillAllocationSummary;
    autoAllocateOccupationSkills: (card: COC7CharacterCard) => COC7CharacterCard;
    getOccupationPassiveEffects: (card: COC7CharacterCard) => string[];
    rollAttributeCheck: (attributes: COC7Attributes, attributeKey: COC7AttributeKey, roller?: () => number) => AttributeCheckResult;
    generateInvestigatorName: (gender?: InvestigatorGender, random?: () => number) => string;
    generateRegionalName: (region?: NameRegion, gender?: InvestigatorGender, random?: () => number) => string;
    parseAttributeRollFormula: (formulaText: string) => AttributeRollFormula | null;
    rollAttributeFormula: (formula: AttributeRollFormula, random?: () => number) => number;
    randomizeAttributes: (random?: () => number, settings?: CharacterRuleSettings) => COC7Attributes;
    createCharacterCard: (input?: COC7CharacterCardInput) => COC7CharacterCard;
    listCharacterCards: () => COC7CharacterCard[];
    getCharacterCardSnapshot: (cardId: string) => Partial<COC7CharacterCard> | null;
    initCharacterSheet: () => void;
}

interface Window {
    COC7CharacterSheet?: CharacterApi;
}

(function initializeCharacterSheet(global: Window & typeof globalThis): void {
    "use strict";

    const STORAGE_KEY = "ai-trpg:coc7-character-cards";
    const ACTIVE_STORAGE_KEY = "ai-trpg:coc7-active-character";
    const RULE_SETTINGS_STORAGE_KEY = "ai-trpg:coc7-character-rule-settings";
    const ATTRIBUTE_KEYS: COC7CoreAttributeKey[] = ["STR", "DEX", "SIZ", "APP", "CON", "INT", "POW", "EDU", "LUC"];
    const PLAYER_UNBOUND_LABEL = "未绑定玩家";
    const ATTRIBUTE_LABELS: Record<COC7CoreAttributeKey, string> = {
        STR: "力量",
        DEX: "敏捷",
        SIZ: "体型",
        APP: "外貌",
        CON: "体质",
        INT: "智力",
        POW: "意志",
        EDU: "教育",
        LUC: "幸运"
    };
    const DEFAULT_ATTRIBUTE_ROLLS: AttributeRollFormulaMap = {
        STR: "3d6x5",
        DEX: "3d6x5",
        SIZ: "(2d6+6)x5",
        APP: "3d6x5",
        CON: "3d6x5",
        INT: "(2d6+6)x5",
        POW: "3d6x5",
        EDU: "(2d6+6)x5",
        LUC: "3d6x5"
    };
    const DEFAULT_RULE_SETTINGS: CharacterRuleSettings = {
        attributeRatioPercent: 20,
        maxCardsPerUser: 5,
        attributeRolls: DEFAULT_ATTRIBUTE_ROLLS
    };
    const STATUS_FIELD_IDS: Record<keyof CharacterStatusFlags, string> = {
        majorWound: "characterStatusMajorWound",
        unconscious: "characterStatusUnconscious",
        dead: "characterStatusDead",
        temporaryInsanity: "characterStatusTemporaryInsanity",
        permanentInsanity: "characterStatusPermanentInsanity",
        indefiniteInsanity: "characterStatusIndefiniteInsanity"
    };
    const SKILL_RANKS: SkillRank[] = ["新手", "学习", "熟修", "主修"];
    const REGIONAL_NAMES: Record<NameRegion, { family: string[]; male: string[]; female: string[]; neutral: string[]; westernOrder?: boolean }> = {
        china: { family: ["林", "陈", "顾", "沈", "周", "陆", "许", "梁"], male: ["雨衡", "明远", "怀瑾", "景行", "子昂", "修文"], female: ["若宁", "清荷", "知遥", "南枝", "书瑶", "映雪"], neutral: ["安和", "知远", "星河"] },
        japan: { family: ["藤原", "佐藤", "高桥", "田中", "渡边", "伊藤"], male: ["悠真", "莲", "翔太", "拓海"], female: ["香里", "美咲", "结衣", "葵"], neutral: ["遥", "光", "律"] },
        korea: { family: ["金", "李", "朴", "崔", "郑", "韩"], male: ["俊浩", "民载", "道允", "志勋"], female: ["素贤", "智雅", "恩彩", "瑞妍"], neutral: ["贤宇", "智安", "夏仁"] },
        western: { family: ["Carter", "Miller", "Bennett", "Morgan", "Reed", "Howard"], male: ["Arthur", "Edward", "Henry", "Victor"], female: ["Eleanor", "Clara", "Grace", "Helen"], neutral: ["Alex", "Robin", "Taylor"], westernOrder: true },
        russia: { family: ["Ivanov", "Petrov", "Sokolov", "Volkov", "Morozov"], male: ["Dmitri", "Nikolai", "Alexei", "Viktor"], female: ["Anastasia", "Irina", "Svetlana", "Katerina"], neutral: ["Sasha", "Valya", "Zhenya"], westernOrder: true },
        india: { family: ["Sharma", "Patel", "Iyer", "Nair", "Kapoor"], male: ["Arjun", "Rahul", "Vikram", "Dev"], female: ["Anika", "Priya", "Meera", "Kavya"], neutral: ["Kiran", "Adi", "Arya"], westernOrder: true },
        france: { family: ["Dubois", "Moreau", "Lefevre", "Laurent", "Bernard"], male: ["Louis", "Henri", "Luc", "Etienne"], female: ["Claire", "Camille", "Elise", "Juliette"], neutral: ["Claude", "Dominique", "Noel"], westernOrder: true },
        germany: { family: ["Muller", "Schmidt", "Weber", "Fischer", "Wagner"], male: ["Karl", "Otto", "Lukas", "Felix"], female: ["Anna", "Greta", "Lena", "Marta"], neutral: ["Alex", "Toni", "Mika"], westernOrder: true },
        spain: { family: ["Garcia", "Lopez", "Martinez", "Sanchez", "Romero"], male: ["Diego", "Mateo", "Javier", "Rafael"], female: ["Lucia", "Sofia", "Isabel", "Carmen"], neutral: ["Cruz", "Angel", "Sol"], westernOrder: true },
        italy: { family: ["Rossi", "Bianchi", "Romano", "Ricci", "Marino"], male: ["Marco", "Luca", "Giovanni", "Matteo"], female: ["Giulia", "Sofia", "Elena", "Bianca"], neutral: ["Andrea", "Noa", "Vale"], westernOrder: true }
    };

    let PRESET_OCCUPATIONS: COC7Occupation[] = [
        {
            id: "detective",
            name: "私家侦探",
            creditRating: [9, 30],
            occupationSkills: ["artCraft", "disguise", "law", "libraryUse", "psychology", "spotHidden", "stealth", "fastTalk"],
            pointsFormula: ["EDU", "EDU", "DEX", "DEX"],
            skillBonuses: { spotHidden: 20, listen: 15, psychology: 15, libraryUse: 10 },
            specialties: ["调查", "跟踪", "线索整合"],
            passiveEffects: ["调查场景中第一次侦查或聆听检定可获得 +10 情境加值。"]
        },
        {
            id: "doctor",
            name: "医生",
            creditRating: [30, 80],
            occupationSkills: ["firstAid", "medicine", "psychology", "science", "scienceBiology", "sciencePharmacy", "languageOther", "persuade"],
            pointsFormula: ["EDU", "EDU", "EDU", "EDU"],
            skillBonuses: { medicine: 25, firstAid: 20, psychology: 10, science: 10 },
            specialties: ["治疗", "诊断", "解剖"],
            passiveEffects: ["处理伤势时，急救成功后可额外恢复 1 点生命值。"]
        },
        {
            id: "professor",
            name: "大学教授",
            creditRating: [20, 70],
            occupationSkills: ["libraryUse", "languageOwn", "history", "archaeology", "science", "psychology", "languageOther", "persuade"],
            pointsFormula: ["EDU", "EDU", "EDU", "EDU"],
            skillBonuses: { libraryUse: 25, languageOwn: 20, history: 15, archaeology: 15 },
            specialties: ["学术研究", "文献检索", "古物辨识"],
            passiveEffects: ["学术分组技能检定成功后，可额外获得一条背景线索。"]
        },
        {
            id: "journalist",
            name: "记者",
            creditRating: [9, 30],
            occupationSkills: ["artCraft", "history", "libraryUse", "languageOwn", "psychology", "fastTalk", "photography", "persuade"],
            pointsFormula: ["EDU", "EDU", "APP", "APP"],
            skillBonuses: { libraryUse: 20, fastTalk: 15, psychology: 10, photography: 10 },
            specialties: ["采访", "摄影", "舆论调查"],
            passiveEffects: ["公开场合收集传闻时，话术或说服检定可获得 +10 情境加值。"]
        },
        {
            id: "police",
            name: "警探",
            creditRating: [20, 50],
            occupationSkills: ["fightingBrawl", "firearmsHandgun", "firstAid", "law", "listen", "psychology", "spotHidden", "driveAuto"],
            pointsFormula: ["EDU", "EDU", "STR", "DEX"],
            skillBonuses: { law: 15, spotHidden: 15, firearmsHandgun: 10, psychology: 10 },
            specialties: ["执法", "审讯", "现场控制"],
            passiveEffects: ["面对普通市民或地方机构时，可获得一次身份便利。"]
        },
        {
            id: "occultist",
            name: "神秘学者",
            creditRating: [9, 30],
            occupationSkills: ["anthropology", "history", "libraryUse", "occult", "languageOther", "psychology", "spotHidden", "cthulhuMythos"],
            pointsFormula: ["EDU", "EDU", "INT", "INT"],
            skillBonuses: { occult: 25, libraryUse: 15, history: 10, languageOther: 10 },
            specialties: ["仪式", "民俗", "禁书"],
            passiveEffects: ["辨识神秘符号、仪式或民俗时可获得 +10 情境加值。"]
        },
        {
            id: "antiquarian",
            name: "古董商",
            creditRating: [30, 70],
            occupationSkills: ["appraise", "artCraft", "history", "libraryUse", "languageOther", "occult", "persuade", "spotHidden"],
            pointsFormula: ["EDU", "EDU", "APP", "APP"],
            skillBonuses: { appraise: 25, history: 15, persuade: 10, spotHidden: 10 },
            specialties: ["估价", "古物", "交易"],
            passiveEffects: ["鉴定古物、赝品或收藏来源时可获得 +10 情境加值。"]
        },
        {
            id: "soldier",
            name: "士兵",
            creditRating: [9, 30],
            occupationSkills: ["climb", "dodge", "fightingBrawl", "firearmsRifle", "firstAid", "stealth", "survival", "throw"],
            pointsFormula: ["EDU", "EDU", "STR", "DEX"],
            skillBonuses: { firearmsRifle: 20, fightingBrawl: 15, firstAid: 10, survival: 10 },
            specialties: ["战斗", "野外", "纪律"],
            passiveEffects: ["战斗轮开始前第一次运动类行动可获得 +10 情境加值。"]
        },
        {
            id: "criminal",
            name: "罪犯",
            creditRating: [5, 65],
            occupationSkills: ["appraise", "disguise", "fightingBrawl", "firearmsHandgun", "locksmith", "sleightOfHand", "stealth", "fastTalk"],
            pointsFormula: ["EDU", "EDU", "DEX", "DEX"],
            skillBonuses: { stealth: 20, locksmith: 15, sleightOfHand: 15, fastTalk: 10 },
            specialties: ["潜入", "黑市", "伪装"],
            passiveEffects: ["处理非法交易、潜入或销赃线索时可获得 +10 情境加值。"]
        },
        {
            id: "engineer",
            name: "工程师",
            creditRating: [30, 60],
            occupationSkills: ["electricalRepair", "mechanicalRepair", "operateHeavyMachinery", "science", "scienceEngineering", "libraryUse", "mathematics", "spotHidden"],
            pointsFormula: ["EDU", "EDU", "EDU", "EDU"],
            skillBonuses: { mechanicalRepair: 25, electricalRepair: 20, scienceEngineering: 15, operateHeavyMachinery: 10 },
            specialties: ["机械", "电气", "结构"],
            passiveEffects: ["修复机械、电气设备或分析工程结构时可获得 +10 情境加值。"]
        }
    ];

    const OCCUPATION_LABELS: Record<string, string> = {
        "occupations.writer": "作家"
    };

    const SKILL_SPECIALTY_LABELS: Record<string, string> = {
        "artCraft.writing": "写作"
    };

    const WRITER_OCCUPATION: COC7Occupation = {
        id: "writer",
        name: "作家",
        nameKey: "occupations.writer",
        creditRating: [9, 30],
        occupationSkills: ["artCraft", "history", "libraryUse", "naturalWorld", "occult", "languageOther", "languageOwn", "psychology"],
        pointsFormula: [{ attribute: "EDU", multiplier: 4 }],
        occupationSkillEntries: [
            { skillKey: "artCraft", specialtyKey: "writing" },
            { skillKey: "history" },
            { skillKey: "libraryUse" },
            { chooseOne: [{ skillKey: "naturalWorld" }, { skillKey: "occult" }] },
            { skillKey: "languageOther" },
            { skillKey: "languageOwn" },
            { skillKey: "psychology" },
            { freeChoice: "personalOrEraSpecialty" }
        ],
        occupationSkillLabels: ["技艺(写作)", "历史", "图书馆使用", "博物学或神秘学", "外语", "母语", "心理学", "任意一项其他个人或时代特长"],
        skillBonuses: {},
        specialties: [],
        passiveEffects: []
    };

    PRESET_OCCUPATIONS = [WRITER_OCCUPATION];

    const BASE_SKILLS: COC7Skill[] = [
        { id: "accounting", name: "会计", base: 5, value: 5, category: "知识", checked: false },
        { id: "anthropology", name: "人类学", base: 1, value: 1, category: "知识", checked: false },
        { id: "appraise", name: "估价", base: 5, value: 5, category: "知识", checked: false },
        { id: "archaeology", name: "考古学", base: 1, value: 1, category: "知识", checked: false },
        { id: "artCraft", name: "艺术/手艺", base: 5, value: 5, category: "知识", checked: false },
        { id: "charm", name: "魅惑", base: 15, value: 15, category: "社交", checked: false },
        { id: "climb", name: "攀爬", base: 20, value: 20, category: "行动", checked: false },
        { id: "cthulhuMythos", name: "克苏鲁神话", base: 0, value: 0, category: "神话", checked: false },
        { id: "disguise", name: "乔装", base: 5, value: 5, category: "社交", checked: false },
        { id: "dodge", name: "闪避", base: 25, value: 25, category: "战斗", checked: false },
        { id: "driveAuto", name: "汽车驾驶", base: 20, value: 20, category: "行动", checked: false },
        { id: "electricalRepair", name: "电气维修", base: 10, value: 10, category: "行动", checked: false },
        { id: "fastTalk", name: "话术", base: 5, value: 5, category: "社交", checked: false },
        { id: "fightingBrawl", name: "格斗", base: 25, value: 25, category: "战斗", checked: false },
        { id: "firearmsHandgun", name: "射击/手枪", base: 20, value: 20, category: "战斗", checked: false },
        { id: "firearmsRifle", name: "射击/步枪霰弹枪", base: 25, value: 25, category: "战斗", checked: false },
        { id: "firstAid", name: "急救", base: 30, value: 30, category: "探索", checked: false },
        { id: "history", name: "历史", base: 5, value: 5, category: "知识", checked: false },
        { id: "intimidate", name: "恐吓", base: 15, value: 15, category: "社交", checked: false },
        { id: "jump", name: "跳跃", base: 20, value: 20, category: "行动", checked: false },
        { id: "languageOwn", name: "母语", base: 70, value: 70, category: "知识", checked: false },
        { id: "law", name: "法律", base: 5, value: 5, category: "知识", checked: false },
        { id: "libraryUse", name: "图书馆使用", base: 20, value: 20, category: "知识", checked: false },
        { id: "listen", name: "聆听", base: 20, value: 20, category: "探索", checked: false },
        { id: "locksmith", name: "锁匠", base: 1, value: 1, category: "探索", checked: false },
        { id: "mechanicalRepair", name: "机械维修", base: 10, value: 10, category: "行动", checked: false },
        { id: "medicine", name: "医学", base: 1, value: 1, category: "知识", checked: false },
        { id: "naturalWorld", name: "博物学", base: 10, value: 10, category: "知识", checked: false },
        { id: "navigate", name: "导航", base: 10, value: 10, category: "行动", checked: false },
        { id: "occult", name: "神秘学", base: 5, value: 5, category: "神话", checked: false },
        { id: "operateHeavyMachinery", name: "操作重型机械", base: 1, value: 1, category: "行动", checked: false },
        { id: "persuade", name: "说服", base: 10, value: 10, category: "社交", checked: false },
        { id: "photography", name: "摄影", base: 5, value: 5, category: "知识", checked: false },
        { id: "pilot", name: "驾驶/飞行器", base: 1, value: 1, category: "行动", checked: false },
        { id: "psychoanalysis", name: "精神分析", base: 1, value: 1, category: "探索", checked: false },
        { id: "psychology", name: "心理学", base: 10, value: 10, category: "社交", checked: false },
        { id: "ride", name: "骑术", base: 5, value: 5, category: "行动", checked: false },
        { id: "science", name: "科学", base: 1, value: 1, category: "知识", checked: false },
        { id: "scienceBiology", name: "科学/生物学", base: 1, value: 1, category: "知识", checked: false },
        { id: "scienceEngineering", name: "科学/工程学", base: 1, value: 1, category: "知识", checked: false },
        { id: "sciencePharmacy", name: "科学/药学", base: 1, value: 1, category: "知识", checked: false },
        { id: "mathematics", name: "数学", base: 10, value: 10, category: "知识", checked: false },
        { id: "sleightOfHand", name: "妙手", base: 10, value: 10, category: "行动", checked: false },
        { id: "spotHidden", name: "侦查", base: 25, value: 25, category: "探索", checked: false },
        { id: "stealth", name: "潜行", base: 20, value: 20, category: "行动", checked: false },
        { id: "survival", name: "生存", base: 10, value: 10, category: "行动", checked: false },
        { id: "swim", name: "游泳", base: 20, value: 20, category: "行动", checked: false },
        { id: "throw", name: "投掷", base: 20, value: 20, category: "行动", checked: false },
        { id: "track", name: "追踪", base: 10, value: 10, category: "探索", checked: false }
    ];

    let cards: COC7CharacterCard[] = [];
    let activeCardId = "";
    let activeCharacterFilter = "all";
    let assignableUsers: CharacterAssignableUser[] = [];
    let modal: BootstrapModalInstance | null = null;
    let nameGeneratorModal: BootstrapModalInstance | null = null;
    let occupationTemplateModal: BootstrapModalInstance | null = null;
    let pendingGeneratedName = "";
    let editorSkills: COC7Skill[] = [];
    let occupationSkillPointsManuallyEdited = false;
    let personalInterestPointsManuallyEdited = false;

    function clampNumber(value: unknown, min: number, max: number, fallback: number): number {
        const parsed = Number(value);
        if (!Number.isFinite(parsed)) return fallback;
        return Math.min(max, Math.max(min, Math.round(parsed)));
    }

    function rollDie(sides: number, random: () => number): number {
        return Math.floor(random() * sides) + 1;
    }

    function parseAttributeRollFormula(formulaText: string): AttributeRollFormula | null {
        const normalized = formulaText.trim().toLowerCase().replace(/\s+/g, "");
        const match = normalized.match(/^\(?(?<dice>\d+)d(?<sides>\d+)(?<bonus>[+-]\d+)?\)?(?:x(?<multiplier>\d+))?$/);
        if (!match?.groups) return null;
        const dice = clampNumber(match.groups.dice, 1, 20, 3);
        const sides = clampNumber(match.groups.sides, 2, 100, 6);
        const bonus = clampNumber(match.groups.bonus || 0, -100, 100, 0);
        const multiplier = clampNumber(match.groups.multiplier || 1, 1, 100, 5);
        return { dice, sides, bonus, multiplier };
    }

    function formatAttributeRollFormula(formula: AttributeRollFormula): string {
        const bonusText = formula.bonus > 0 ? `+${formula.bonus}` : formula.bonus < 0 ? String(formula.bonus) : "";
        const base = `${formula.dice}d${formula.sides}${bonusText}`;
        const wrapped = formula.bonus === 0 ? base : `(${base})`;
        return `${wrapped}x${formula.multiplier}`;
    }

    function rollAttributeFormula(formula: AttributeRollFormula, random: () => number = Math.random): number {
        let total = formula.bonus;
        for (let index = 0; index < formula.dice; index += 1) {
            total += rollDie(formula.sides, random);
        }
        return clampNumber(total * formula.multiplier, 1, 999, 50);
    }

    function normalizeRuleSettings(input?: CharacterRuleSettingsInput): CharacterRuleSettings {
        const rawRolls = input?.attributeRolls || DEFAULT_ATTRIBUTE_ROLLS;
        const attributeRolls = ATTRIBUTE_KEYS.reduce((settings, key) => {
            const parsed = parseAttributeRollFormula(rawRolls[key] || DEFAULT_ATTRIBUTE_ROLLS[key]);
            settings[key] = parsed ? formatAttributeRollFormula(parsed) : DEFAULT_ATTRIBUTE_ROLLS[key];
            return settings;
        }, {} as AttributeRollFormulaMap);
        return {
            attributeRatioPercent: clampNumber(input?.attributeRatioPercent, 1, 100, DEFAULT_RULE_SETTINGS.attributeRatioPercent),
            maxCardsPerUser: clampNumber(input?.maxCardsPerUser, 1, 999, DEFAULT_RULE_SETTINGS.maxCardsPerUser),
            attributeRolls
        };
    }

    function getConfigSection(name: string): Record<string, unknown> | null {
        const section = global.configManager?.getSection("general", name);
        return section && typeof section === "object" && !Array.isArray(section) ? section as Record<string, unknown> : null;
    }

    function loadRuleSettings(): CharacterRuleSettings {
        const configSection = getConfigSection("character_rules");
        const configRolls = ATTRIBUTE_KEYS.reduce((rolls, key) => {
            const value = configSection?.[`attribute_roll_${key.toLowerCase()}`];
            if (typeof value === "string") rolls[key] = value;
            return rolls;
        }, { ...DEFAULT_ATTRIBUTE_ROLLS } as AttributeRollFormulaMap);
        const storage = safeStorage();
        const localSettings = storage ? parseRuleSettingsFromStorage(storage.getItem(RULE_SETTINGS_STORAGE_KEY)) : null;
        return normalizeRuleSettings({
            attributeRatioPercent: localSettings?.attributeRatioPercent ?? configSection?.attribute_ratio_percent ?? DEFAULT_RULE_SETTINGS.attributeRatioPercent,
            maxCardsPerUser: configSection?.max_cards_per_user ?? localSettings?.maxCardsPerUser ?? DEFAULT_RULE_SETTINGS.maxCardsPerUser,
            attributeRolls: localSettings?.attributeRolls || configRolls
        });
    }

    function parseRuleSettingsFromStorage(raw: string | null): CharacterRuleSettings | null {
        if (!raw) return null;
        try {
            const parsed = JSON.parse(raw) as CharacterRuleSettingsInput;
            return normalizeRuleSettings(parsed);
        } catch {
            return null;
        }
    }

    function persistRuleSettings(settings: CharacterRuleSettings): void {
        const storage = safeStorage();
        if (storage) storage.setItem(RULE_SETTINGS_STORAGE_KEY, JSON.stringify(normalizeRuleSettings(settings)));
    }

    function randomizeAttributes(random: () => number = Math.random, settings: CharacterRuleSettings = loadRuleSettings()): COC7Attributes {
        const normalizedSettings = normalizeRuleSettings(settings);
        const roll = (key: COC7CoreAttributeKey): number => {
            const formula = parseAttributeRollFormula(normalizedSettings.attributeRolls[key]) || parseAttributeRollFormula(DEFAULT_ATTRIBUTE_ROLLS[key]);
            return formula ? rollAttributeFormula(formula, random) : 50;
        };
        return {
            STR: roll("STR"),
            DEX: roll("DEX"),
            SIZ: roll("SIZ"),
            APP: roll("APP"),
            CON: roll("CON"),
            INT: roll("INT"),
            POW: roll("POW"),
            EDU: roll("EDU"),
            LUC: roll("LUC"),
            AGE: 25
        };
    }

    function calculateMaxHp(attributes: COC7Attributes): number {
        return Math.floor((attributes.CON + attributes.SIZ) / 10);
    }

    function calculateMaxSan(attributes: COC7Attributes): number {
        return attributes.POW;
    }

    function calculateMaxMp(attributes: COC7Attributes): number {
        return Math.floor(attributes.POW / 5);
    }

    function calculateHalfAndFifth(value: number): COC7HalfAndFifth {
        const normalized = clampNumber(value, 0, 999, 0);
        return {
            half: Math.floor(normalized / 2),
            fifth: Math.floor(normalized / 5)
        };
    }

    function calculateAttributeDisplayValues(value: number, ratioPercent: number = loadRuleSettings().attributeRatioPercent): AttributeDisplayValues {
        const normalized = clampNumber(value, 0, 999, 0);
        return {
            half: Math.floor(normalized / 2),
            ratio: Math.floor(normalized * clampNumber(ratioPercent, 1, 100, 20) / 100)
        };
    }

    function calculateOccupationSkillPoints(attributes: COC7Attributes, occupationId: string): number {
        const occupation = getOccupationById(occupationId);
        return occupation.pointsFormula.reduce((total, term) => {
            if (typeof term === "string") return total + attributes[term];
            return total + attributes[term.attribute] * term.multiplier;
        }, 0);
    }

    function calculatePersonalInterestPoints(attributes: COC7Attributes): number {
        return attributes.INT * 2;
    }

    function calculateMov(attributes: COC7Attributes): number {
        let mov = 8;
        if (attributes.STR < attributes.SIZ && attributes.DEX < attributes.SIZ) mov = 7;
        if (attributes.STR > attributes.SIZ && attributes.DEX > attributes.SIZ) mov = 9;
        if (attributes.AGE >= 40) mov -= Math.floor((Math.min(attributes.AGE, 89) - 30) / 10);
        if (attributes.AGE >= 90) mov -= 6;
        return Math.max(1, mov);
    }

    function calculateBuildAndDamageBonus(attributes: Pick<COC7Attributes, "STR" | "SIZ">): { build: number; damageBonus: string } {
        const total = attributes.STR + attributes.SIZ;
        if (total <= 64) return { build: -2, damageBonus: "-2" };
        if (total <= 84) return { build: -1, damageBonus: "-1" };
        if (total <= 124) return { build: 0, damageBonus: "0" };
        if (total <= 164) return { build: 1, damageBonus: "+1D4" };
        if (total <= 204) return { build: 2, damageBonus: "+1D6" };
        const extra = Math.floor((total - 205) / 80);
        return { build: 3 + extra, damageBonus: `+${2 + extra}D6` };
    }

    function calculateEquipmentLoad(equipment: COC7EquipmentItem[]): { totalWeight: number; totalVolume: number } {
        return equipment.reduce((summary, item) => ({
            totalWeight: roundMetric(summary.totalWeight + item.weight * item.quantity),
            totalVolume: roundMetric(summary.totalVolume + (item.volume || 0) * item.quantity)
        }), { totalWeight: 0, totalVolume: 0 });
    }

    function roundMetric(value: number): number {
        return Math.round(value * 100) / 100;
    }

    function groupSkillsByCategory(skills: COC7Skill[]): Record<string, number> {
        return skills.reduce((summary, skill) => {
            summary[skill.category] = (summary[skill.category] || 0) + 1;
            return summary;
        }, {} as Record<string, number>);
    }

    function rankFromValue(value: number): SkillRank {
        if (value >= 70) return "主修";
        if (value >= 50) return "熟修";
        if (value >= 25) return "学习";
        return "新手";
    }

    function countSkillsByRank(skills: COC7Skill[]): Record<SkillRank, number> {
        return SKILL_RANKS.reduce((summary, rank) => {
            summary[rank] = skills.filter((skill) => (skill.rank || rankFromValue(skill.value)) === rank).length;
            return summary;
        }, {} as Record<SkillRank, number>);
    }

    function countSelectedOccupationSkills(skills: COC7Skill[]): number {
        return skills.filter((skill) => skill.checked || skill.occupation).length;
    }

    function getOccupationById(occupationId: string): COC7Occupation {
        return PRESET_OCCUPATIONS.find((occupation) => occupation.id === occupationId) || PRESET_OCCUPATIONS[0] as COC7Occupation;
    }

    function resolveOccupationFromInput(value: string): COC7Occupation {
        const normalized = value.trim();
        return PRESET_OCCUPATIONS.find((occupation) => occupation.id === normalized || occupation.name === normalized) || getOccupationById("writer");
    }

    function resolveOccupationIdFromInput(value: string): string {
        return resolveOccupationFromInput(value).id;
    }

    function resolveOccupationNameFromInput(value: string): string {
        return value.trim() || resolveOccupationFromInput(value).name;
    }

    function getOccupation(card: COC7CharacterCard): COC7Occupation {
        return getOccupationById(card.occupationId);
    }

    function getOccupationPassiveEffects(card: COC7CharacterCard): string[] {
        return [...getOccupation(card).passiveEffects];
    }

    function validateOccupationSkillSelection(card: COC7CharacterCard): COC7SkillAllocationSummary {
        const occupation = getOccupation(card);
        return {
            selectedOccupationSkills: countSelectedOccupationSkills(card.skills),
            requiredOccupationSkills: occupation.occupationSkills.length,
            creditRatingValid: card.creditRating >= occupation.creditRating[0] && card.creditRating <= occupation.creditRating[1],
            occupationPoints: card.occupationSkillPoints,
            personalInterestPoints: card.personalInterestPoints
        };
    }

    function autoAllocateOccupationSkills(card: COC7CharacterCard): COC7CharacterCard {
        const occupation = getOccupation(card);
        const bonusEntries = Object.entries(occupation.skillBonuses);
        const skills = card.skills.map((skill) => {
            const occupationSkill = occupation.occupationSkills.includes(skill.id);
            const bonusEntry = bonusEntries.find(([skillId]) => skillId === skill.id);
            const bonus = bonusEntry ? bonusEntry[1] : 0;
            const value = clampNumber(skill.value + bonus, 0, 99, skill.value);
            return {
                ...skill,
                checked: skill.checked || occupationSkill,
                occupation: skill.occupation || occupationSkill,
                value,
                rank: rankFromValue(value)
            };
        });
        return createCharacterCard({ ...card, skills });
    }

    function rollAttributeCheck(attributes: COC7Attributes, attributeKey: COC7AttributeKey, roller: () => number = () => Math.floor(Math.random() * 100) + 1): AttributeCheckResult {
        const target = attributes[attributeKey];
        const roll = clampNumber(roller(), 1, 100, 100);
        let level = "失败";
        if (roll === 1) level = "大成功";
        else if (roll <= Math.floor(target / 5)) level = "极难成功";
        else if (roll <= Math.floor(target / 2)) level = "困难成功";
        else if (roll <= target) level = "普通成功";
        else if (roll >= 96) level = "大失败";
        return { roll, target, success: roll <= target || roll === 1, level };
    }

    function generateInvestigatorName(gender: InvestigatorGender = "male", random: () => number = Math.random): string {
        return generateRegionalName("china", gender, random);
    }

    function generateRegionalName(region: NameRegion = "china", gender: InvestigatorGender = "unknown", random: () => number = Math.random): string {
        const source = REGIONAL_NAMES[region] || REGIONAL_NAMES.china;
        const givenPool = gender === "male" ? source.male : gender === "female" ? source.female : source.neutral;
        const family = pickRandom(source.family, random);
        const given = pickRandom(givenPool.length ? givenPool : source.neutral, random);
        return source.westernOrder ? `${given} ${family}` : `${family}${given}`;
    }

    function pickRandom(pool: string[], random: () => number): string {
        return pool[Math.floor(random() * pool.length)] || pool[0] || "";
    }

    function normalizeAttributes(input?: LegacyAttributesInput): COC7Attributes {
        return {
            STR: clampNumber(input?.STR, 1, 99, 50),
            DEX: clampNumber(input?.DEX, 1, 99, 50),
            SIZ: clampNumber(input?.SIZ, 1, 99, 50),
            APP: clampNumber(input?.APP, 1, 99, 50),
            CON: clampNumber(input?.CON, 1, 99, 50),
            INT: clampNumber(input?.INT, 1, 99, 50),
            POW: clampNumber(input?.POW, 1, 99, 50),
            EDU: clampNumber(input?.EDU, 1, 99, 50),
            LUC: clampNumber(input?.LUC ?? input?.LUK, 1, 99, 50),
            AGE: clampNumber(input?.AGE, 15, 99, 25)
        };
    }

    function normalizeNameGender(value: string | undefined): InvestigatorGender {
        return value === "male" || value === "female" || value === "unknown" ? value : "unknown";
    }

    function createCharacterCard(input: COC7CharacterCardInput = {}): COC7CharacterCard {
        const attributes = normalizeAttributes(input.attributes);
        const maxHp = calculateMaxHp(attributes);
        const maxSan = calculateMaxSan(attributes);
        const maxMp = calculateMaxMp(attributes);
        const damage = calculateBuildAndDamageBonus(attributes);
        const occupationId = input.occupationId || resolveOccupationIdFromInput(input.occupationName || "");
        const occupation = getOccupationById(occupationId);
        const now = new Date().toISOString();
        return {
            id: input.id || `investigator-${Date.now()}-${Math.random().toString(36).slice(2, 8)}`,
            name: input.name || generateInvestigatorName(normalizeNameGender(input.gender)),
            playerId: input.playerId || "",
            era: input.era || "1920s",
            gender: input.gender || "",
            age: attributes.AGE,
            avatar: input.avatar || "",
            occupationId,
            occupationName: input.occupationName || occupation.name,
            creditRating: clampNumber(input.creditRating, occupation.creditRating[0], occupation.creditRating[1], occupation.creditRating[0]),
            residence: input.residence || "",
            birthplace: input.birthplace || "",
            attributes,
            maxHp,
            currentHp: clampNumber(input.currentHp, 0, maxHp, maxHp),
            maxSan,
            initialSan: clampNumber(input.initialSan, 0, maxSan, maxSan),
            currentSan: clampNumber(input.currentSan, 0, maxSan, maxSan),
            magicPoints: clampNumber(input.magicPoints ?? input.currentMp, 0, maxMp, maxMp),
            currentMp: clampNumber(input.currentMp ?? input.magicPoints, 0, maxMp, maxMp),
            maxMp,
            status: normalizeStatus(input.status),
            occupationSkillPoints: clampNumber(input.occupationSkillPoints, 0, 999, calculateOccupationSkillPoints(attributes, occupationId)),
            personalInterestPoints: clampNumber(input.personalInterestPoints, 0, 999, calculatePersonalInterestPoints(attributes)),
            skillSuccessLimits: normalizeSkillSuccessLimits(input.skillSuccessLimits),
            mov: calculateMov(attributes),
            build: damage.build,
            damageBonus: damage.damageBonus,
            skills: normalizeSkills(input.skills, attributes, occupation),
            weapons: normalizeWeapons(input.weapons),
            equipment: normalizeEquipment(input.equipment),
            assets: {
                cash: clampNumber(input.assets?.cash, 0, 999999, 0),
                spendingLevel: clampNumber(input.assets?.spendingLevel, 0, 999999, 0),
                assetsText: input.assets?.assetsText || ""
            },
            background: normalizeBackground(input.background),
            relationships: normalizeRelationships(input.relationships),
            createdAt: input.createdAt || now,
            updatedAt: now
        };
    }

    function normalizeSkills(skills?: COC7Skill[], attributes?: COC7Attributes, occupation?: COC7Occupation): COC7Skill[] {
        const source = skills && skills.length ? mergeSkillCatalog(skills) : BASE_SKILLS;
        return source.map((skill) => {
            const base = calculateSkillBase(skill, attributes);
            const value = clampNumber(skill.value, 0, 99, Math.max(skill.base, base));
            const occupationSkill = occupation?.occupationSkills.includes(skill.id) || Boolean(skill.occupation);
            return {
            id: skill.id || slugify(skill.name),
            name: String(skill.name || "未命名技能").slice(0, 40),
            base,
            value,
            category: skill.category || "知识",
            checked: Boolean(skill.checked || occupationSkill),
            occupation: occupationSkill,
            specialty: skill.specialty || "",
            rank: skill.rank || rankFromValue(value)
        };
        });
    }

    function mergeSkillCatalog(skills: COC7Skill[]): COC7Skill[] {
        const byId = new Map(skills.map((skill) => [skill.id, skill]));
        return BASE_SKILLS.map((base) => ({ ...base, ...(byId.get(base.id) || {}) }));
    }

    function calculateSkillBase(skill: COC7Skill, attributes?: COC7Attributes): number {
        if (skill.id === "dodge" && attributes) return Math.floor(attributes.DEX / 2);
        if (skill.id === "languageOwn" && attributes) return attributes.EDU;
        return clampNumber(skill.base, 0, 99, 0);
    }

    function normalizeWeapons(weapons?: COC7Weapon[]): COC7Weapon[] {
        return (weapons || []).map((weapon) => ({
            name: weapon.name || "未命名武器",
            skill: weapon.skill || "格斗",
            damage: weapon.damage || "1D3",
            range: weapon.range || "接触",
            attacks: clampNumber(weapon.attacks, 1, 10, 1),
            ammo: clampNumber(weapon.ammo, 0, 999, 0),
            malfunction: clampNumber(weapon.malfunction, 0, 100, 100)
        }));
    }

    function normalizeEquipment(equipment?: COC7EquipmentItem[]): COC7EquipmentItem[] {
        return (equipment || []).map((item) => ({
            name: item.name || "未命名装备",
            quantity: clampNumber(item.quantity, 1, 999, 1),
            weight: Math.max(0, Number(item.weight) || 0),
            volume: Math.max(0, Number(item.volume) || 0),
            notes: item.notes || ""
        }));
    }

    function normalizeBackground(background?: Partial<COC7Background>): COC7Background {
        return {
            appearance: background?.appearance || "",
            ideology: background?.ideology || "",
            significantPeople: background?.significantPeople || "",
            meaningfulLocations: background?.meaningfulLocations || "",
            treasuredPossessions: background?.treasuredPossessions || "",
            traits: background?.traits || "",
            injuriesScars: background?.injuriesScars || "",
            phobiasManias: background?.phobiasManias || "",
            arcaneTomes: background?.arcaneTomes || "",
            encounters: background?.encounters || "",
            story: background?.story || "",
            education: background?.education || "",
            raceType: background?.raceType || "人类"
        };
    }

    function normalizeStatus(status?: Partial<CharacterStatusFlags>): CharacterStatusFlags {
        return {
            majorWound: Boolean(status?.majorWound),
            unconscious: Boolean(status?.unconscious),
            dead: Boolean(status?.dead),
            temporaryInsanity: Boolean(status?.temporaryInsanity),
            permanentInsanity: Boolean(status?.permanentInsanity),
            indefiniteInsanity: Boolean(status?.indefiniteInsanity)
        };
    }

    function normalizeSkillSuccessLimits(limits?: Partial<SkillSuccessLimits>): SkillSuccessLimits {
        return {
            occupation: clampNumber(limits?.occupation, 0, 99, 75),
            other: clampNumber(limits?.other, 0, 99, 50)
        };
    }

    function normalizeRelationships(relationships?: COC7Relationship[]): COC7Relationship[] {
        return (relationships || []).map((item) => ({
            name: item.name || "未命名关系",
            description: item.description || ""
        }));
    }

    function slugify(value: string): string {
        return value.toLowerCase().replace(/\s+/g, "-").replace(/[^a-z0-9\-\u4e00-\u9fa5]/g, "");
    }

    function cloneCard(card: COC7CharacterCard): COC7CharacterCard {
        return JSON.parse(JSON.stringify(card)) as COC7CharacterCard;
    }

    function safeStorage(): Storage | null {
        try { return global.localStorage || null; } catch { return null; }
    }

    function currentPlayerId(): string {
        return String(global.currentUser?.user_id ?? "");
    }

    function currentPlayerLabel(): string {
        const user = global.currentUser;
        if (!user) return "";
        return String(user.username || user.user_id || "");
    }

    function isBoundToCurrentPlayer(playerId: string): boolean {
        if (!playerId) return true;
        const user = global.currentUser;
        if (!user) return false;
        return playerId === String(user.user_id) || playerId === user.username;
    }

    function isCurrentUserElevated(): boolean {
        return ["ADMIN", "OWNER"].includes(global.currentUser?.role || "");
    }

    async function loadAssignableUsers(): Promise<void> {
        if (!isCurrentUserElevated()) {
            assignableUsers = [];
            return;
        }
        try {
            const response = await TrpgApi.get<ApiResponse<CharacterAssignableUser[]>>("/api/users");
            assignableUsers = response.success && Array.isArray(response.data) ? response.data : [];
            hydratePlayerOptions();
        } catch (error) {
            assignableUsers = [];
            console.warn("加载玩家列表失败:", error);
        }
    }

    function hydratePlayerOptions(): void {
        const list = byId<HTMLDataListElement>("characterPlayerOptions");
        if (!list) return;
        list.innerHTML = assignableUsers
            .filter((user) => user.status !== "banned")
            .map((user) => {
                const id = String(user.id);
                const username = String(user.username || user.id);
                return `<option value="${escapeHtml(username)}" label="${escapeHtml(id)}"></option>`;
            })
            .join("");
    }

    function playerDisplayName(playerId: string): string {
        if (!playerId || playerId === PLAYER_UNBOUND_LABEL) return PLAYER_UNBOUND_LABEL;
        const matchedUser = assignableUsers.find((user) => String(user.id) === playerId || user.username === playerId);
        if (matchedUser) return matchedUser.username || String(matchedUser.id);
        const currentUser = global.currentUser;
        if (currentUser && (String(currentUser.user_id ?? "") === playerId || currentUser.username === playerId)) {
            return currentUser.username || playerId;
        }
        return playerId;
    }

    function setPlayerBindingInputValue(playerId: string): void {
        setInputValue("characterBoundPlayer", playerDisplayName(playerId));
        const input = byId<HTMLInputElement>("characterBoundPlayer");
        if (input) {
            input.readOnly = !isCurrentUserElevated();
            input.placeholder = isCurrentUserElevated() ? "输入玩家 ID，或留空表示未绑定" : "";
        }
        updateUnbindButton(playerId);
    }

    function currentUserCharacterCards(): COC7CharacterCard[] {
        return cards.filter((card) => Boolean(card.playerId) && isBoundToCurrentPlayer(card.playerId));
    }

    function canCreateCharacterCard(): boolean {
        if (isCurrentUserElevated()) return true;
        const limit = loadRuleSettings().maxCardsPerUser;
        if (currentUserCharacterCards().length < limit) return true;
        notify(`普通用户最多只能拥有 ${limit} 张角色卡，请删除旧角色卡或联系管理员调整上限。`, "error");
        return false;
    }

    async function loadOccupationCatalogs(): Promise<void> {
        try {
            const response = await TrpgApi.get<ApiResponse<OccupationCatalogPayload[]>>("/api/character-catalogs/occupations");
            if (response.success && Array.isArray(response.data) && response.data.length) {
                PRESET_OCCUPATIONS = response.data.map(normalizeOccupationCatalog);
                hydrateOccupationSelect();
            }
        } catch (error) {
            console.warn("加载职业目录失败:", error);
        }
    }

    function normalizeOccupationCatalog(payload: OccupationCatalogPayload): COC7Occupation {
        const entries = payload.occupationSkills || [];
        const skillKeys = Array.from(new Set(entries.flatMap(occupationSkillKeys)));
        const minCredit = clampNumber(payload.creditRating?.min, 0, 99, 9);
        const maxCredit = clampNumber(payload.creditRating?.max, minCredit, 99, 30);
        return {
            id: payload.id || "writer",
            name: localizeOccupationName(payload.nameKey, payload.id),
            nameKey: payload.nameKey || "",
            creditRating: [minCredit, maxCredit],
            occupationSkills: skillKeys,
            pointsFormula: normalizeOccupationFormula(payload.occupationSkillPoints?.terms),
            occupationSkillEntries: entries,
            occupationSkillLabels: entries.map(occupationSkillEntryLabel),
            skillBonuses: {},
            specialties: [],
            passiveEffects: []
        };
    }

    function normalizeOccupationFormula(terms?: OccupationPointFormulaTerm[]): OccupationPointFormula {
        const validTerms = (terms || []).filter((term) => ATTRIBUTE_KEYS.includes(term.attribute as COC7CoreAttributeKey) || term.attribute === "AGE");
        return validTerms.length ? validTerms : [{ attribute: "EDU", multiplier: 4 }];
    }

    function occupationSkillKeys(entry: OccupationSkillEntry): string[] {
        if (entry.skillKey) return [entry.skillKey];
        if (entry.chooseOne) return entry.chooseOne.flatMap(occupationSkillKeys);
        return [];
    }

    function occupationSkillEntryLabel(entry: OccupationSkillEntry): string {
        if (entry.skillKey) return formatSkillLabel(entry.skillKey, entry.specialtyKey);
        if (entry.chooseOne) return entry.chooseOne.map(occupationSkillEntryLabel).join("或");
        if (entry.freeChoice === "personalOrEraSpecialty") return "任意一项其他个人或时代特长";
        return "自定义本职技能";
    }

    function formatSkillLabel(skillKey: string, specialtyKey?: string): string {
        const skillName = skillNameById(skillKey);
        if (!specialtyKey) return skillName;
        return `${skillName}(${SKILL_SPECIALTY_LABELS[`${skillKey}.${specialtyKey}`] || specialtyKey})`;
    }

    function localizeOccupationName(nameKey?: string, fallback?: string): string {
        return nameKey ? OCCUPATION_LABELS[nameKey] || fallback || nameKey : fallback || "未命名职业";
    }

    async function loadCards(): Promise<void> {
        cards = [];
        try {
            const response = await TrpgApi.get<ApiResponse<COC7CharacterCardInput[]>>("/api/characters");
            if (response.success && Array.isArray(response.data)) {
                cards = response.data.map((card) => createCharacterCard(card));
            }
        } catch (error) {
            console.warn("???????:", error);
        }

        const storage = safeStorage();
        if (storage) {
            try {
                const parsed = JSON.parse(storage.getItem(STORAGE_KEY) || "[]") as unknown;
                if (Array.isArray(parsed) && parsed.length) {
                    const migratedCards = parsed.map((card) => createCharacterCard(card as COC7CharacterCardInput));
                    for (const card of migratedCards) {
                        if (!cards.some((item) => item.id === card.id)) {
                            cards.push(card);
                            await saveCardToServer(card);
                        }
                    }
                    storage.removeItem(STORAGE_KEY);
                    storage.removeItem(ACTIVE_STORAGE_KEY);
                }
            } catch {
                storage.removeItem(STORAGE_KEY);
            }
        }
        activeCardId = cards[0]?.id || "";
    }

    async function saveCardToServer(card: COC7CharacterCard): Promise<COC7CharacterCard | null> {
        try {
            const response = await TrpgApi.put<ApiResponse<COC7CharacterCard>>(`/api/characters/${encodeURIComponent(card.id)}`, card);
            if (response.success && response.data) return createCharacterCard(response.data);
            notify(response.message || response.error || "???????", "error");
        } catch (error) {
            notify(`???????: ${characterErrorMessage(error)}`, "error");
        }
        return null;
    }

    function persistCards(): void {
        const card = cards.find((item) => item.id === activeCardId);
        if (!card) return;
        void saveCardToServer(card).then((savedCard) => {
            if (!savedCard) return;
            cards = cards.map((item) => item.id === savedCard.id ? savedCard : item);
            renderList();
        });
    }

    function byId<T extends HTMLElement = HTMLElement>(id: string): T | null {
        return typeof document === "undefined" ? null : document.getElementById(id) as T | null;
    }

    function initCharacterSheet(): void {
        if (typeof document === "undefined") return;
        const workspace = byId("characterWorkspace");
        if (!workspace || workspace.dataset.initialized === "true") return;
        workspace.dataset.initialized = "true";
        const modalElement = byId("characterModal");
        modal = modalElement && typeof bootstrap !== "undefined" ? new bootstrap.Modal(modalElement) : null;
        const nameModalElement = byId("nameGeneratorModal");
        nameGeneratorModal = nameModalElement && typeof bootstrap !== "undefined" ? new bootstrap.Modal(nameModalElement) : null;
        const occupationModalElement = byId("occupationTemplateModal");
        occupationTemplateModal = occupationModalElement && typeof bootstrap !== "undefined" ? new bootstrap.Modal(occupationModalElement) : null;
        hydrateOccupationSelect();
        bindEvents();
        void loadOccupationCatalogs().then(() => {
            void loadCards().then(render);
        });
        void loadAssignableUsers().then(render);
    }

    function bindEvents(): void {
        byId("createCharacter")?.addEventListener("click", () => {
            if (!canCreateCharacterCard()) return;
            openEditor();
        });
        byId("saveCharacter")?.addEventListener("click", saveFromEditor);
        byId("exportCharacter")?.addEventListener("click", exportActiveCard);
        byId("backToCharacterList")?.addEventListener("click", showCharacterList);
        byId("skillLevelFilters")?.addEventListener("click", handleCharacterFilterClick);
        byId("randomizeCharacterName")?.addEventListener("click", openNameGenerator);
        byId("regenerateName")?.addEventListener("click", regenerateNamePreview);
        byId("confirmGeneratedName")?.addEventListener("click", confirmGeneratedName);
        byId("cancelGeneratedName")?.addEventListener("click", () => nameGeneratorModal?.hide());
        byId("nameRegionSelect")?.addEventListener("change", regenerateNamePreview);
        byId("nameGenderSelect")?.addEventListener("change", regenerateNamePreview);
        byId("openOccupationTemplatePicker")?.addEventListener("click", openOccupationTemplatePicker);
        byId("characterAvatarPreview")?.addEventListener("click", () => byId<HTMLInputElement>("characterAvatarUpload")?.click());
        byId("unbindCharacterPlayer")?.addEventListener("click", unbindCharacterPlayerFromEditor);
        byId("randomizeAttributes")?.addEventListener("click", () => {
            const attributes = randomizeAttributes();
            ATTRIBUTE_KEYS.forEach((key) => setInputValue(`attribute${key}`, attributes[key]));
            setInputValue("characterAge", attributes.AGE);
            refreshEditorRuleSummary();
        });
        byId("saveCharacterRuleSettings")?.addEventListener("click", () => {
            void saveRuleSettingsFromPanel();
        });
        byId("characterOccupation")?.addEventListener("input", () => {
            occupationSkillPointsManuallyEdited = false;
            refreshEditorRuleSummary();
        });
        byId("characterCreditRating")?.addEventListener("input", refreshEditorRuleSummary);
        byId("characterOccupationSkillPoints")?.addEventListener("input", () => {
            occupationSkillPointsManuallyEdited = true;
            refreshSkillPointSummary();
        });
        byId("characterPersonalInterestPoints")?.addEventListener("input", () => {
            personalInterestPointsManuallyEdited = true;
            refreshSkillPointSummary();
        });
        byId("generateOccupationSkillPoints")?.addEventListener("click", () => {
            occupationSkillPointsManuallyEdited = false;
            setGeneratedOccupationSkillPoints();
            refreshSkillPointSummary();
        });
        byId("generatePersonalInterestPoints")?.addEventListener("click", () => {
            personalInterestPointsManuallyEdited = false;
            setGeneratedPersonalInterestPoints();
            refreshSkillPointSummary();
        });
        document.querySelectorAll<HTMLInputElement>(".character-attribute-input").forEach((input) => {
            input.addEventListener("input", () => {
                refreshEditorRuleSummary();
            });
        });
        byId("characterAge")?.addEventListener("input", () => {
            refreshEditorRuleSummary();
        });
        ["characterCurrentHp", "characterCurrentMp", "characterCurrentSan", "characterInitialSan"].forEach((fieldId) => {
            byId(fieldId)?.addEventListener("input", refreshEditorRuleSummary);
        });
        byId<HTMLInputElement>("characterAvatarUpload")?.addEventListener("change", handleAvatarUpload);
        hydrateRuleSettingsPanel();
    }

    function hydrateOccupationSelect(): void {
        const list = byId<HTMLDataListElement>("characterOccupationOptions");
        if (!list) return;
        list.innerHTML = PRESET_OCCUPATIONS.map((occupation) => `<option value="${escapeHtml(occupation.name)}"></option>`).join("");
    }

    function hydrateSkillChecklist(skills: COC7Skill[] = BASE_SKILLS): void {
        const container = byId("characterSkillChecklist");
        if (!container) return;
        const occupation = resolveOccupationFromInput(getInputValue("characterOccupation"));
        container.innerHTML = normalizeSkills(skills, readAttributes(), occupation).map((skill) => `
            <label class="skill-check-item">
                <input type="checkbox" data-skill-id="${escapeHtml(skill.id)}" ${skill.checked ? "checked" : ""}>
                <span>${escapeHtml(skill.name)}${skill.occupation ? " · 职业" : ""}</span>
                <input type="number" min="0" max="99" value="${skill.value}" data-skill-value="${escapeHtml(skill.id)}">
            </label>
        `).join("");
    }

    function openEditor(card?: COC7CharacterCard): void {
        if (card?.playerId && !isCurrentUserElevated() && !isBoundToCurrentPlayer(card.playerId)) {
            notify("该角色卡已绑定其他玩家，当前玩家不能编辑。", "error");
            return;
        }
        const target = card ? cloneCard(card) : createCharacterCard();
        setInputValue("characterEditingId", card?.id || "");
        setInputValue("characterName", target.name);
        const boundPlayerId = target.playerId && target.playerId !== PLAYER_UNBOUND_LABEL
            ? target.playerId
            : (isCurrentUserElevated() ? "" : currentPlayerId());
        setPlayerBindingInputValue(boundPlayerId);
        setInputValue("characterEra", target.era);
        setInputValue("characterOccupation", target.occupationName || getOccupation(target).name);
        setInputValue("characterCreditRating", target.creditRating);
        setInputValue("characterAge", target.age);
        setInputValue("characterGender", target.gender);
        setInputValue("raceType", target.background.raceType);
        setInputValue("characterResidence", target.residence);
        setInputValue("characterBirthplace", target.birthplace);
        ATTRIBUTE_KEYS.forEach((key) => setInputValue(`attribute${key}`, target.attributes[key]));
        setInputValue("appearance", target.background.appearance);
        setInputValue("education", target.background.education);
        setInputValue("characterBio", target.background.story);
        setInputValue("traits", target.background.traits);
        setInputValue("characterRelationships", target.relationships.map((item) => `${item.name}:${item.description}`).join("；"));
        setInputValue("characterMythos", target.background.encounters);
        setInputValue("characterWeapons", formatWeapons(target.weapons));
        setInputValue("characterEquipment", formatEquipment(target.equipment));
        setInputValue("characterAssets", formatAssets(target.assets));
        setInputValue("characterCurrentHp", target.currentHp);
        setInputValue("characterMaxHp", target.maxHp);
        setInputValue("characterCurrentMp", target.currentMp);
        setInputValue("characterMaxMp", target.maxMp);
        setInputValue("characterCurrentSan", target.currentSan);
        setInputValue("characterInitialSan", target.initialSan);
        setInputValue("characterMaxSan", target.maxSan);
        setInputValue("characterOccupationSkillPoints", target.occupationSkillPoints);
        setInputValue("characterPersonalInterestPoints", target.personalInterestPoints);
        setInputValue("characterOccupationSkillLimit", target.skillSuccessLimits.occupation);
        setInputValue("characterOtherSkillLimit", target.skillSuccessLimits.other);
        editorSkills = target.skills;
        occupationSkillPointsManuallyEdited = target.occupationSkillPoints !== calculateOccupationSkillPoints(target.attributes, target.occupationId);
        personalInterestPointsManuallyEdited = target.personalInterestPoints !== calculatePersonalInterestPoints(target.attributes);
        setEditorStatus(target.status);
        updateUnbindButton(boundPlayerId);
        updateAvatarPreview(target.avatar);
        refreshEditorRuleSummary();
        modal?.show();
    }

    function openNameGenerator(): void {
        const gender = normalizeNameGender(getInputValue("characterGender"));
        setInputValue("nameGenderSelect", gender);
        regenerateNamePreview();
        nameGeneratorModal?.show();
    }

    function regenerateNamePreview(): void {
        const region = (getInputValue("nameRegionSelect") || "china") as NameRegion;
        const gender = (getInputValue("nameGenderSelect") || "unknown") as InvestigatorGender;
        pendingGeneratedName = generateRegionalName(region, gender);
        setText("generatedNamePreview", pendingGeneratedName);
    }

    function confirmGeneratedName(): void {
        if (pendingGeneratedName) setInputValue("characterName", pendingGeneratedName);
        nameGeneratorModal?.hide();
    }

    function openOccupationTemplatePicker(): void {
        const container = byId("occupationTemplateList");
        if (!container) return;
        container.innerHTML = PRESET_OCCUPATIONS.map((occupation) => `
            <button type="button" class="occupation-template-card" data-occupation-id="${escapeHtml(occupation.id)}">
                <strong>${escapeHtml(occupation.name)}</strong>
                <span>信用评级 ${occupation.creditRating[0]}-${occupation.creditRating[1]}</span>
                <small>职业点：${formatOccupationPointFormula(occupation.pointsFormula)}</small>
                <small>本职技能：${(occupation.occupationSkillLabels || occupation.occupationSkills.map(skillNameById)).join("、")}</small>
            </button>
        `).join("");
        container.querySelectorAll<HTMLButtonElement>("[data-occupation-id]").forEach((button) => {
            button.addEventListener("click", () => applyOccupationTemplate(button.dataset.occupationId || "writer"));
        });
        occupationTemplateModal?.show();
    }

    function applyOccupationTemplate(occupationId: string): void {
        const occupation = getOccupationById(occupationId);
        setInputValue("characterOccupation", occupation.name);
        setInputValue("characterCreditRating", occupation.creditRating[0]);
        occupationSkillPointsManuallyEdited = false;
        refreshEditorRuleSummary();
        occupationTemplateModal?.hide();
    }

    function hydrateRuleSettingsPanel(): void {
        const settings = loadRuleSettings();
        setInputValue("attributeRatioPercent", settings.attributeRatioPercent);
        setInputValue("maxCardsPerUser", settings.maxCardsPerUser);
        ATTRIBUTE_KEYS.forEach((key) => setInputValue(`attributeRoll${key}`, settings.attributeRolls[key]));
        setText("characterRuleSettingsMessage", "");
    }

    async function saveRuleSettingsFromPanel(): Promise<void> {
        const nextSettings = normalizeRuleSettings({
            attributeRatioPercent: Number(getInputValue("attributeRatioPercent")),
            maxCardsPerUser: Number(getInputValue("maxCardsPerUser")),
            attributeRolls: ATTRIBUTE_KEYS.reduce((rolls, key) => {
                rolls[key] = getInputValue(`attributeRoll${key}`) || DEFAULT_ATTRIBUTE_ROLLS[key];
                return rolls;
            }, {} as AttributeRollFormulaMap)
        });
        persistRuleSettings(nextSettings);
        const generalConfig = global.configManager?.getConfig("general") || {};
        const characterRules = {
            ...(getConfigSection("character_rules") || {}),
            attribute_ratio_percent: nextSettings.attributeRatioPercent,
            max_cards_per_user: nextSettings.maxCardsPerUser,
            ...ATTRIBUTE_KEYS.reduce((rolls, key) => {
                rolls[`attribute_roll_${key.toLowerCase()}`] = nextSettings.attributeRolls[key];
                return rolls;
            }, {} as Record<string, string>)
        };
        const saved = await global.configManager?.saveConfig("general", {
            ...generalConfig,
            character_rules: characterRules
        });
        setText("characterRuleSettingsMessage", saved === false ? "?????????" : "????????");
        refreshEditorRuleSummary();
    }

    function skillNameById(skillId: string): string {
        return BASE_SKILLS.find((skill) => skill.id === skillId)?.name || skillId;
    }

    function formatOccupationPointFormula(formula: OccupationPointFormula): string {
        return formula.map((term) => typeof term === "string" ? term : `${term.attribute} * ${term.multiplier}`).join(" + ");
    }

    function handleAvatarUpload(event: Event): void {
        const input = event.target as HTMLInputElement | null;
        const file = input?.files?.[0];
        if (!file) return;
        const reader = new FileReader();
        reader.onload = () => {
            input.dataset.avatar = String(reader.result || "");
            updateAvatarPreview(input.dataset.avatar);
        };
        reader.readAsDataURL(file);
    }

    function updateAvatarPreview(src: string): void {
        const image = byId<HTMLImageElement>("characterAvatarPreviewImage");
        if (!image) return;
        image.src = src || "/assets/avatars/default.jpg";
    }

    function setInputValue(id: string, value: unknown): void {
        const field = byId<HTMLInputElement | HTMLTextAreaElement | HTMLSelectElement>(id);
        if (field) field.value = String(value ?? "");
    }

    function setCheckboxValue(id: string, checked: boolean): void {
        const field = byId<HTMLInputElement>(id);
        if (field) field.checked = checked;
    }

    function setText(id: string, value: string): void {
        const element = byId(id);
        if (element) element.textContent = value;
    }

    function getInputValue(id: string): string {
        return byId<HTMLInputElement | HTMLTextAreaElement | HTMLSelectElement>(id)?.value.trim() || "";
    }

    function getCheckboxValue(id: string): boolean {
        return byId<HTMLInputElement>(id)?.checked || false;
    }

    function readAttributes(): COC7Attributes {
        const coreAttributes = Object.fromEntries(ATTRIBUTE_KEYS.map((key) => [key, Number(getInputValue(`attribute${key}`))])) as LegacyAttributesInput;
        coreAttributes.AGE = Number(getInputValue("characterAge"));
        return normalizeAttributes(coreAttributes);
    }

    function setEditorStatus(status: CharacterStatusFlags): void {
        (Object.keys(STATUS_FIELD_IDS) as Array<keyof CharacterStatusFlags>).forEach((key) => {
            setCheckboxValue(STATUS_FIELD_IDS[key], status[key]);
        });
    }

    function readEditorStatus(): CharacterStatusFlags {
        return (Object.keys(STATUS_FIELD_IDS) as Array<keyof CharacterStatusFlags>).reduce((status, key) => {
            status[key] = getCheckboxValue(STATUS_FIELD_IDS[key]);
            return status;
        }, normalizeStatus());
    }

    function updateUnbindButton(playerId: string): void {
        const button = byId<HTMLButtonElement>("unbindCharacterPlayer");
        if (!button) return;
        button.hidden = !isCurrentUserElevated() || !playerId || playerId === PLAYER_UNBOUND_LABEL;
    }

    function unbindCharacterPlayerFromEditor(): void {
        if (!isCurrentUserElevated()) {
            notify("只有管理员可以解绑角色卡玩家。", "error");
            return;
        }
        setPlayerBindingInputValue("");
    }

    function syncAttributeDerivedFields(attributes: COC7Attributes = readAttributes()): void {
        const ratioPercent = loadRuleSettings().attributeRatioPercent;
        ATTRIBUTE_KEYS.forEach((key) => {
            const derived = calculateAttributeDisplayValues(attributes[key], ratioPercent);
            setInputValue(`attribute${key}Half`, derived.half);
            setInputValue(`attribute${key}Ratio`, derived.ratio);
        });
    }

    function syncEditorResourceLimits(attributes: COC7Attributes = readAttributes()): void {
        const maxHp = calculateMaxHp(attributes);
        const maxMp = calculateMaxMp(attributes);
        const maxSan = calculateMaxSan(attributes);
        setInputValue("characterMaxHp", maxHp);
        setInputValue("characterMaxMp", maxMp);
        setInputValue("characterMaxSan", maxSan);
        setInputValue("characterCurrentHp", clampNumber(getInputValue("characterCurrentHp"), 0, maxHp, maxHp));
        setInputValue("characterCurrentMp", clampNumber(getInputValue("characterCurrentMp"), 0, maxMp, maxMp));
        setInputValue("characterCurrentSan", clampNumber(getInputValue("characterCurrentSan"), 0, maxSan, maxSan));
        setInputValue("characterInitialSan", clampNumber(getInputValue("characterInitialSan"), 0, maxSan, maxSan));
    }

    function updateAttributeRollHints(): void {
        const settings = loadRuleSettings();
        document.querySelectorAll<HTMLElement>("[data-attribute-roll]").forEach((element) => {
            const key = element.dataset.attributeRoll as COC7CoreAttributeKey | undefined;
            if (key && ATTRIBUTE_KEYS.includes(key)) element.textContent = settings.attributeRolls[key];
        });
    }

    function readChecklistSkills(): COC7Skill[] {
        const container = byId("characterSkillChecklist");
        if (!container) return editorSkills.length ? editorSkills : normalizeSkills(undefined, readAttributes(), resolveOccupationFromInput(getInputValue("characterOccupation")));
        const occupation = resolveOccupationFromInput(getInputValue("characterOccupation"));
        return BASE_SKILLS.map((base) => {
            const checked = container.querySelector<HTMLInputElement>(`[data-skill-id="${CSS.escape(base.id)}"]`)?.checked || false;
            const value = Number(container.querySelector<HTMLInputElement>(`[data-skill-value="${CSS.escape(base.id)}"]`)?.value || base.value);
            const occupationSkill = occupation.occupationSkills.includes(base.id);
            return { ...base, checked, occupation: occupationSkill, value: clampNumber(value, 0, 99, base.base), rank: rankFromValue(value) };
        });
    }

    function refreshEditorRuleSummary(): void {
        const attributes = readAttributes();
        syncAttributeDerivedFields(attributes);
        syncEditorResourceLimits(attributes);
        syncGeneratedSkillPointInputs(false);
        refreshSkillPointSummary();
        updateAttributeRollHints();
    }

    function syncGeneratedSkillPointInputs(force: boolean): void {
        if (force || !occupationSkillPointsManuallyEdited) {
            setGeneratedOccupationSkillPoints();
        }
        if (force || !personalInterestPointsManuallyEdited) {
            setGeneratedPersonalInterestPoints();
        }
        refreshSkillPointSummary();
    }

    function setGeneratedOccupationSkillPoints(): void {
        setInputValue("characterOccupationSkillPoints", calculateOccupationSkillPoints(readAttributes(), resolveOccupationIdFromInput(getInputValue("characterOccupation"))));
    }

    function setGeneratedPersonalInterestPoints(): void {
        setInputValue("characterPersonalInterestPoints", calculatePersonalInterestPoints(readAttributes()));
    }

    function refreshSkillPointSummary(): void {
        const occupation = resolveOccupationFromInput(getInputValue("characterOccupation"));
        const spent = calculateEditorSkillPointSpending(occupation);
        const occupationTotal = clampNumber(getInputValue("characterOccupationSkillPoints"), 0, 999, 0);
        const personalTotal = clampNumber(getInputValue("characterPersonalInterestPoints"), 0, 999, 0);
        setText("characterOccupationSkillPointsRemaining", `剩余 ${Math.max(0, occupationTotal - spent.occupation)}`);
        setText("characterPersonalInterestPointsRemaining", `剩余 ${Math.max(0, personalTotal - spent.personal)}`);
    }

    function calculateEditorSkillPointSpending(occupation: COC7Occupation): { occupation: number; personal: number } {
        return readChecklistSkills().reduce((summary, skill) => {
            const spent = Math.max(0, skill.value - skill.base);
            if (occupation.occupationSkills.includes(skill.id) || skill.occupation) summary.occupation += spent;
            else summary.personal += spent;
            return summary;
        }, { occupation: 0, personal: 0 });
    }

    function autoAllocateEditorOccupationSkills(): void {
        const card = createCharacterCard({
            occupationId: resolveOccupationIdFromInput(getInputValue("characterOccupation")),
            occupationName: resolveOccupationNameFromInput(getInputValue("characterOccupation")),
            creditRating: Number(getInputValue("characterCreditRating") || "0"),
            attributes: readAttributes(),
            skills: readChecklistSkills()
        });
        hydrateSkillChecklist(autoAllocateOccupationSkills(card).skills);
        refreshEditorRuleSummary();
    }

    function resolveEditorPlayerId(existing?: COC7CharacterCard): string {
        const boundDisplayValue = getInputValue("characterBoundPlayer").trim();
        if (isCurrentUserElevated()) {
            if (!boundDisplayValue || boundDisplayValue === PLAYER_UNBOUND_LABEL) return "";
            const matchedUser = assignableUsers.find((user) => {
                const userId = String(user.id);
                return userId === boundDisplayValue || user.username === boundDisplayValue;
            });
            return matchedUser ? String(matchedUser.id) : boundDisplayValue;
        }
        if (existing?.playerId && !isBoundToCurrentPlayer(existing.playerId)) return existing.playerId;
        return currentPlayerId();
    }

    function validatePlayerBinding(cardId: string, playerId: string, existing?: COC7CharacterCard): boolean {
        if (!playerId) return true;
        if (!isCurrentUserElevated() && existing?.playerId && !isBoundToCurrentPlayer(existing.playerId)) {
            notify("该角色卡已绑定其他玩家，当前玩家不能使用。", "error");
            return false;
        }
        if (!isCurrentUserElevated() && existing?.playerId && existing.playerId !== playerId) {
            notify("该角色卡已绑定其他玩家，只有管理员可以解绑后重新绑定。", "error");
            return false;
        }
        return true;
    }

    function saveFromEditor(): void {
        const editingId = getInputValue("characterEditingId");
        const existing = cards.find((card) => card.id === editingId);
        const attributes = readAttributes();
        const maxHp = calculateMaxHp(attributes);
        const maxMp = calculateMaxMp(attributes);
        const maxSan = calculateMaxSan(attributes);
        const nextCardId = editingId || `investigator-${Date.now()}-${Math.random().toString(36).slice(2, 8)}`;
        const playerId = resolveEditorPlayerId(existing);
        if (!validatePlayerBinding(nextCardId, playerId, existing)) return;
        const avatarInput = byId<HTMLInputElement>("characterAvatarUpload");
        const age = Number(getInputValue("characterAge") || attributes.AGE);
        attributes.AGE = clampNumber(age, 15, 99, attributes.AGE);
        const occupationName = resolveOccupationNameFromInput(getInputValue("characterOccupation"));
        const cardInput: Partial<COC7CharacterCard> = {
            ...existing,
            id: nextCardId,
            name: getInputValue("characterName") || generateInvestigatorName(),
            playerId,
            era: getInputValue("characterEra") || "1920s",
            gender: getInputValue("characterGender"),
            occupationId: resolveOccupationIdFromInput(occupationName),
            occupationName,
            creditRating: Number(getInputValue("characterCreditRating") || "0"),
            avatar: avatarInput?.dataset.avatar || existing?.avatar || "",
            residence: getInputValue("characterResidence"),
            birthplace: getInputValue("characterBirthplace"),
            attributes,
            currentHp: clampNumber(getInputValue("characterCurrentHp"), 0, maxHp, maxHp),
            currentMp: clampNumber(getInputValue("characterCurrentMp"), 0, maxMp, maxMp),
            magicPoints: clampNumber(getInputValue("characterCurrentMp"), 0, maxMp, maxMp),
            maxMp,
            initialSan: clampNumber(getInputValue("characterInitialSan"), 0, maxSan, maxSan),
            currentSan: clampNumber(getInputValue("characterCurrentSan"), 0, maxSan, maxSan),
            status: readEditorStatus(),
            occupationSkillPoints: clampNumber(getInputValue("characterOccupationSkillPoints"), 0, 999, calculateOccupationSkillPoints(attributes, resolveOccupationIdFromInput(occupationName))),
            personalInterestPoints: clampNumber(getInputValue("characterPersonalInterestPoints"), 0, 999, calculatePersonalInterestPoints(attributes)),
            skillSuccessLimits: {
                occupation: clampNumber(getInputValue("characterOccupationSkillLimit"), 0, 99, 75),
                other: clampNumber(getInputValue("characterOtherSkillLimit"), 0, 99, 50)
            },
            skills: readChecklistSkills(),
            weapons: parseWeapons(getInputValue("characterWeapons")),
            equipment: parseEquipment(getInputValue("characterEquipment")),
            assets: parseAssets(getInputValue("characterAssets")),
            background: {
                ...normalizeBackground(existing?.background),
                appearance: getInputValue("appearance"),
                education: getInputValue("education"),
                story: getInputValue("characterBio"),
                traits: getInputValue("traits"),
                encounters: getInputValue("characterMythos"),
                raceType: getInputValue("raceType") || "人类"
            },
            relationships: parseRelationships(getInputValue("characterRelationships"))
        };
        const card = createCharacterCard(cardInput);
        if (!validatePlayerBinding(card.id, card.playerId, existing)) return;
        cards = existing ? cards.map((item) => item.id === editingId ? card : item) : [card, ...cards];
        activeCardId = card.id;
        persistCards();
        renderList();
        openCharacterDetail(card.id);
        modal?.hide();
    }

    function render(): void {
        renderList();
        showCharacterList();
    }

    function handleCharacterFilterClick(event: Event): void {
        const button = (event.target as HTMLElement).closest<HTMLButtonElement>("[data-rank-filter]");
        if (!button) return;
        activeCharacterFilter = button.dataset.rankFilter || "all";
        document.querySelectorAll<HTMLElement>("#skillLevelFilters [data-rank-filter]").forEach((item) => {
            item.classList.toggle("active", item === button);
        });
        renderList();
    }

    function filteredCards(): COC7CharacterCard[] {
        if (activeCharacterFilter === "mine") {
            return cards.filter((card) => Boolean(card.playerId) && isBoundToCurrentPlayer(card.playerId));
        }
        if (activeCharacterFilter === "all") return cards;
        return cards.filter((card) => card.skills.some((skill) => (skill.rank || rankFromValue(skill.value)) === activeCharacterFilter));
    }

    function renderList(): void {
        const list = byId("characterList");
        if (!list) return;
        const visibleCards = filteredCards();
        if (visibleCards.length === 0) {
            list.innerHTML = `<div class="character-empty-filter">没有符合筛选条件的角色卡。</div>`;
            return;
        }
        list.innerHTML = visibleCards.map(renderCharacterCardSummary).join("");
        list.querySelectorAll<HTMLElement>(".character-card").forEach((cardElement) => {
            cardElement.addEventListener("click", (event) => {
                const id = cardElement.dataset.characterId || "";
                const action = (event.target as HTMLElement).closest<HTMLButtonElement>("[data-action]")?.dataset.action || "detail";
                const card = cards.find((item) => item.id === id);
                if (!card) return;
                if (action === "edit") openEditor(card);
                else if (action === "delete") deleteCard(id);
                else openCharacterDetail(id);
            });
        });
    }

    function renderCharacterCardSummary(card: COC7CharacterCard): string {
        return `
            <article class="character-card ${card.id === activeCardId ? "active" : ""}" data-character-id="${escapeHtml(card.id)}">
                <div class="character-card-avatar">${card.avatar ? `<img src="${escapeHtml(card.avatar)}" alt="">` : `<i class="fa fa-id-card-o"></i>`}</div>
                <h5>${escapeHtml(card.name)}</h5>
                <p>${escapeHtml(getOccupation(card).name)} · ${escapeHtml(card.residence || "未知居住地")}</p>
                <div class="character-card-metrics">
                    <span>HP 上限 ${card.maxHp}</span>
                    <span>SAN 上限 ${card.maxSan}</span>
                    <span>MOV ${card.mov}</span>
                </div>
                <div class="character-card-actions">
                    <button type="button" data-action="detail"><i class="fa fa-eye"></i> 详情</button>
                    <button type="button" data-action="edit"><i class="fa fa-pencil"></i> 编辑</button>
                    <button type="button" data-action="delete"><i class="fa fa-trash"></i> 删除</button>
                </div>
            </article>
        `;
    }

    function openCharacterDetail(cardId: string): void {
        const card = cards.find((item) => item.id === cardId) || cards[0];
        const listView = byId("character-list-view");
        const detailPage = byId("character-detail-page");
        const detail = byId("characterDetailView");
        const empty = document.querySelector<HTMLElement>(".character-empty-state");
        if (!detail || !card) return;
        activeCardId = card.id;
        persistCards();
        if (listView) listView.hidden = true;
        if (detailPage) detailPage.hidden = false;
        if (empty) empty.hidden = true;
        detail.hidden = false;
        detail.innerHTML = renderCharacterDetail(card);
        document.querySelectorAll(".character-card").forEach((item) => item.classList.toggle("active", (item as HTMLElement).dataset.characterId === card.id));
        detail.querySelector<HTMLButtonElement>("[data-character-edit-active]")?.addEventListener("click", () => openEditor(card));
    }

    function showCharacterList(): void {
        const listView = byId("character-list-view");
        const detailPage = byId("character-detail-page");
        const detail = byId("characterDetailView");
        const empty = document.querySelector<HTMLElement>(".character-empty-state");
        if (listView) listView.hidden = false;
        if (detailPage) detailPage.hidden = true;
        if (detail) detail.hidden = true;
        if (empty) empty.hidden = false;
        document.querySelectorAll(".character-card").forEach((item) => item.classList.remove("active"));
    }

    function renderCharacterDetail(card: COC7CharacterCard): string {
        const occupation = getOccupation(card);
        const load = calculateEquipmentLoad(card.equipment);
        const groups = groupSkillsByCategory(card.skills);
        const allocation = validateOccupationSkillSelection(card);
        return `
            <header class="character-inspector-header">
                <div>
                    <h3>${escapeHtml(card.name)}</h3>
                    <div class="character-tag-row">
                        <span class="character-tag">${escapeHtml(occupation.name)}</span>
                        <span class="character-tag">绑定玩家 ${escapeHtml(playerDisplayName(card.playerId))}</span>
                        <span class="character-tag">信用评级 ${occupation.creditRating[0]}-${occupation.creditRating[1]}</span>
                        <span class="character-tag">当前信用 ${card.creditRating}</span>
                        <span class="character-tag">伤害加值 ${escapeHtml(card.damageBonus)}</span>
                        <span class="character-tag">体格 ${card.build}</span>
                    </div>
                </div>
                <div class="character-inline-actions"><button type="button" data-character-edit-active><i class="fa fa-pencil"></i> 编辑角色卡</button></div>
            </header>
            <section class="character-section"><h4>属性</h4><div class="character-attribute-grid">${ATTRIBUTE_KEYS.map((key) => renderAttributeChip(key, card.attributes[key])).join("")}</div></section>
            <section class="character-section"><h4>状态</h4><div class="character-vital-grid">${statCard("生命 HP", `${card.currentHp} / ${card.maxHp}`)}${statCard("魔法 MP", `${card.currentMp} / ${card.maxMp}`)}${statCard("理智 SAN", `${card.currentSan} / ${card.initialSan} / ${card.maxSan}`)}${statCard("人物状态", statusSummary(card.status))}${statCard("幸运", card.attributes.LUC)}${statCard("移动速度", card.mov)}${statCard("职业技能点", card.occupationSkillPoints)}${statCard("兴趣点", card.personalInterestPoints)}${statCard("职业技能", `${allocation.selectedOccupationSkills}/${allocation.requiredOccupationSkills}`)}</div></section>
            <section class="character-section"><h4>技能等级</h4><div class="character-card-metrics">${Object.entries(groups).map(([group, total]) => `<span>${escapeHtml(group)} ${total}</span>`).join("")}</div><div class="character-skill-grid">${card.skills.map(renderSkillCard).join("")}</div></section>
            <section class="character-section"><h4>武器</h4>${card.weapons.map((weapon) => `<div class="equipment-row"><strong>${escapeHtml(weapon.name)}</strong><br><small>${escapeHtml(weapon.skill)} · ${escapeHtml(weapon.damage)} · ${escapeHtml(weapon.range)}</small></div>`).join("") || `<div class="background-note">暂无武器</div>`}</section>
            <section class="character-section"><h4>战斗物品与装备资产</h4>${statCard("总重量", `${load.totalWeight} kg`)}${statCard("现金", card.assets.cash)}${statCard("消费水平", card.assets.spendingLevel)}<div class="background-note">${escapeHtml(card.assets.assetsText || "暂无资产")}</div>${card.equipment.map(renderEquipmentRow).join("")}</section>
            <section class="character-section"><h4>背景故事与人际关系</h4><div class="background-grid">${backgroundNote("外貌特征", card.background.appearance)}${backgroundNote("思想信念", card.background.ideology)}${backgroundNote("重要之人", card.background.significantPeople)}${backgroundNote("克苏鲁神话", card.background.encounters)}${backgroundNote("故事经历", card.background.story)}${backgroundNote("人际关系", card.relationships.map((item) => `${item.name}: ${item.description}`).join("；"))}</div></section>
        `;
    }

    function deleteCard(id: string): void {
        if (cards.length <= 1) return;
        cards = cards.filter((card) => card.id !== id);
        activeCardId = cards[0]?.id || "";
        persistCards();
        render();
    }

    function statCard(label: string, value: unknown): string {
        return `<div class="character-stat-card"><span>${escapeHtml(label)}</span><strong>${escapeHtml(value)}</strong></div>`;
    }

    function statusSummary(status: CharacterStatusFlags): string {
        const labels: Array<[keyof CharacterStatusFlags, string]> = [
            ["majorWound", "重伤"],
            ["unconscious", "昏迷"],
            ["dead", "死亡"],
            ["temporaryInsanity", "临时疯狂"],
            ["permanentInsanity", "永久疯狂"],
            ["indefiniteInsanity", "不定期疯狂"]
        ];
        const active = labels.filter(([key]) => status[key]).map(([, label]) => label);
        return active.length ? active.join("、") : "正常";
    }

    function renderAttributeChip(key: COC7CoreAttributeKey, value: number): string {
        const derived = calculateAttributeDisplayValues(value);
        return `<div class="attribute-chip"><span>${ATTRIBUTE_LABELS[key]} (${key})</span><strong>${value}</strong><small>半 ${derived.half} / 比 ${derived.ratio}</small></div>`;
    }

    function renderSkillCard(skill: COC7Skill): string {
        return `<div class="skill-card"><div class="skill-card-header"><strong>${escapeHtml(skill.name)}</strong><span>${escapeHtml(skill.rank || rankFromValue(skill.value))} · ${escapeHtml(skill.category)}</span></div><div class="skill-card-meter"><span style="width:${skill.value}%"></span></div><small>${skill.value}</small></div>`;
    }

    function renderEquipmentRow(item: COC7EquipmentItem): string {
        return `<div class="equipment-row"><strong>${escapeHtml(item.name)}</strong> x ${item.quantity}<br><small>${item.weight} kg ${escapeHtml(item.notes || "")}</small></div>`;
    }

    function backgroundNote(label: string, value: string): string {
        return `<div class="background-note"><strong>${escapeHtml(label)}</strong><p>${escapeHtml(value || "未填写")}</p></div>`;
    }

    function formatSkills(skills: COC7Skill[]): string {
        return skills.map((skill) => `${skill.name}:${skill.value}:${skill.category}`).join("；");
    }

    function parseSkills(raw: string): COC7Skill[] {
        return raw.split(/[;\n；]+/).map((line) => line.trim()).filter(Boolean).map((line) => {
            const [name, value, category] = line.split(/[:：]/).map((part) => part.trim());
            return { id: slugify(name || ""), name: name || "未命名技能", base: 0, value: clampNumber(value, 0, 99, 0), category: category || "知识", checked: false, rank: rankFromValue(Number(value)) };
        });
    }

    function mergeManualSkills(base: COC7Skill[], manual: COC7Skill[]): COC7Skill[] {
        const ids = new Set(base.map((skill) => skill.id));
        return [...base, ...manual.filter((skill) => !ids.has(skill.id))];
    }

    function formatWeapons(weapons: COC7Weapon[]): string {
        return weapons.map((weapon) => `${weapon.name}:${weapon.skill}:${weapon.damage}:${weapon.range}:${weapon.attacks}:${weapon.ammo}:${weapon.malfunction}`).join("；");
    }

    function parseWeapons(raw: string): COC7Weapon[] {
        return raw.split(/[;\n；]+/).map((line) => line.trim()).filter(Boolean).map((line) => {
            const [name, skill, damage, range, attacks, ammo, malfunction] = line.split(/[:：]/).map((part) => part.trim());
            return { name: name || "未命名武器", skill: skill || "格斗", damage: damage || "1D3", range: range || "接触", attacks: clampNumber(attacks, 1, 10, 1), ammo: clampNumber(ammo, 0, 999, 0), malfunction: clampNumber(malfunction, 0, 100, 100) };
        });
    }

    function formatEquipment(equipment: COC7EquipmentItem[]): string {
        return equipment.map((item) => `${item.name}:${item.quantity}:${item.weight}:${item.notes || ""}`).join("；");
    }

    function parseEquipment(raw: string): COC7EquipmentItem[] {
        return raw.split(/[;\n；]+/).map((line) => line.trim()).filter(Boolean).map((line) => {
            const [name, quantity, weight, notes] = line.split(/[:：]/).map((part) => part.trim());
            return { name: name || "未命名装备", quantity: clampNumber(quantity, 1, 999, 1), weight: Math.max(0, Number(weight) || 0), volume: 0, notes: notes || "" };
        });
    }

    function formatAssets(assets: COC7Assets): string {
        return `现金:${assets.cash}；消费水平:${assets.spendingLevel}；资产:${assets.assetsText}`;
    }

    function parseAssets(raw: string): COC7Assets {
        const assets: COC7Assets = { cash: 0, spendingLevel: 0, assetsText: "" };
        raw.split(/[;\n；]+/).forEach((line) => {
            const [key, value] = line.split(/[:：]/).map((part) => part.trim());
            if (key === "现金") assets.cash = clampNumber(value, 0, 999999, 0);
            else if (key === "消费水平") assets.spendingLevel = clampNumber(value, 0, 999999, 0);
            else if (key === "资产") assets.assetsText = value || "";
        });
        return assets;
    }

    function parseRelationships(raw: string): COC7Relationship[] {
        return raw.split(/[;\n；]+/).map((line) => line.trim()).filter(Boolean).map((line) => {
            const [name, description] = line.split(/[:：]/).map((part) => part.trim());
            return { name: name || "未命名关系", description: description || "" };
        });
    }

    function exportActiveCard(): void {
        const card = cards.find((item) => item.id === activeCardId);
        if (!card) return;
        const payload = JSON.stringify(card, null, 2);
        if (navigator.clipboard?.writeText) {
            void navigator.clipboard.writeText(payload).then(() => notify("角色卡 JSON 已复制到剪贴板。", "success"));
        } else {
            console.log(payload);
            notify("当前浏览器不支持剪贴板写入，角色卡 JSON 已输出到控制台。", "error");
        }
    }

    function listCharacterCards(): COC7CharacterCard[] {
        const availableCards = isCurrentUserElevated()
            ? cards
            : currentUserCharacterCards();
        return availableCards.map(cloneCard);
    }

    function getCharacterCardSnapshot(cardId: string): Partial<COC7CharacterCard> | null {
        const card = cards.find((item) => item.id === cardId);
        return card ? cloneCard(card) : null;
    }

    function notify(message: string, type = "info"): void {
        const notifier = (global as unknown as { showNotification?: (message: string, type?: string) => void }).showNotification;
        if (typeof notifier === "function") notifier(message, type);
    }

    function characterErrorMessage(error: unknown): string {
        return error instanceof Error ? error.message : String(error);
    }

    function escapeHtml(value: unknown): string {
        return String(value ?? "")
            .replace(/&/g, "&amp;")
            .replace(/</g, "&lt;")
            .replace(/>/g, "&gt;")
            .replace(/"/g, "&quot;")
            .replace(/'/g, "&#039;");
    }

    const api: CharacterApi = {
        ATTRIBUTE_KEYS,
        SKILL_RANKS,
        BASE_SKILLS,
        PRESET_OCCUPATIONS,
        calculateHalfAndFifth,
        calculateAttributeDisplayValues,
        calculateMaxHp,
        calculateMaxSan,
        calculateMaxMp,
        calculateMov,
        calculateOccupationSkillPoints,
        calculatePersonalInterestPoints,
        calculateBuildAndDamageBonus,
        calculateEquipmentLoad,
        groupSkillsByCategory,
        countSkillsByRank,
        countSelectedOccupationSkills,
        validateOccupationSkillSelection,
        autoAllocateOccupationSkills,
        getOccupationPassiveEffects,
        rollAttributeCheck,
        generateInvestigatorName,
        generateRegionalName,
        parseAttributeRollFormula,
        rollAttributeFormula,
        randomizeAttributes,
        createCharacterCard,
        listCharacterCards,
        getCharacterCardSnapshot,
        initCharacterSheet
    };

    global.COC7CharacterSheet = api;
})(typeof window !== "undefined" ? window : globalThis as Window & typeof globalThis);

