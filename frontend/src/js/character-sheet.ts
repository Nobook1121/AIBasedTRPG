type COC7AttributeKey = "STR" | "CON" | "SIZ" | "DEX" | "APP" | "INT" | "POW" | "EDU" | "LUK" | "AGE";
type SkillRank = "新手" | "学习" | "熟修" | "主修";
type SkillCategory = "探索" | "社交" | "知识" | "战斗" | "行动" | "神话";
type InvestigatorGender = "male" | "female";

interface COC7Attributes {
    STR: number;
    CON: number;
    SIZ: number;
    DEX: number;
    APP: number;
    INT: number;
    POW: number;
    EDU: number;
    LUK: number;
    AGE: number;
}

interface COC7Skill {
    id: string;
    name: string;
    value: number;
    base: number;
    category: SkillCategory | string;
    checked: boolean;
    rank?: SkillRank;
}

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
    creditRating: [number, number];
    occupationSkills: string[];
    skillBonuses: Record<string, number>;
    specialties: string[];
    passiveEffects: string[];
}

interface COC7CharacterCard {
    id: string;
    name: string;
    playerId: string;
    gender: InvestigatorGender;
    age: number;
    avatar: string;
    occupationId: string;
    residence: string;
    birthplace: string;
    attributes: COC7Attributes;
    maxHp: number;
    currentHp: number;
    maxSan: number;
    currentSan: number;
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

interface AttributeCheckResult {
    roll: number;
    target: number;
    success: boolean;
    level: string;
}

interface CharacterApi {
    ATTRIBUTE_KEYS: COC7AttributeKey[];
    SKILL_RANKS: SkillRank[];
    PRESET_OCCUPATIONS: COC7Occupation[];
    calculateMaxHp: (attributes: COC7Attributes) => number;
    calculateMaxSan: (attributes: COC7Attributes) => number;
    calculateMov: (attributes: COC7Attributes) => number;
    calculateBuildAndDamageBonus: (attributes: Pick<COC7Attributes, "STR" | "SIZ">) => { build: number; damageBonus: string };
    calculateEquipmentLoad: (equipment: COC7EquipmentItem[]) => { totalWeight: number; totalVolume: number };
    groupSkillsByCategory: (skills: COC7Skill[]) => Record<string, number>;
    countSkillsByRank: (skills: COC7Skill[]) => Record<SkillRank, number>;
    countSelectedOccupationSkills: (skills: COC7Skill[]) => number;
    getOccupationPassiveEffects: (card: COC7CharacterCard) => string[];
    rollAttributeCheck: (attributes: COC7Attributes, attributeKey: COC7AttributeKey, roller?: () => number) => AttributeCheckResult;
    generateInvestigatorName: (gender?: InvestigatorGender, random?: () => number) => string;
    randomizeAttributes: (random?: () => number) => COC7Attributes;
    createCharacterCard: (input?: Partial<COC7CharacterCard>) => COC7CharacterCard;
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
    const SAMPLE_CHARACTER_URL = "frontend/data/characters/sample-investigator.json";
    const ATTRIBUTE_KEYS: COC7AttributeKey[] = ["STR", "CON", "SIZ", "DEX", "APP", "INT", "POW", "EDU", "LUK", "AGE"];
    const SKILL_RANKS: SkillRank[] = ["新手", "学习", "熟修", "主修"];
    const LAST_NAMES = ["林", "陈", "顾", "沈", "周", "陆", "许", "梁"];
    const MALE_NAMES = ["雨衡", "明远", "怀瑾", "景行", "子昂", "修文"];
    const FEMALE_NAMES = ["若宁", "清荷", "知遥", "南枝", "书瑶", "映雪"];

    const PRESET_OCCUPATIONS: COC7Occupation[] = [
        {
            id: "detective",
            name: "私家侦探",
            creditRating: [9, 30],
            occupationSkills: ["artCraft", "disguise", "law", "libraryUse", "psychology", "spotHidden", "stealth", "social"],
            skillBonuses: { spotHidden: 20, listen: 15, psychology: 15, libraryUse: 10 },
            specialties: ["调查", "跟踪", "线索整合"],
            passiveEffects: ["调查场景中第一次侦查或聆听检定可获得 +10 情境加值。"]
        },
        {
            id: "doctor",
            name: "医生",
            creditRating: [30, 80],
            occupationSkills: ["firstAid", "medicine", "psychology", "science", "biology", "pharmacy", "languageOther", "social"],
            skillBonuses: { medicine: 25, firstAid: 20, psychology: 10, science: 10 },
            specialties: ["治疗", "诊断", "解剖"],
            passiveEffects: ["处理伤势时，急救成功后可额外恢复 1 点生命值。"]
        },
        {
            id: "professor",
            name: "大学教授",
            creditRating: [20, 70],
            occupationSkills: ["libraryUse", "languageOwn", "history", "archaeology", "science", "psychology", "languageOther", "social"],
            skillBonuses: { libraryUse: 25, languageOwn: 20, history: 15, archaeology: 15 },
            specialties: ["学术研究", "文献检索", "古物辨识"],
            passiveEffects: ["学术分组技能检定成功后，可额外获得一条背景线索。"]
        }
    ];

