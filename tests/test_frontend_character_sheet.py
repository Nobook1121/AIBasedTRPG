import json
import subprocess
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
INDEX_HTML = PROJECT_ROOT / "index.html"
STYLE_CSS = PROJECT_ROOT / "style.css"
CHARACTER_TS = PROJECT_ROOT / "frontend" / "src" / "js" / "character-sheet.ts"
CHARACTER_JS = PROJECT_ROOT / "js" / "character-sheet.js"
SAMPLE_CHARACTER_JSON = PROJECT_ROOT / "frontend" / "data" / "characters" / "sample-investigator.json"


def _read(path):
    return path.read_text(encoding="utf-8")


def _run_character_rules(script):
    node_script = f"""
const fs = require('fs');
const vm = require('vm');
const source = fs.readFileSync({json.dumps(str(CHARACTER_JS))}, 'utf8');
const context = {{ console, window: {{}}, document: {{}}, fetch: async () => ({{ ok: false }}) }};
vm.createContext(context);
vm.runInContext(source, context);
const api = context.window.COC7CharacterSheet || context.COC7CharacterSheet;
const result = (() => {{
{script}
}})();
console.log(JSON.stringify(result));
"""
    completed = subprocess.run(
        ["node", "-e", node_script],
        cwd=PROJECT_ROOT,
        check=True,
        text=True,
        encoding="utf-8",
        capture_output=True,
    )
    return json.loads(completed.stdout)


def test_coc7_rule_calculations_match_required_formulas():
    result = _run_character_rules(
        """
const attributes = { STR: 50, CON: 60, SIZ: 70, DEX: 55, APP: 45, INT: 80, POW: 65, EDU: 70, LUK: 50, AGE: 42 };
return {
  maxHp: api.calculateMaxHp(attributes),
  maxSan: api.calculateMaxSan(attributes),
  mov: api.calculateMov(attributes),
  noDamageBonus: api.calculateBuildAndDamageBonus(attributes),
  d4DamageBonus: api.calculateBuildAndDamageBonus({ ...attributes, STR: 60 })
};
"""
    )

    assert result["maxHp"] == 13
    assert result["maxSan"] == 65
    assert result["mov"] == 6
    assert result["noDamageBonus"] == {"build": 0, "damageBonus": "0"}
    assert result["d4DamageBonus"] == {"build": 1, "damageBonus": "+1D4"}


def test_coc7_runtime_helpers_cover_skills_assets_and_equipment():
    result = _run_character_rules(
        """
const card = api.createCharacterCard({
  id: "test-card",
  name: "测试调查员",
  playerId: "player-1",
  occupationId: "detective",
  attributes: { STR: 50, CON: 60, SIZ: 70, DEX: 55, APP: 45, INT: 80, POW: 65, EDU: 70, LUK: 50, AGE: 42 },
  skills: [
    { id: "spotHidden", name: "侦查", value: 65, checked: true, category: "探索" },
    { id: "libraryUse", name: "图书馆使用", value: 70, checked: true, category: "知识" },
    { id: "cthulhuMythos", name: "克苏鲁神话", value: 5, checked: false, category: "神话" }
  ],
  equipment: [{ name: "急救包", quantity: 2, weight: 0.8, notes: "医疗" }],
  weapons: [{ name: "左轮手枪", skill: "射击", damage: "1D10", range: "15m", attacks: 1, ammo: 6, malfunction: 100 }],
  assets: { cash: 20, spendingLevel: 10, assetsText: "旧车" },
  relationships: [{ name: "陈教授", description: "导师" }]
});
return {
  check: api.rollAttributeCheck(card.attributes, "INT", () => 42),
  skillGroups: api.groupSkillsByCategory(card.skills),
  selectedSkillCount: api.countSelectedOccupationSkills(card.skills),
  load: api.calculateEquipmentLoad(card.equipment),
  passives: api.getOccupationPassiveEffects(card).length,
  generatedName: api.generateInvestigatorName("male", () => 0)
};
"""
    )

    assert result["check"] == {"roll": 42, "target": 80, "success": True, "level": "普通成功"}
    assert result["skillGroups"] == {"探索": 1, "知识": 1, "神话": 1}
    assert result["selectedSkillCount"] == 2
    assert result["load"] == {"totalWeight": 1.6, "totalVolume": 0}
    assert result["passives"] >= 1
    assert result["generatedName"]


def test_character_sheet_typescript_defines_coc7_data_model_and_loads_external_sample():
    source = _read(CHARACTER_TS)

    assert "interface COC7CharacterCard" in source
    assert "type COC7AttributeKey = \"STR\" | \"CON\" | \"SIZ\" | \"DEX\" | \"APP\" | \"INT\" | \"POW\" | \"EDU\" | \"LUK\" | \"AGE\"" in source
    assert "PRESET_OCCUPATIONS" in source
    assert "DEFAULT_CHARACTER" not in source
    assert "sample-investigator.json" in source
    assert SAMPLE_CHARACTER_JSON.exists()
    sample = json.loads(_read(SAMPLE_CHARACTER_JSON))
    assert sample["name"]
    assert sample["occupationId"]
    assert "技能等级" in source
    assert "equipment" in source
    assert "weapons" in source
    assert "assets" in source
    assert "relationships" in source


def test_character_management_page_has_full_coc7_workspace():
    html = _read(INDEX_HTML)

    assert 'id="characterWorkspace"' in html
    assert 'id="character-list-view"' in html
    assert 'id="character-detail-page"' in html
    assert 'id="backToCharacterList"' in html
    assert 'id="characterInspector"' in html
    assert 'id="characterDetailView"' in html
    assert 'id="characterOccupation"' in html
    assert 'id="characterAvatarUpload"' in html
    assert 'id="randomizeCharacterName"' in html
    assert 'id="randomizeAttributes"' in html
    assert 'id="characterSkillChecklist"' in html
    assert 'id="skillLevelFilters"' in html
    assert 'src="js/character-sheet.js"' in html
    assert html.index('src="js/character-sheet.js"') < html.index('src="js/main.js"')


def test_character_sheet_site_wide_light_styles_and_card_detail_flow_exist():
    css = _read(STYLE_CSS)
    source = _read(CHARACTER_TS)

    assert ".character-workspace" in css
    assert ".character-list-view" in css
    assert ".character-detail-page" in css
    assert ".character-card" in css
    assert ".character-detail-view" in css
    assert ".skill-check-grid" in css
    assert "background: var(--color-bg);" in css
    assert "border: 1px solid var(--border-subtle);" in css
    assert "openCharacterDetail" in source
    assert "showCharacterList" in source
    assert "renderCharacterCardSummary" in source


def test_character_sheet_keeps_room_scoped_runtime_records_out_of_character_manager():
    source = _read(CHARACTER_TS)

    assert "listCharacterCards" in source
    assert "getCharacterCardSnapshot" in source
    assert "data-inspector-action=\"check\"" not in source
    assert "data-inspector-action=\"injury\"" not in source
    assert "data-inspector-action=\"san\"" not in source
    assert "alert(" not in source
    assert "生命值/受伤记录" not in source
    assert "San 值检定和损失记录" not in source
