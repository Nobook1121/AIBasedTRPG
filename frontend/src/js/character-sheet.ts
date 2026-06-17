type COC7CoreAttributeKey = "STR" | "DEX" | "SIZ" | "APP" | "CON" | "INT" | "POW" | "EDU" | "LUC";
type COC7AttributeKey = COC7CoreAttributeKey | "AGE";
type SkillRank = "新手" | "学习" | "熟修" | "主修";
type SkillCategory = "特殊" | "探索" | "社交" | "战斗" | "医疗" | "运动" | "知识" | "技术" | "操纵" | "其他";
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
    skillKey?: string;
    name: string;
    value: number;
    base: number;
    category: SkillCategory | string;
    checked: boolean;
    occupation?: boolean;
    specialty?: string;
    specialtyKey?: string;
    occupationPoints?: number;
    interestPoints?: number;
    growthPoints?: number;
    rank?: SkillRank;
}

interface COC7SkillWithSource extends COC7Skill {
    skillKey?: string;
}

interface SkillSpecialtyCatalogEntry {
    key: string;
    labelKey: string;
}

interface SkillCatalogEntry {
    key: string;
    labelKey: string;
    category: SkillCategory;
    base: number;
    repeatable: number;
    specialties: SkillSpecialtyCatalogEntry[];
    eraLimited?: boolean;
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
    skillKey?: string;
    specialtyKey?: string;
    damage: string;
    range: string;
    impale: boolean | null;
    attacks: string;
    ammo: string;
    malfunction: string;
}

interface WeaponCatalogPayload {
    id: string;
    name: string;
    skill: {
        skillKey?: string;
        specialtyKey?: string;
        label?: string;
    };
    damage: string;
    attacks: string;
    impale: boolean;
    range: string;
    ammo: string;
    malfunction: string;
    eras: string[];
    price: string;
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
    skillBases: Record<string, number>;
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
    skillBases?: Record<string, number>;
}

interface SkillCatalogPayload {
    version?: number;
    defaultLocale?: string;
    skills?: SkillCatalogEntry[];
    locales?: Record<string, Record<string, string>>;
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
    weaponSlotCount: number;
    attributeRolls: AttributeRollFormulaMap;
}