    const BASE_SKILLS: COC7Skill[] = [
        { id: "accounting", name: "会计", base: 5, value: 5, category: "知识", checked: false },
        { id: "anthropology", name: "人类学", base: 1, value: 1, category: "知识", checked: false },
        { id: "archaeology", name: "考古学", base: 1, value: 1, category: "知识", checked: false },
        { id: "artCraft", name: "艺术/手艺", base: 5, value: 5, category: "知识", checked: false },
        { id: "charm", name: "魅惑", base: 15, value: 15, category: "社交", checked: false },
        { id: "climb", name: "攀爬", base: 20, value: 20, category: "行动", checked: false },
        { id: "cthulhuMythos", name: "克苏鲁神话", base: 0, value: 0, category: "神话", checked: false },
        { id: "disguise", name: "乔装", base: 5, value: 5, category: "社交", checked: false },
        { id: "dodge", name: "闪避", base: 25, value: 25, category: "战斗", checked: false },
        { id: "driveAuto", name: "汽车驾驶", base: 20, value: 20, category: "行动", checked: false },
        { id: "fastTalk", name: "话术", base: 5, value: 5, category: "社交", checked: false },
        { id: "fightingBrawl", name: "格斗", base: 25, value: 25, category: "战斗", checked: false },
        { id: "firearmsHandgun", name: "射击/手枪", base: 20, value: 20, category: "战斗", checked: false },
        { id: "firstAid", name: "急救", base: 30, value: 30, category: "探索", checked: false },
        { id: "history", name: "历史", base: 5, value: 5, category: "知识", checked: false },
        { id: "intimidate", name: "恐吓", base: 15, value: 15, category: "社交", checked: false },
        { id: "jump", name: "跳跃", base: 20, value: 20, category: "行动", checked: false },
        { id: "languageOwn", name: "母语", base: 70, value: 70, category: "知识", checked: false },
        { id: "law", name: "法律", base: 5, value: 5, category: "知识", checked: false },
        { id: "libraryUse", name: "图书馆使用", base: 20, value: 20, category: "知识", checked: false },
        { id: "listen", name: "聆听", base: 20, value: 20, category: "探索", checked: false },
        { id: "locksmith", name: "锁匠", base: 1, value: 1, category: "探索", checked: false },
        { id: "medicine", name: "医学", base: 1, value: 1, category: "知识", checked: false },
        { id: "naturalWorld", name: "博物学", base: 10, value: 10, category: "知识", checked: false },
        { id: "navigate", name: "导航", base: 10, value: 10, category: "行动", checked: false },
        { id: "occult", name: "神秘学", base: 5, value: 5, category: "神话", checked: false },
        { id: "persuade", name: "说服", base: 10, value: 10, category: "社交", checked: false },
        { id: "psychology", name: "心理学", base: 10, value: 10, category: "社交", checked: false },
        { id: "science", name: "科学", base: 1, value: 1, category: "知识", checked: false },
        { id: "sleightOfHand", name: "妙手", base: 10, value: 10, category: "行动", checked: false },
        { id: "spotHidden", name: "侦查", base: 25, value: 25, category: "探索", checked: false },
        { id: "stealth", name: "潜行", base: 20, value: 20, category: "行动", checked: false },
        { id: "survival", name: "生存", base: 10, value: 10, category: "行动", checked: false },
        { id: "track", name: "追踪", base: 10, value: 10, category: "探索", checked: false }
    ];

    let cards: COC7CharacterCard[] = [];
    let activeCardId = "";
    let modal: BootstrapModalInstance | null = null;

    function clampNumber(value: unknown, min: number, max: number, fallback: number): number {
        const parsed = Number(value);
        if (!Number.isFinite(parsed)) return fallback;
        return Math.min(max, Math.max(min, Math.round(parsed)));
    }

    function rollD6(random: () => number): number {
        return Math.floor(random() * 6) + 1;
    }

    function randomizeAttributes(random: () => number = Math.random): COC7Attributes {
        const roll3d6 = (): number => (rollD6(random) + rollD6(random) + rollD6(random)) * 5;
        const roll2d6plus6 = (): number => (rollD6(random) + rollD6(random) + 6) * 5;
        return {
            STR: roll3d6(),
            CON: roll3d6(),
            SIZ: roll2d6plus6(),
            DEX: roll3d6(),
            APP: roll3d6(),
            INT: roll2d6plus6(),
            POW: roll3d6(),
            EDU: roll2d6plus6(),
            LUK: roll3d6(),
            AGE: 25
        };
    }

    function calculateMaxHp(attributes: COC7Attributes): number {
        return Math.floor((attributes.CON + attributes.SIZ) / 10);
    }

    function calculateMaxSan(attributes: COC7Attributes): number {
        return attributes.POW;
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
        return skills.filter((skill) => skill.checked).length;
    }

    function getOccupation(card: COC7CharacterCard): COC7Occupation {
        return PRESET_OCCUPATIONS.find((occupation) => occupation.id === card.occupationId) || PRESET_OCCUPATIONS[0] as COC7Occupation;
    }

    function getOccupationPassiveEffects(card: COC7CharacterCard): string[] {
        return [...getOccupation(card).passiveEffects];
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
        const last = LAST_NAMES[Math.floor(random() * LAST_NAMES.length)] || LAST_NAMES[0];
        const pool = gender === "female" ? FEMALE_NAMES : MALE_NAMES;
        return `${last}${pool[Math.floor(random() * pool.length)] || pool[0]}`;
    }

    function normalizeAttributes(input?: Partial<COC7Attributes>): COC7Attributes {
        return {
            STR: clampNumber(input?.STR, 1, 99, 50),
            CON: clampNumber(input?.CON, 1, 99, 50),
            SIZ: clampNumber(input?.SIZ, 1, 99, 50),
            DEX: clampNumber(input?.DEX, 1, 99, 50),
            APP: clampNumber(input?.APP, 1, 99, 50),
            INT: clampNumber(input?.INT, 1, 99, 50),
            POW: clampNumber(input?.POW, 1, 99, 50),
            EDU: clampNumber(input?.EDU, 1, 99, 50),
            LUK: clampNumber(input?.LUK, 1, 99, 50),
            AGE: clampNumber(input?.AGE, 15, 99, 25)
        };
    }