interface CharacterRuleSettingsInput {
    attributeRatioPercent?: unknown;
    maxCardsPerUser?: unknown;
    weaponSlotCount?: unknown;
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
    armor: number;
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
        weaponSlotCount: 5,
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
        china: {
            family: ["林", "陈", "顾", "沈", "周", "陆", "许", "梁", "赵", "钱", "孙", "李", "王", "吴", "郑", "冯", "蒋", "韩", "杨", "朱", "秦", "何", "吕", "罗", "宋", "谢", "唐", "杜", "程", "苏", "魏", "叶"],
            male: ["雨衡", "明远", "怀瑾", "景行", "子昂", "修文", "亦舟", "远航", "启明", "望舒", "云起", "砚清", "书珩", "临川", "君泽", "予安", "星野", "知白", "立言", "鹤鸣", "清越", "元恺", "文昊", "慕辰", "南烛", "纪行", "守拙", "斯年"],
            female: ["若宁", "清荷", "知遥", "南枝", "书瑶", "映雪", "芷晴", "以沫", "予棠", "云舒", "念真", "采薇", "夕颜", "月白", "景澜", "安歌", "诗涵", "沐晴", "婉仪", "明玥", "洛笙", "令仪", "素问", "清欢", "青黛", "语桐", "初夏", "晚照"],
            neutral: ["安和", "知远", "星河", "沐川", "云深", "青岚", "长风", "一白", "宁川", "砚秋", "归鸿", "明岑", "溪亭", "望川", "逐光", "南星"]
        },
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
            skillBases: {},
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
            skillBases: {},
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
            skillBases: {},
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
            skillBases: {},
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
            skillBases: {},
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
            skillBases: {},
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
            skillBases: {},
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
            skillBases: {},
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
            skillBases: {},
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
            skillBases: {},
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
        skillBases: {
            artCraft: 5,
            history: 5,
            libraryUse: 20,
            naturalWorld: 10,
            occult: 5,
            languageOther: 1,
            languageOwn: 0,
            psychology: 10
        },
        specialties: [],
        passiveEffects: []
    };

    PRESET_OCCUPATIONS = [WRITER_OCCUPATION];

    let SKILL_CATALOG: SkillCatalogEntry[] = [];
    let SKILL_LOCALE_MAP: Record<string, string> = {};
    let BASE_SKILLS: COC7Skill[] = [
        { id: "artCraft", skillKey: "artCraft", name: "技艺", base: 5, value: 5, category: "技术", checked: false, specialty: "写作", specialtyKey: "writing" },
        { id: "history", skillKey: "history", name: "历史", base: 5, value: 5, category: "知识", checked: false },
        { id: "libraryUse", skillKey: "libraryUse", name: "图书馆使用", base: 20, value: 20, category: "探索", checked: false },
        { id: "naturalWorld", skillKey: "naturalWorld", name: "博物学", base: 10, value: 10, category: "知识", checked: false },
        { id: "occult", skillKey: "occult", name: "神秘学", base: 5, value: 5, category: "知识", checked: false },
        { id: "languageOwn", skillKey: "languageOwn", name: "母语", base: 0, value: 0, category: "社交", checked: false, specialty: "汉语", specialtyKey: "chinese" },
        { id: "languageOther", skillKey: "languageOther", name: "外语", base: 1, value: 1, category: "社交", checked: false, specialty: "英语", specialtyKey: "english" },
        { id: "psychology", skillKey: "psychology", name: "心理学", base: 10, value: 10, category: "社交", checked: false },
        { id: "creditRating", skillKey: "creditRating", name: "信用评级", base: 0, value: 0, category: "特殊", checked: false },
        { id: "cthulhuMythos", skillKey: "cthulhuMythos", name: "克苏鲁神话", base: 0, value: 0, category: "特殊", checked: false }
    ];

    let cards: COC7CharacterCard[] = [];
    let activeCardId = "";
    let activeCharacterFilter = "all";
    let assignableUsers: CharacterAssignableUser[] = [];
    let modal: BootstrapModalInstance | null = null;
    let nameGeneratorModal: BootstrapModalInstance | null = null;
    let occupationTemplateModal: BootstrapModalInstance | null = null;
    let skillSpecialtyModal: BootstrapModalInstance | null = null;
    let weaponPickerModal: BootstrapModalInstance | null = null;
    let pendingGeneratedName = "";
    let pendingSkillSpecialtyTarget = "";
    let pendingWeaponPickerTarget = "";
    let activeSkillCategoryFilter = "全部技能";
    let editorSkills: COC7Skill[] = [];
    let WEAPON_CATALOG: WeaponCatalogPayload[] = [];
    let occupationSkillPointsManuallyEdited = false;
    let personalInterestPointsManuallyEdited = false;
    let combatStatsManuallyEdited = false;

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
            weaponSlotCount: clampNumber(input?.weaponSlotCount, 1, 20, DEFAULT_RULE_SETTINGS.weaponSlotCount),
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
            weaponSlotCount: configSection?.weapon_slot_count ?? localSettings?.weaponSlotCount ?? DEFAULT_RULE_SETTINGS.weaponSlotCount,
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
        const givenPool = gender === "male" ? source.male : gender === "female" ? source.female : [...source.male, ...source.female, ...source.neutral];
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
            mov: clampNumber(input.mov, 0, 99, calculateMov(attributes)),
            build: clampNumber(input.build, -2, 99, damage.build),
            damageBonus: input.damageBonus || damage.damageBonus,
            armor: clampNumber(input.armor, 0, 99, 0),
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
            const skillKey = resolveSkillKey(skill);
            const base = calculateSkillBase(skill, attributes, occupation);
            const occupationPoints = clampNumber(skill.occupationPoints, 0, 99, 0);
            const interestPoints = clampNumber(skill.interestPoints, 0, 99, 0);
            const growthPoints = clampNumber(skill.growthPoints, 0, 99, 0);
            const value = clampNumber(skill.value, 0, 99, base + occupationPoints + interestPoints + growthPoints);
            const occupationSpecialtyKey = getOccupationSpecialtyKey(occupation, skillKey);
            const occupationSkill = occupation?.occupationSkills.includes(skillKey) || Boolean(skill.occupation);
            const specialtyKey = skill.specialtyKey || occupationSpecialtyKey || "";
            const specialty = skill.specialty || (specialtyKey ? localizeSkillSpecialty(skillKey, specialtyKey) : "");
            return {
                id: skill.id || slugify(skill.name),
                skillKey,
                name: String(skill.name || "未命名技能").slice(0, 40),
                base,
                value,
                category: skill.category || "知识",
                checked: Boolean(skill.checked || occupationSkill),
                occupation: occupationSkill,
                specialty,
                specialtyKey,
                occupationPoints,
                interestPoints,
                growthPoints,
                rank: skill.rank || rankFromValue(value)
            };
        });
    }

    function mergeSkillCatalog(skills: COC7Skill[]): COC7Skill[] {
        const byId = new Map(skills.map((skill) => [skill.id, skill]));
        const byKey = skills.reduce((index, skill) => {
            const skillKey = resolveSkillKey(skill);
            const list = index.get(skillKey) || [];
            list.push(skill);
            index.set(skillKey, list);
            return index;
        }, new Map<string, COC7Skill[]>());
        return BASE_SKILLS.map((base) => {
            const skillKey = resolveSkillKey(base);
            const exact = byId.get(base.id);
            const fallback = byKey.get(skillKey)?.shift();
            return { ...base, ...(exact || fallback || {}) };
        });
    }

    function calculateSkillBase(skill: COC7Skill, attributes?: COC7Attributes, occupation?: COC7Occupation): number {
        const skillKey = resolveSkillKey(skill);
        if (occupation?.skillBases && Object.prototype.hasOwnProperty.call(occupation.skillBases, skillKey)) {
            return clampNumber(occupation.skillBases[skillKey], 0, 99, clampNumber(skill.base, 0, 99, 0));
        }
        if (skill.id === "dodge" && attributes) return Math.floor(attributes.DEX / 2);
        return clampNumber(skill.base, 0, 99, 0);
    }

    function resolveSkillKey(skill: Pick<COC7Skill, "id" | "skillKey">): string {
        return skill.skillKey || skill.id.split("__")[0] || skill.id;
    }

    function getOccupationSpecialtyKey(occupation: COC7Occupation | undefined, skillKey: string): string {
        const match = (occupation?.occupationSkillEntries || []).find((entry) => entry.skillKey === skillKey && entry.specialtyKey);
        return match?.specialtyKey || "";
    }

    function normalizeWeapons(weapons?: COC7Weapon[]): COC7Weapon[] {
        return (weapons || []).map((weapon) => ({
            name: weapon.name || "未命名武器",
            skill: weapon.skill || "格斗(斗殴)",
            skillKey: weapon.skillKey || "",
            specialtyKey: weapon.specialtyKey || "",
            damage: weapon.damage || "1D3",
            range: weapon.range || "接触",
            impale: typeof weapon.impale === "boolean" ? weapon.impale : null,
            attacks: String(weapon.attacks || "1"),
            ammo: String(weapon.ammo || "N/A"),
            malfunction: String(weapon.malfunction || "N/A")
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
            skillBases: normalizeSkillBases(payload.skillBases),
            specialties: [],
            passiveEffects: []
        };
    }

    function normalizeSkillBases(skillBases?: Record<string, number>): Record<string, number> {
        return Object.entries(skillBases || {}).reduce((bases, [skillKey, value]) => {
            const parsed = Number(value);
            if (Number.isFinite(parsed)) bases[skillKey] = clampNumber(parsed, 0, 99, 0);
            return bases;
        }, {} as Record<string, number>);
    }

    async function loadSkillCatalog(): Promise<void> {
        try {
            const response = await TrpgApi.get<ApiResponse<SkillCatalogPayload>>("/api/character-catalogs/skills");
            if (!response.success || !response.data) return;
            const payload = response.data;
            SKILL_CATALOG = normalizeSkillCatalog(payload.skills || []);
            SKILL_LOCALE_MAP = payload.locales?.[payload.defaultLocale || "zh-CN"] || payload.locales?.["zh-CN"] || {};
            BASE_SKILLS = flattenSkillCatalog(SKILL_CATALOG, SKILL_LOCALE_MAP);
        } catch (error) {
            console.warn("加载技能目录失败:", error);
        }
    }

    async function loadWeaponCatalog(): Promise<void> {
        try {
            const response = await TrpgApi.get<ApiResponse<WeaponCatalogPayload[]>>("/api/character-catalogs/weapons");
            WEAPON_CATALOG = response.success && Array.isArray(response.data)
                ? response.data.map(normalizeWeaponCatalog).filter((weapon) => Boolean(weapon.id))
                : [];
        } catch (error) {
            WEAPON_CATALOG = [];
            console.warn("加载武器目录失败:", error);
        }
    }

    function normalizeWeaponCatalog(payload: WeaponCatalogPayload): WeaponCatalogPayload {
        return {
            id: String(payload.id || "").trim(),
            name: String(payload.name || "未命名武器").slice(0, 60),
            skill: {
                skillKey: String(payload.skill?.skillKey || "").trim(),
                specialtyKey: String(payload.skill?.specialtyKey || "").trim(),
                label: String(payload.skill?.label || "").trim()
            },
            damage: String(payload.damage || "1D3"),
            attacks: String(payload.attacks || "1"),
            impale: Boolean(payload.impale),
            range: String(payload.range || "接触"),
            ammo: String(payload.ammo || "N/A"),
            malfunction: String(payload.malfunction || "N/A"),
            eras: Array.isArray(payload.eras) ? payload.eras.map((era) => String(era)) : [],
            price: String(payload.price || "N/A")
        };
    }

    function normalizeSkillCatalog(entries: SkillCatalogEntry[]): SkillCatalogEntry[] {
        return entries.map((entry) => ({
            key: String(entry.key || "").trim(),
            labelKey: String(entry.labelKey || "").trim(),
            category: normalizeSkillCategory(entry.category),
            base: clampNumber(entry.base, 0, 99, 0),
            repeatable: clampNumber(entry.repeatable, 1, 9, 1),
            specialties: Array.isArray(entry.specialties)
                ? entry.specialties.map((specialty) => ({
                    key: String(specialty.key || "").trim(),
                    labelKey: String(specialty.labelKey || "").trim()
                })).filter((specialty) => Boolean(specialty.key))
                : [],
            eraLimited: Boolean(entry.eraLimited)
        })).filter((entry) => Boolean(entry.key));
    }

    function normalizeSkillCategory(value: SkillCategory | string): SkillCategory {
        const allowed: SkillCategory[] = ["特殊", "探索", "社交", "战斗", "医疗", "运动", "知识", "技术", "操纵", "其他"];
        return allowed.includes(value as SkillCategory) ? value as SkillCategory : "其他";
    }

    function flattenSkillCatalog(entries: SkillCatalogEntry[], locales: Record<string, string>): COC7Skill[] {
        const flattened: COC7Skill[] = [];
        entries.forEach((entry) => {
            const label = locales[entry.labelKey] || entry.labelKey.split(".").pop() || entry.key;
            const repeatCount = Math.max(1, entry.repeatable || 1);
            for (let index = 0; index < repeatCount; index += 1) {
                const suffix = repeatCount > 1 ? index + 1 : 0;
                flattened.push({
                    id: repeatCount > 1 ? `${entry.key}__${suffix}` : entry.key,
                    skillKey: entry.key,
                    name: label,
                    base: entry.base,
                    value: entry.base,
                    category: entry.category,
                    checked: false,
                    specialty: "",
                    specialtyKey: ""
                });
            }
        });
        return flattened.length ? flattened : BASE_SKILLS;
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
        return `${skillName}(${localizeSkillSpecialty(skillKey, specialtyKey)})`;
    }

    function localizeSkillSpecialty(skillKey: string, specialtyKey: string): string {
        return SKILL_LOCALE_MAP[`skillSpecialties.${skillKey}.${specialtyKey}`] || SKILL_SPECIALTY_LABELS[`${skillKey}.${specialtyKey}`] || specialtyKey;
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
        const skillSpecialtyModalElement = byId("skillSpecialtyModal");
        skillSpecialtyModal = skillSpecialtyModalElement && typeof bootstrap !== "undefined" ? new bootstrap.Modal(skillSpecialtyModalElement) : null;
        const weaponPickerModalElement = byId("characterWeaponPickerModal");
        weaponPickerModal = weaponPickerModalElement && typeof bootstrap !== "undefined" ? new bootstrap.Modal(weaponPickerModalElement) : null;
        hydrateOccupationSelect();
        bindEvents();
        void Promise.all([loadSkillCatalog(), loadOccupationCatalogs(), loadWeaponCatalog()]).then(() => {
            hydrateOccupationSelect();
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
            editorSkills = readChecklistSkills();
            hydrateSkillChecklist(editorSkills);
            refreshEditorRuleSummary();
        });
        byId("characterCreditRating")?.addEventListener("input", refreshEditorRuleSummary);
        byId("characterOccupationSkillPoints")?.addEventListener("input", () => {
            occupationSkillPointsManuallyEdited = true;
            refreshSkillTableCalculations();
        });
        byId("characterPersonalInterestPoints")?.addEventListener("input", () => {
            personalInterestPointsManuallyEdited = true;
            refreshSkillTableCalculations();
        });
        ["characterDamageBonus", "characterBuild", "characterArmor", "characterMov"].forEach((fieldId) => {
            byId(fieldId)?.addEventListener("input", () => {
                combatStatsManuallyEdited = true;
            });
        });
        byId("generateOccupationSkillPoints")?.addEventListener("click", () => {
            occupationSkillPointsManuallyEdited = false;
            setGeneratedOccupationSkillPoints();
            refreshSkillTableCalculations();
        });
        byId("generatePersonalInterestPoints")?.addEventListener("click", () => {
            personalInterestPointsManuallyEdited = false;
            setGeneratedPersonalInterestPoints();
            refreshSkillTableCalculations();
        });
        ["characterOccupationSkillLimit", "characterOtherSkillLimit"].forEach((fieldId) => {
            byId(fieldId)?.addEventListener("input", refreshSkillTableCalculations);
        });
        byId("characterSkillCategoryFilters")?.addEventListener("click", handleSkillCategoryFilterClick);
        byId("characterSkillTableBody")?.addEventListener("input", handleSkillTableInput);
        byId("characterSkillTableBody")?.addEventListener("change", handleSkillTableInput);
        byId("characterSkillTableBody")?.addEventListener("click", handleSkillTableClick);
        byId("skillSpecialtyOptions")?.addEventListener("click", handleSkillSpecialtyOptionClick);
        byId("characterWeaponTableBody")?.addEventListener("input", handleWeaponTableInput);
        byId("characterWeaponTableBody")?.addEventListener("change", handleWeaponTableInput);
        byId("characterWeaponTableBody")?.addEventListener("click", handleWeaponTableClick);
        byId("characterWeaponCatalogList")?.addEventListener("click", handleWeaponCatalogClick);
        byId("createCustomWeapon")?.addEventListener("click", createCustomWeaponRow);
        byId("removeCurrentWeapon")?.addEventListener("click", removeCurrentWeaponRow);
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
        renderSkillTable(skills);
    }

    function renderSkillTable(skills: COC7Skill[] = BASE_SKILLS): void {
        const body = byId("characterSkillTableBody");
        if (!body) return;
        const occupation = resolveOccupationFromInput(getInputValue("characterOccupation"));
        const normalized = normalizeSkills(skills, readAttributes(), occupation);
        const availableCategories = new Set(["全部技能", "特殊", "探索", "社交", "战斗", "医疗", "运动", "知识", "操纵", "其他"]);
        body.innerHTML = normalized.map((skill) => {
            const skillKey = resolveSkillKey(skill);
            const rowId = escapeHtml(skill.id);
            const category = escapeHtml(skill.category || "其他");
            const allowed = availableCategories.has(skill.category || "其他");
            const successLimit = skill.occupation ? getSkillLimit("occupation") : getSkillLimit("other");
            const occupationPoints = skill.occupationPoints || 0;
            const interestPoints = skill.interestPoints || 0;
            const growthPoints = skill.growthPoints || 0;
            const success = clampNumber(skill.base + occupationPoints + interestPoints + growthPoints, 0, successLimit, skill.base);
            const occupationDisabled = skill.occupation ? "" : "disabled";
            const typeButton = buildSkillSpecialtyButton(skill);
            const customNameInput = buildCustomSkillNameInput(skill, rowId);
            const displayName = isCustomSkill(skillKey) ? (skill.name || skillNameById(skillKey)) : skill.name;
            return `
                <tr data-skill-row-id="${rowId}" data-skill-key="${escapeHtml(skillKey)}" data-skill-category="${category}" data-skill-occupation="${skill.occupation ? "1" : "0"}" data-specialty-key="${escapeHtml(skill.specialtyKey || "")}" data-specialty-label="${escapeHtml(skill.specialty || "")}" ${allowed ? "" : 'hidden="hidden"'}>
                    <td><input type="checkbox" class="form-check-input" data-skill-occupation-checkbox="${rowId}" ${skill.occupation ? "checked" : ""}></td>
                    <td>
                        <div class="character-skill-name-cell">
                            <span data-skill-display-name="${rowId}">${escapeHtml(displayName)}</span>
                            ${customNameInput}
                            ${typeButton}
                        </div>
                    </td>
                    <td><span class="character-skill-value-cell" data-skill-base="${rowId}">${skill.base}</span></td>
                    <td><input type="number" class="form-control form-control-sm character-skill-points-input" min="0" max="${getSkillLimit("occupation")}" value="${occupationPoints}" data-skill-occupation-points="${rowId}" ${occupationDisabled}></td>
                    <td><input type="number" class="form-control form-control-sm character-skill-points-input" min="0" max="${getSkillLimit("other")}" value="${interestPoints}" data-skill-interest-points="${rowId}"></td>
                    <td><input type="number" class="form-control form-control-sm character-skill-points-input" min="0" max="${getSkillLimit("other")}" value="${growthPoints}" data-skill-growth-points="${rowId}"></td>
                    <td><span class="character-skill-value-cell" data-skill-success="${rowId}">${success}</span></td>
                    <td><span class="character-skill-value-cell" data-skill-hard="${rowId}">${Math.floor(success / 2)}</span></td>
                    <td><span class="character-skill-value-cell" data-skill-extreme="${rowId}">${Math.floor(success / 5)}</span></td>
                </tr>
            `;
        }).join("");
        refreshSkillTableVisibility();
        refreshSkillPointSummary();
    }

    function buildCustomSkillNameInput(skill: COC7Skill, rowId: string): string {
        const skillKey = resolveSkillKey(skill);
        if (!isCustomSkill(skillKey)) return "";
        const defaultName = skillNameById(skillKey);
        const customName = skill.name && skill.name !== defaultName ? skill.name : "";
        return `<input type="text" class="form-control form-control-sm character-custom-skill-name-input" maxlength="40" value="${escapeHtml(customName)}" placeholder="输入自定义技能" data-custom-skill-name="${rowId}">`;
    }

    function isCustomSkill(skillKey: string): boolean {
        return skillKey === "custom";
    }

    function buildSkillSpecialtyButton(skill: COC7Skill): string {
        const skillKey = resolveSkillKey(skill);
        const catalog = SKILL_CATALOG.find((entry) => entry.key === skillKey);
        if (!catalog?.specialties?.length) return "";
        const label = skill.specialty || "选择类型";
        return `<button type="button" class="character-skill-type-button" data-skill-specialty-trigger="${escapeHtml(skill.id)}">${escapeHtml(label)}</button>`;
    }

    function getSkillLimit(type: "occupation" | "other"): number {
        return clampNumber(getInputValue(type === "occupation" ? "characterOccupationSkillLimit" : "characterOtherSkillLimit"), 0, 99, type === "occupation" ? 75 : 50);
    }

    function handleSkillCategoryFilterClick(event: Event): void {
        const button = (event.target as HTMLElement).closest<HTMLButtonElement>("[data-skill-category]");
        if (!button) return;
        activeSkillCategoryFilter = button.dataset.skillCategory || "全部技能";
        document.querySelectorAll<HTMLElement>("#characterSkillCategoryFilters [data-skill-category]").forEach((item) => {
            item.classList.toggle("is-active", item === button);
        });
        refreshSkillTableVisibility();
    }

    function handleSkillTableInput(event: Event): void {
        const row = (event.target as HTMLElement).closest<HTMLTableRowElement>("tr[data-skill-row-id]");
        if (!row) return;
        const target = event.target as HTMLElement;
        if (target.closest("[data-custom-skill-name]")) {
            syncCustomSkillDisplayName(row);
        }
        refreshSkillTableCalculations();
    }

    function handleSkillTableClick(event: Event): void {
        const button = (event.target as HTMLElement).closest<HTMLButtonElement>("[data-skill-specialty-trigger]");
        if (!button) return;
        openSkillSpecialtyPicker(button.dataset.skillSpecialtyTrigger || "");
    }

    function openSkillSpecialtyPicker(rowId: string): void {
        const row = findSkillRow(rowId);
        const options = byId("skillSpecialtyOptions");
        if (!row || !options) return;
        const skillKey = row.dataset.skillKey || rowId.split("__")[0] || rowId;
        const catalog = SKILL_CATALOG.find((entry) => entry.key === skillKey);
        if (!catalog?.specialties?.length) return;
        pendingSkillSpecialtyTarget = rowId;
        setInputValue("skillSpecialtyTargetRow", rowId);
        const used = selectedSpecialtyKeys(skillKey, rowId);
        options.innerHTML = catalog.specialties.map((specialty) => {
            const disabled = used.has(specialty.key);
            return `
                <button type="button" class="character-specialty-option" data-specialty-key="${escapeHtml(specialty.key)}" ${disabled ? "disabled" : ""}>
                    ${escapeHtml(localizeSkillSpecialty(skillKey, specialty.key))}
                </button>
            `;
        }).join("");
        skillSpecialtyModal?.show();
    }

    function handleSkillSpecialtyOptionClick(event: Event): void {
        const button = (event.target as HTMLElement).closest<HTMLButtonElement>("[data-specialty-key]");
        if (!button || button.disabled) return;
        const rowId = pendingSkillSpecialtyTarget || getInputValue("skillSpecialtyTargetRow");
        const row = findSkillRow(rowId);
        if (!row) return;
        const skillKey = row.dataset.skillKey || rowId.split("__")[0] || rowId;
        const specialtyKey = button.dataset.specialtyKey || "";
        if (selectedSpecialtyKeys(skillKey, rowId).has(specialtyKey)) {
            notify("同一技能的类型不能重复选择。", "error");
            return;
        }
        const label = localizeSkillSpecialty(skillKey, specialtyKey);
        row.dataset.specialtyKey = specialtyKey;
        row.dataset.specialtyLabel = label;
        const trigger = row.querySelector<HTMLButtonElement>("[data-skill-specialty-trigger]");
        if (trigger) trigger.textContent = label;
        skillSpecialtyModal?.hide();
    }

    function findSkillRow(rowId: string): HTMLTableRowElement | null {
        const body = byId("characterSkillTableBody");
        if (!body || !rowId) return null;
        return body.querySelector<HTMLTableRowElement>(`tr[data-skill-row-id="${CSS.escape(rowId)}"]`);
    }

    function selectedSpecialtyKeys(skillKey: string, excludedRowId = ""): Set<string> {
        const body = byId("characterSkillTableBody");
        const selected = new Set<string>();
        if (!body) return selected;
        body.querySelectorAll<HTMLTableRowElement>(`tr[data-skill-key="${CSS.escape(skillKey)}"]`).forEach((row) => {
            if (row.dataset.skillRowId === excludedRowId) return;
            if (row.dataset.specialtyKey) selected.add(row.dataset.specialtyKey);
        });
        return selected;
    }

    function hydrateWeaponTable(weapons: COC7Weapon[] = []): void {
        renderWeaponTable(weapons);
    }

    function renderWeaponTable(weapons: COC7Weapon[] = []): void {
        const body = byId("characterWeaponTableBody");
        if (!body) return;
        const normalized = ensureWeaponSlots(normalizeWeapons(weapons));
        body.innerHTML = normalized.map((weapon, index) => renderWeaponRow(weapon, index)).join("");
        refreshWeaponSuccessRates();
    }

    function getWeaponSlotCount(): number {
        return loadRuleSettings().weaponSlotCount;
    }

    function ensureWeaponSlots(weapons: COC7Weapon[]): COC7Weapon[] {
        const slots = Math.max(getWeaponSlotCount(), weapons.length);
        return Array.from({ length: slots }, (_, index) => weapons[index] || createEmptyWeapon());
    }

    function renderWeaponRow(weapon: COC7Weapon, index: number): string {
        const rowId = `weapon-${index}`;
        const skillOptions = weaponSkillOptions(weapon);
        const success = findSkillSuccessByWeaponSkill(weapon);
        return `
            <tr data-weapon-row-id="${rowId}">
                <td>
                    <button type="button" class="character-weapon-name-button" data-weapon-picker-trigger="${rowId}">
                        ${escapeHtml(weapon.name || "选择武器")}
                    </button>
                    <input type="hidden" data-weapon-name="${rowId}" value="${escapeHtml(weapon.name)}">
                </td>
                <td>
                    <select class="form-select form-select-sm character-weapon-skill-select" data-weapon-skill="${rowId}">
                        ${skillOptions}
                    </select>
                </td>
                <td><span class="character-skill-value-cell" data-weapon-success="${rowId}">${success}</span></td>
                <td><input type="text" class="form-control form-control-sm character-weapon-input" data-weapon-damage="${rowId}" value="${escapeHtml(weapon.damage)}"></td>
                <td><input type="text" class="form-control form-control-sm character-weapon-input" data-weapon-range="${rowId}" value="${escapeHtml(weapon.range)}"></td>
                <td>
                    <select class="form-select form-select-sm character-weapon-impale-select" data-weapon-impale="${rowId}">
                        <option value="" ${weapon.impale === null ? "selected" : ""}>-</option>
                        <option value="false" ${weapon.impale === false ? "selected" : ""}>否</option>
                        <option value="true" ${weapon.impale ? "selected" : ""}>是</option>
                    </select>
                </td>
                <td><input type="text" class="form-control form-control-sm character-weapon-input character-weapon-input-narrow" data-weapon-attacks="${rowId}" value="${escapeHtml(weapon.attacks)}"></td>
                <td><input type="text" class="form-control form-control-sm character-weapon-input character-weapon-input-narrow" data-weapon-ammo="${rowId}" value="${escapeHtml(weapon.ammo)}"></td>
                <td><input type="text" class="form-control form-control-sm character-weapon-input character-weapon-input-narrow" data-weapon-malfunction="${rowId}" value="${escapeHtml(weapon.malfunction)}"></td>
            </tr>
        `;
    }

    function createEmptyWeapon(): COC7Weapon {
        return {
            name: "选择武器",
            skill: "-",
            skillKey: "",
            specialtyKey: "",
            damage: "",
            range: "",
            impale: null,
            attacks: "",
            ammo: "N/A",
            malfunction: "N/A"
        };
    }

    function weaponSkillOptions(selectedWeapon: COC7Weapon): string {
        const options = getWeaponSkillChoices();
        const selectedValue = weaponSkillValue(selectedWeapon);
        return `<option value="">-</option>` + options.map((option) => {
            const selected = option.value === selectedValue || (!selectedValue && option.label === selectedWeapon.skill);
            return `<option value="${escapeHtml(option.value)}" ${selected ? "selected" : ""}>${escapeHtml(option.label)}</option>`;
        }).join("");
    }

    function getWeaponSkillChoices(): Array<{ value: string; label: string; skillKey: string; specialtyKey: string }> {
        const choices: Array<{ value: string; label: string; skillKey: string; specialtyKey: string }> = [];
        SKILL_CATALOG.forEach((catalog) => {
            if (!isWeaponSkillKey(catalog.key)) return;
            if (catalog.specialties.length) {
                catalog.specialties.forEach((specialty) => {
                    choices.push({
                        value: `${catalog.key}|${specialty.key}`,
                        label: formatWeaponSkillChoiceLabel(catalog.key, specialty.key),
                        skillKey: catalog.key,
                        specialtyKey: specialty.key
                    });
                });
                return;
            }
            choices.push({
                value: `${catalog.key}|`,
                label: skillNameById(catalog.key),
                skillKey: catalog.key,
                specialtyKey: ""
            });
        });
        const fixed = [
            { value: "throw|", label: skillNameById("throw"), skillKey: "throw", specialtyKey: "" },
            { value: "demolitions|", label: skillNameById("demolitions"), skillKey: "demolitions", specialtyKey: "" },
            { value: "artillery|", label: skillNameById("artillery"), skillKey: "artillery", specialtyKey: "" }
        ];
        return dedupeWeaponSkillChoices([...choices, ...fixed]);
    }

    function isWeaponSkillKey(skillKey: string): boolean {
        return ["fighting", "firearms", "throw", "demolitions", "artillery"].includes(skillKey);
    }

    function dedupeWeaponSkillChoices(choices: Array<{ value: string; label: string; skillKey: string; specialtyKey: string }>): Array<{ value: string; label: string; skillKey: string; specialtyKey: string }> {
        const seen = new Set<string>();
        return choices.filter((choice) => {
            if (seen.has(choice.value)) return false;
            seen.add(choice.value);
            return true;
        });
    }

    function formatWeaponSkillLabel(skill: COC7Skill): string {
        return formatWeaponSkillChoiceLabel(resolveSkillKey(skill), skill.specialtyKey || "");
    }

    function formatWeaponSkillChoiceLabel(skillKey: string, specialtyKey: string): string {
        const baseName = skillNameById(skillKey);
        const specialtyName = specialtyKey ? localizeSkillSpecialty(skillKey, specialtyKey) : "";
        return specialtyName ? `${baseName}(${specialtyName})` : baseName;
    }

    function weaponSkillValue(weapon: Pick<COC7Weapon, "skillKey" | "specialtyKey" | "skill">): string {
        if (weapon.skillKey) return `${weapon.skillKey}|${weapon.specialtyKey || ""}`;
        const matched = getWeaponSkillChoices().find((choice) => choice.label === weapon.skill);
        return matched?.value || "";
    }

    function handleWeaponTableInput(): void {
        refreshWeaponSuccessRates();
    }

    function handleWeaponTableClick(event: Event): void {
        const button = (event.target as HTMLElement).closest<HTMLButtonElement>("[data-weapon-picker-trigger]");
        if (!button) return;
        openWeaponPicker(button.dataset.weaponPickerTrigger || "");
    }

    function openWeaponPicker(rowId: string): void {
        pendingWeaponPickerTarget = rowId;
        setInputValue("weaponPickerTargetRow", rowId);
        renderWeaponCatalog();
        weaponPickerModal?.show();
    }

    function renderWeaponCatalog(): void {
        const container = byId("characterWeaponCatalogList");
        if (!container) return;
        container.innerHTML = WEAPON_CATALOG.map((weapon) => `
            <article class="character-weapon-catalog-card">
                <div>
                    <strong>${escapeHtml(weapon.name)}</strong>
                    <span>${escapeHtml(weapon.skill.label || formatWeaponCatalogSkillLabel(weapon))}</span>
                </div>
                <small>${escapeHtml(weapon.damage)} · ${escapeHtml(weapon.range)} · ${weapon.impale ? "贯穿" : "非贯穿"}</small>
                <small>次数 ${escapeHtml(weapon.attacks)} · 装弹 ${escapeHtml(weapon.ammo)} · 故障 ${escapeHtml(weapon.malfunction)}</small>
                <small>年代 ${escapeHtml(weapon.eras.join("、") || "不限")} · 价格 ${escapeHtml(weapon.price)}</small>
                <button type="button" class="btn btn-sm btn-primary" data-equip-weapon="${escapeHtml(weapon.id)}">装备</button>
            </article>
        `).join("") || `<div class="background-note">暂无预设武器</div>`;
    }

    function formatWeaponCatalogSkillLabel(weapon: WeaponCatalogPayload): string {
        const baseName = skillNameById(weapon.skill.skillKey || "");
        const specialty = weapon.skill.skillKey && weapon.skill.specialtyKey
            ? localizeSkillSpecialty(weapon.skill.skillKey, weapon.skill.specialtyKey)
            : "";
        return specialty ? `${baseName}(${specialty})` : baseName;
    }

    function handleWeaponCatalogClick(event: Event): void {
        const button = (event.target as HTMLElement).closest<HTMLButtonElement>("[data-equip-weapon]");
        if (!button) return;
        const preset = WEAPON_CATALOG.find((weapon) => weapon.id === button.dataset.equipWeapon);
        if (!preset) return;
        applyWeaponToRow(presetWeaponToCharacterWeapon(preset));
        weaponPickerModal?.hide();
    }

    function presetWeaponToCharacterWeapon(preset: WeaponCatalogPayload): COC7Weapon {
        return {
            name: preset.name,
            skill: preset.skill.label || formatWeaponCatalogSkillLabel(preset),
            skillKey: preset.skill.skillKey || "",
            specialtyKey: preset.skill.specialtyKey || "",
            damage: preset.damage,
            range: preset.range,
            impale: preset.impale,
            attacks: preset.attacks,
            ammo: preset.ammo,
            malfunction: preset.malfunction
        };
    }

    function applyWeaponToRow(weapon: COC7Weapon): void {
        const row = findWeaponRow(pendingWeaponPickerTarget || getInputValue("weaponPickerTargetRow"));
        if (!row) return;
        const rows = readWeaponRows();
        const rowIndex = Array.from(row.parentElement?.children || []).indexOf(row);
        rows[rowIndex] = weapon;
        renderWeaponTable(rows);
    }

    function createCustomWeaponRow(): void {
        applyWeaponToRow(createEmptyWeapon());
        weaponPickerModal?.hide();
    }

    function removeCurrentWeaponRow(): void {
        const row = findWeaponRow(pendingWeaponPickerTarget || getInputValue("weaponPickerTargetRow"));
        if (!row) return;
        const rows = readWeaponRows();
        const rowIndex = Array.from(row.parentElement?.children || []).indexOf(row);
        rows[rowIndex] = createEmptyWeapon();
        renderWeaponTable(rows);
        weaponPickerModal?.hide();
    }

    function findWeaponRow(rowId: string): HTMLTableRowElement | null {
        const body = byId("characterWeaponTableBody");
        if (!body || !rowId) return null;
        return body.querySelector<HTMLTableRowElement>(`tr[data-weapon-row-id="${CSS.escape(rowId)}"]`);
    }

    function readWeaponRows(): COC7Weapon[] {
        const body = byId("characterWeaponTableBody");
        if (!body) return [];
        return Array.from(body.querySelectorAll<HTMLTableRowElement>("tr[data-weapon-row-id]")).map((row) => {
            const rowId = row.dataset.weaponRowId || "";
            const select = row.querySelector<HTMLSelectElement>("[data-weapon-skill]");
            const selected = parseWeaponSkillSelectValue(select?.value || "");
            return {
                name: String(row.querySelector<HTMLInputElement>("[data-weapon-name]")?.value || "未命名武器").trim() || "未命名武器",
                skill: select?.selectedOptions[0]?.textContent?.trim() || "-",
                skillKey: selected.skillKey,
                specialtyKey: selected.specialtyKey,
                damage: readWeaponField(row, "[data-weapon-damage]", "1D3"),
                range: readWeaponField(row, "[data-weapon-range]", "接触"),
                impale: readWeaponImpale(row),
                attacks: readWeaponField(row, "[data-weapon-attacks]", ""),
                ammo: readWeaponField(row, "[data-weapon-ammo]", "N/A"),
                malfunction: readWeaponField(row, "[data-weapon-malfunction]", "N/A")
            };
        });
    }

    function readWeaponImpale(row: HTMLTableRowElement): boolean | null {
        const value = row.querySelector<HTMLSelectElement>("[data-weapon-impale]")?.value;
        if (value === "true") return true;
        if (value === "false") return false;
        return null;
    }

    function readWeaponField(row: HTMLTableRowElement, selector: string, fallback: string): string {
        const value = row.querySelector<HTMLInputElement>(selector)?.value.trim();
        return value || fallback;
    }

    function parseWeaponSkillSelectValue(value: string): { skillKey: string; specialtyKey: string } {
        const [skillKey, specialtyKey = ""] = value.split("|");
        return { skillKey: skillKey || "", specialtyKey };
    }

    function refreshWeaponSuccessRates(): void {
        const body = byId("characterWeaponTableBody");
        if (!body) return;
        body.querySelectorAll<HTMLTableRowElement>("tr[data-weapon-row-id]").forEach((row) => {
            const rowId = row.dataset.weaponRowId || "";
            const select = row.querySelector<HTMLSelectElement>("[data-weapon-skill]");
            const selected = parseWeaponSkillSelectValue(select?.value || "");
            const success = findSkillSuccessByWeaponSkill({
                skill: select?.selectedOptions[0]?.textContent?.trim() || "",
                skillKey: selected.skillKey,
                specialtyKey: selected.specialtyKey
            });
            const output = row.querySelector<HTMLElement>(`[data-weapon-success="${CSS.escape(rowId)}"]`);
            if (output) output.textContent = String(success);
        });
    }

    function findSkillSuccessByWeaponSkill(weapon: Pick<COC7Weapon, "skill" | "skillKey" | "specialtyKey">): number | "" {
        if (!weapon.skillKey) return "";
        const skills = readChecklistSkills();
        const exact = skills.find((skill) => resolveSkillKey(skill) === weapon.skillKey && (skill.specialtyKey || "") === (weapon.specialtyKey || ""));
        if (exact) return exact.value;
        const byLabel = skills.find((skill) => formatWeaponSkillLabel(skill) === weapon.skill || skill.name === weapon.skill);
        if (byLabel) return byLabel.value;
        return weapon.skillKey && weapon.specialtyKey ? weaponSkillBaseFallback(weapon.skillKey) : 0;
    }

    function weaponSkillBaseFallback(skillKey: string): number {
        if (skillKey === "fighting") return 1;
        const catalog = SKILL_CATALOG.find((entry) => entry.key === skillKey);
        return catalog ? catalog.base : 0;
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
        setInputValue("characterDamageBonus", target.damageBonus);
        setInputValue("characterBuild", target.build);
        setInputValue("characterArmor", target.armor);
        setInputValue("characterMov", target.mov);
        editorSkills = target.skills;
        occupationSkillPointsManuallyEdited = target.occupationSkillPoints !== calculateOccupationSkillPoints(target.attributes, target.occupationId);
        personalInterestPointsManuallyEdited = target.personalInterestPoints !== calculatePersonalInterestPoints(target.attributes);
        combatStatsManuallyEdited = false;
        setEditorStatus(target.status);
        updateUnbindButton(boundPlayerId);
        updateAvatarPreview(target.avatar);
        hydrateSkillChecklist(editorSkills);
        hydrateWeaponTable(target.weapons);
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
        editorSkills = readChecklistSkills();
        hydrateSkillChecklist(editorSkills);
        refreshEditorRuleSummary();
        occupationTemplateModal?.hide();
    }

    function hydrateRuleSettingsPanel(): void {
        const settings = loadRuleSettings();
        setInputValue("attributeRatioPercent", settings.attributeRatioPercent);
        setInputValue("maxCardsPerUser", settings.maxCardsPerUser);
        setInputValue("weaponSlotCount", settings.weaponSlotCount);
        ATTRIBUTE_KEYS.forEach((key) => setInputValue(`attributeRoll${key}`, settings.attributeRolls[key]));
        setText("characterRuleSettingsMessage", "");
    }

    async function saveRuleSettingsFromPanel(): Promise<void> {
        const nextSettings = normalizeRuleSettings({
            attributeRatioPercent: Number(getInputValue("attributeRatioPercent")),
            maxCardsPerUser: Number(getInputValue("maxCardsPerUser")),
            weaponSlotCount: Number(getInputValue("weaponSlotCount")),
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
            weapon_slot_count: nextSettings.weaponSlotCount,
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
        const base = BASE_SKILLS.find((skill) => skill.id === skillId || (skill.skillKey || skill.id) === skillId);
        if (base) return base.name;
        const catalog = SKILL_CATALOG.find((entry) => entry.key === skillId);
        return catalog ? SKILL_LOCALE_MAP[catalog.labelKey] || skillId : skillId;
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

    function syncEditorCombatStats(attributes: COC7Attributes = readAttributes(), force = false): void {
        if (combatStatsManuallyEdited && !force) return;
        const damage = calculateBuildAndDamageBonus(attributes);
        setInputValue("characterDamageBonus", damage.damageBonus);
        setInputValue("characterBuild", damage.build);
        setInputValue("characterMov", calculateMov(attributes));
        if (!getInputValue("characterArmor")) setInputValue("characterArmor", 0);
    }

    function updateAttributeRollHints(): void {
        const settings = loadRuleSettings();
        document.querySelectorAll<HTMLElement>("[data-attribute-roll]").forEach((element) => {
            const key = element.dataset.attributeRoll as COC7CoreAttributeKey | undefined;
            if (key && ATTRIBUTE_KEYS.includes(key)) element.textContent = settings.attributeRolls[key];
        });
    }

    function readChecklistSkills(): COC7Skill[] {
        const body = byId("characterSkillTableBody");
        if (!body) return editorSkills.length ? editorSkills : normalizeSkills(undefined, readAttributes(), resolveOccupationFromInput(getInputValue("characterOccupation")));
        const rows = Array.from(body.querySelectorAll<HTMLTableRowElement>("tr[data-skill-row-id]"));
        if (!rows.length) return normalizeSkills(editorSkills.length ? editorSkills : undefined, readAttributes(), resolveOccupationFromInput(getInputValue("characterOccupation")));
        return rows.map((row) => {
            const rowId = row.dataset.skillRowId || "";
            const skillKey = row.dataset.skillKey || rowId.split("__")[0] || rowId;
            const baseSkill = BASE_SKILLS.find((skill) => skill.id === rowId) || BASE_SKILLS.find((skill) => (skill.skillKey || skill.id) === skillKey);
            const occupation = row.querySelector<HTMLInputElement>("[data-skill-occupation-checkbox]")?.checked || false;
            const base = readSkillRowNumber(row, "base", 0);
            const occupationPoints = readSkillRowNumber(row, "occupationPoints", 0);
            const interestPoints = readSkillRowNumber(row, "interestPoints", 0);
            const growthPoints = readSkillRowNumber(row, "growthPoints", 0);
            const value = clampNumber(base + occupationPoints + interestPoints + growthPoints, 0, 99, base);
            const name = isCustomSkill(skillKey) ? readCustomSkillName(row) || skillNameById(skillKey) : baseSkill?.name || skillNameById(skillKey);
            return {
                ...(baseSkill || {}),
                id: rowId,
                skillKey,
                name,
                base,
                value,
                category: row.dataset.skillCategory || baseSkill?.category || "其他",
                checked: occupation,
                occupation,
                specialty: row.dataset.specialtyLabel || "",
                specialtyKey: row.dataset.specialtyKey || "",
                occupationPoints,
                interestPoints,
                growthPoints,
                rank: rankFromValue(value)
            };
        });
    }

    function readCustomSkillName(row: HTMLTableRowElement): string {
        return String(row.querySelector<HTMLInputElement>("[data-custom-skill-name]")?.value || "").trim().slice(0, 40);
    }

    function syncCustomSkillDisplayName(row: HTMLTableRowElement): void {
        const skillKey = row.dataset.skillKey || "";
        if (!isCustomSkill(skillKey)) return;
        const display = row.querySelector<HTMLElement>("[data-skill-display-name]");
        if (display) display.textContent = readCustomSkillName(row) || skillNameById(skillKey);
    }

    function readSkillRowNumber(row: HTMLTableRowElement, kind: "base" | "occupationPoints" | "interestPoints" | "growthPoints", fallback: number): number {
        const selectors = {
            base: "[data-skill-base]",
            occupationPoints: "[data-skill-occupation-points]",
            interestPoints: "[data-skill-interest-points]",
            growthPoints: "[data-skill-growth-points]"
        };
        const element = row.querySelector<HTMLInputElement | HTMLElement>(selectors[kind]);
        const value = element instanceof HTMLInputElement ? element.value : element?.textContent;
        return clampNumber(value, 0, 99, fallback);
    }

    function refreshSkillTableVisibility(): void {
        const body = byId("characterSkillTableBody");
        if (!body) return;
        body.querySelectorAll<HTMLTableRowElement>("tr[data-skill-row-id]").forEach((row) => {
            const category = row.dataset.skillCategory || "其他";
            row.hidden = activeSkillCategoryFilter !== "全部技能" && category !== activeSkillCategoryFilter;
        });
    }

    function refreshSkillTableCalculations(): void {
        const body = byId("characterSkillTableBody");
        if (!body) return;
        body.querySelectorAll<HTMLTableRowElement>("tr[data-skill-row-id]").forEach(refreshSkillRowCalculations);
        refreshSkillPointSummary();
        refreshWeaponSuccessRates();
    }

    function refreshSkillRowCalculations(row: HTMLTableRowElement): void {
        const occupationCheckbox = row.querySelector<HTMLInputElement>("[data-skill-occupation-checkbox]");
        const occupationInput = row.querySelector<HTMLInputElement>("[data-skill-occupation-points]");
        const interestInput = row.querySelector<HTMLInputElement>("[data-skill-interest-points]");
        const growthInput = row.querySelector<HTMLInputElement>("[data-skill-growth-points]");
        const successOutput = row.querySelector<HTMLElement>("[data-skill-success]");
        const hardOutput = row.querySelector<HTMLElement>("[data-skill-hard]");
        const extremeOutput = row.querySelector<HTMLElement>("[data-skill-extreme]");
        const base = readSkillRowNumber(row, "base", 0);
        const isOccupation = Boolean(occupationCheckbox?.checked);
        row.dataset.skillOccupation = isOccupation ? "1" : "0";
        if (occupationInput) {
            occupationInput.disabled = !isOccupation;
            if (!isOccupation && Number(occupationInput.value || 0) > 0) {
                occupationInput.value = "0";
                notify("只有本职技能才能添加点数", "error");
            }
            occupationInput.value = String(clampNumber(occupationInput.value, 0, getSkillLimit("occupation"), 0));
        }
        if (interestInput) interestInput.value = String(clampNumber(interestInput.value, 0, getSkillLimit("other"), 0));
        if (growthInput) growthInput.value = String(clampNumber(growthInput.value, 0, getSkillLimit("other"), 0));
        enforceSkillPointBudgets();
        const occupationPoints = readSkillRowNumber(row, "occupationPoints", 0);
        const interestPoints = readSkillRowNumber(row, "interestPoints", 0);
        const growthPoints = readSkillRowNumber(row, "growthPoints", 0);
        const success = clampNumber(base + occupationPoints + interestPoints + growthPoints, 0, getSkillLimit("occupation"), base);
        if (successOutput) successOutput.textContent = String(success);
        if (hardOutput) hardOutput.textContent = String(Math.floor(success / 2));
        if (extremeOutput) extremeOutput.textContent = String(Math.floor(success / 5));
        refreshSkillPointSummary();
    }

    function enforceSkillPointBudgets(): void {
        const body = byId("characterSkillTableBody");
        if (!body) return;
        const occupationTotal = clampNumber(getInputValue("characterOccupationSkillPoints"), 0, 999, 0);
        const interestTotal = clampNumber(getInputValue("characterPersonalInterestPoints"), 0, 999, 0);
        clampColumnToBudget(Array.from(body.querySelectorAll<HTMLInputElement>("[data-skill-occupation-points]")), occupationTotal);
        clampColumnToBudget(Array.from(body.querySelectorAll<HTMLInputElement>("[data-skill-interest-points]")), interestTotal);
    }

    function clampColumnToBudget(inputs: HTMLInputElement[], budget: number): void {
        let total = 0;
        inputs.forEach((input) => {
            const value = clampNumber(input.value, 0, 99, 0);
            const allowed = Math.max(0, budget - total);
            const nextValue = Math.min(value, allowed);
            if (nextValue !== value) input.value = String(nextValue);
            total += nextValue;
        });
    }

    function refreshEditorRuleSummary(): void {
        const attributes = readAttributes();
        syncAttributeDerivedFields(attributes);
        syncEditorResourceLimits(attributes);
        syncEditorCombatStats(attributes);
        syncGeneratedSkillPointInputs(false);
        refreshSkillTableCalculations();
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
        const body = byId("characterSkillTableBody");
        if (!body) return { occupation: 0, personal: 0 };
        const rows = Array.from(body.querySelectorAll<HTMLTableRowElement>("tr[data-skill-row-id]"));
        return rows.reduce((summary, row) => {
            const occupationInput = row.querySelector<HTMLInputElement>("[data-skill-occupation-points]");
            const interestInput = row.querySelector<HTMLInputElement>("[data-skill-interest-points]");
            summary.occupation += clampNumber(occupationInput?.value, 0, 99, 0);
            summary.personal += clampNumber(interestInput?.value, 0, 99, 0);
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
            weapons: readWeaponRows(),
            damageBonus: getInputValue("characterDamageBonus") || calculateBuildAndDamageBonus(attributes).damageBonus,
            build: clampNumber(getInputValue("characterBuild"), -2, 99, calculateBuildAndDamageBonus(attributes).build),
            armor: clampNumber(getInputValue("characterArmor"), 0, 99, 0),
            mov: clampNumber(getInputValue("characterMov"), 0, 99, calculateMov(attributes)),
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
            <section class="character-section"><h4>武器</h4>${card.weapons.map(renderWeaponDetailRow).join("") || `<div class="background-note">暂无武器</div>`}</section>
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

    function renderWeaponDetailRow(weapon: COC7Weapon): string {
        const impale = weapon.impale ? "贯穿" : "非贯穿";
        return `<div class="equipment-row"><strong>${escapeHtml(weapon.name)}</strong><br><small>${escapeHtml(weapon.skill)} · ${escapeHtml(weapon.damage)} · ${escapeHtml(weapon.range)} · ${impale} · 次数 ${escapeHtml(weapon.attacks)} · 装弹 ${escapeHtml(weapon.ammo)} · 故障 ${escapeHtml(weapon.malfunction)}</small></div>`;
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