    function createCharacterCard(input: Partial<COC7CharacterCard> = {}): COC7CharacterCard {
        const attributes = normalizeAttributes(input.attributes);
        const maxHp = calculateMaxHp(attributes);
        const maxSan = calculateMaxSan(attributes);
        const damage = calculateBuildAndDamageBonus(attributes);
        const now = new Date().toISOString();
        return {
            id: input.id || `investigator-${Date.now()}-${Math.random().toString(36).slice(2, 8)}`,
            name: input.name || generateInvestigatorName(input.gender || "male"),
            playerId: input.playerId || "未指定玩家",
            gender: input.gender || "male",
            age: attributes.AGE,
            avatar: input.avatar || "",
            occupationId: input.occupationId || PRESET_OCCUPATIONS[0]?.id || "detective",
            residence: input.residence || "",
            birthplace: input.birthplace || "",
            attributes,
            maxHp,
            currentHp: clampNumber(input.currentHp, 0, maxHp, maxHp),
            maxSan,
            currentSan: clampNumber(input.currentSan, 0, maxSan, maxSan),
            mov: calculateMov(attributes),
            build: damage.build,
            damageBonus: damage.damageBonus,
            skills: normalizeSkills(input.skills),
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

    function normalizeSkills(skills?: COC7Skill[]): COC7Skill[] {
        const source = skills && skills.length ? skills : BASE_SKILLS;
        return source.map((skill) => ({
            id: skill.id || slugify(skill.name),
            name: String(skill.name || "未命名技能").slice(0, 40),
            base: clampNumber(skill.base, 0, 99, 0),
            value: clampNumber(skill.value, 0, 99, skill.base || 0),
            category: skill.category || "知识",
            checked: Boolean(skill.checked),
            rank: skill.rank || rankFromValue(skill.value)
        }));
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

    async function loadSampleCharacter(): Promise<COC7CharacterCard> {
        try {
            const response = await fetch(SAMPLE_CHARACTER_URL);
            if (response.ok) return createCharacterCard(await response.json() as Partial<COC7CharacterCard>);
        } catch (error) {
            console.warn("加载示例角色失败:", error);
        }
        return createCharacterCard();
    }

    async function loadCards(): Promise<void> {
        const storage = safeStorage();
        if (storage) {
            try {
                const parsed = JSON.parse(storage.getItem(STORAGE_KEY) || "[]") as unknown;
                if (Array.isArray(parsed) && parsed.length) {
                    cards = parsed.map((card) => createCharacterCard(card as Partial<COC7CharacterCard>));
                    activeCardId = storage.getItem(ACTIVE_STORAGE_KEY) || cards[0]?.id || "";
                    return;
                }
            } catch {
                cards = [];
            }
        }
        cards = [await loadSampleCharacter()];
        activeCardId = cards[0]?.id || "";
    }

    function persistCards(): void {
        const storage = safeStorage();
        if (!storage) return;
        storage.setItem(STORAGE_KEY, JSON.stringify(cards));
        storage.setItem(ACTIVE_STORAGE_KEY, activeCardId);
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
        hydrateOccupationSelect();
        hydrateSkillChecklist();
        bindEvents();
        void loadCards().then(render);
    }

    function bindEvents(): void {
        byId("createCharacter")?.addEventListener("click", () => openEditor());
        byId("saveCharacter")?.addEventListener("click", saveFromEditor);
        byId("exportCharacter")?.addEventListener("click", exportActiveCard);
        byId("backToCharacterList")?.addEventListener("click", showCharacterList);
        byId("randomizeCharacterName")?.addEventListener("click", () => setInputValue("characterName", generateInvestigatorName()));
        byId("randomizeAttributes")?.addEventListener("click", () => {
            const attributes = randomizeAttributes();
            ATTRIBUTE_KEYS.forEach((key) => setInputValue(`attribute${key}`, attributes[key]));
        });
        byId<HTMLInputElement>("characterAvatarUpload")?.addEventListener("change", handleAvatarUpload);
    }

    function hydrateOccupationSelect(): void {
        const select = byId<HTMLSelectElement>("characterOccupation");
        if (!select) return;
        select.innerHTML = PRESET_OCCUPATIONS.map((occupation) => `<option value="${escapeHtml(occupation.id)}">${escapeHtml(occupation.name)}</option>`).join("");
    }

    function hydrateSkillChecklist(skills: COC7Skill[] = BASE_SKILLS): void {
        const container = byId("characterSkillChecklist");
        if (!container) return;
        container.innerHTML = skills.map((skill) => `
            <label class="skill-check-item">
                <input type="checkbox" data-skill-id="${escapeHtml(skill.id)}" ${skill.checked ? "checked" : ""}>
                <span>${escapeHtml(skill.name)}</span>
                <input type="number" min="0" max="99" value="${skill.value}" data-skill-value="${escapeHtml(skill.id)}">
            </label>
        `).join("");
    }

    function openEditor(card?: COC7CharacterCard): void {
        const target = card ? cloneCard(card) : createCharacterCard();
        setInputValue("characterEditingId", card?.id || "");
        setInputValue("characterName", target.name);
        setInputValue("playerId", target.playerId);
        setInputValue("characterOccupation", target.occupationId);
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
        setInputValue("characterSkills", formatSkills(target.skills));
        setInputValue("characterWeapons", formatWeapons(target.weapons));
        setInputValue("characterEquipment", formatEquipment(target.equipment));
        setInputValue("characterAssets", formatAssets(target.assets));
        hydrateSkillChecklist(target.skills);
        modal?.show();
    }

    function handleAvatarUpload(event: Event): void {
        const input = event.target as HTMLInputElement | null;
        const file = input?.files?.[0];
        if (!file) return;
        const reader = new FileReader();
        reader.onload = () => {
            input.dataset.avatar = String(reader.result || "");
        };
        reader.readAsDataURL(file);
    }

    function setInputValue(id: string, value: unknown): void {
        const field = byId<HTMLInputElement | HTMLTextAreaElement | HTMLSelectElement>(id);
        if (field) field.value = String(value ?? "");
    }

    function getInputValue(id: string): string {
        return byId<HTMLInputElement | HTMLTextAreaElement | HTMLSelectElement>(id)?.value.trim() || "";
    }

    function readAttributes(): COC7Attributes {
        return normalizeAttributes(Object.fromEntries(ATTRIBUTE_KEYS.map((key) => [key, Number(getInputValue(`attribute${key}`))])) as Partial<COC7Attributes>);
    }

    function readChecklistSkills(): COC7Skill[] {
        const container = byId("characterSkillChecklist");
        if (!container) return parseSkills(getInputValue("characterSkills"));
        return BASE_SKILLS.map((base) => {
            const checked = container.querySelector<HTMLInputElement>(`[data-skill-id="${CSS.escape(base.id)}"]`)?.checked || false;
            const value = Number(container.querySelector<HTMLInputElement>(`[data-skill-value="${CSS.escape(base.id)}"]`)?.value || base.value);
            return { ...base, checked, value: clampNumber(value, 0, 99, base.base), rank: rankFromValue(value) };
        });
    }

    function saveFromEditor(): void {
        const editingId = getInputValue("characterEditingId");
        const existing = cards.find((card) => card.id === editingId);
        const attributes = readAttributes();
        const avatarInput = byId<HTMLInputElement>("characterAvatarUpload");
        const cardInput: Partial<COC7CharacterCard> = {
            ...existing,
            name: getInputValue("characterName") || generateInvestigatorName(),
            playerId: getInputValue("playerId") || "未指定玩家",
            occupationId: getInputValue("characterOccupation") || "detective",
            avatar: avatarInput?.dataset.avatar || existing?.avatar || "",
            residence: getInputValue("characterResidence"),
            birthplace: getInputValue("characterBirthplace"),
            attributes,
            skills: mergeManualSkills(readChecklistSkills(), parseSkills(getInputValue("characterSkills"))),
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
        if (editingId) cardInput.id = editingId;
        const card = createCharacterCard(cardInput);
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

    function renderList(): void {
        const list = byId("characterList");
        if (!list) return;
        list.innerHTML = cards.map(renderCharacterCardSummary).join("");
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
                    <span>HP ${card.currentHp}/${card.maxHp}</span>
                    <span>SAN ${card.currentSan}/${card.maxSan}</span>
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
        return `
            <header class="character-inspector-header">
                <div>
                    <h3>${escapeHtml(card.name)}</h3>
                    <div class="character-tag-row">
                        <span class="character-tag">${escapeHtml(occupation.name)}</span>
                        <span class="character-tag">信用评级 ${occupation.creditRating[0]}-${occupation.creditRating[1]}</span>
                        <span class="character-tag">伤害加值 ${escapeHtml(card.damageBonus)}</span>
                        <span class="character-tag">体格 ${card.build}</span>
                    </div>
                </div>
                <div class="character-inline-actions"><button type="button" data-character-edit-active><i class="fa fa-pencil"></i> 编辑角色卡</button></div>
            </header>
            <section class="character-section"><h4>属性</h4><div class="character-attribute-grid">${ATTRIBUTE_KEYS.map((key) => `<div class="attribute-chip"><span>${key}</span><strong>${card.attributes[key]}</strong></div>`).join("")}</div></section>
            <section class="character-section"><h4>状态</h4><div class="character-vital-grid">${statCard("生命值", `${card.currentHp}/${card.maxHp}`)}${statCard("San 值", `${card.currentSan}/${card.maxSan}`)}${statCard("幸运", card.attributes.LUK)}${statCard("移动速度", card.mov)}</div></section>
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
        return cards.map(cloneCard);
    }

    function getCharacterCardSnapshot(cardId: string): Partial<COC7CharacterCard> | null {
        const card = cards.find((item) => item.id === cardId);
        return card ? cloneCard(card) : null;
    }

    function notify(message: string, type = "info"): void {
        const notifier = (global as unknown as { showNotification?: (message: string, type?: string) => void }).showNotification;
        if (typeof notifier === "function") notifier(message, type);
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
        PRESET_OCCUPATIONS,
        calculateMaxHp,
        calculateMaxSan,
        calculateMov,
        calculateBuildAndDamageBonus,
        calculateEquipmentLoad,
        groupSkillsByCategory,
        countSkillsByRank,
        countSelectedOccupationSkills,
        getOccupationPassiveEffects,
        rollAttributeCheck,
        generateInvestigatorName,
        randomizeAttributes,
        createCharacterCard,
        listCharacterCards,
        getCharacterCardSnapshot,
        initCharacterSheet
    };

    global.COC7CharacterSheet = api;
})(typeof window !== "undefined" ? window : globalThis as Window & typeof globalThis);
