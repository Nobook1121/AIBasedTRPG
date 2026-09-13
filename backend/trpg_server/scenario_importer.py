"""Scenario document extraction and conversion helpers."""
from __future__ import annotations

import io
import json
import logging
import re
import zipfile
from pathlib import Path
from typing import Any, Callable
from xml.etree import ElementTree

try:
    import olefile
except ImportError:  # pragma: no cover
    olefile = None

logger = logging.getLogger(__name__)
_HEADING_RE = re.compile(r"^\s{0,3}(?:#{1,6}\s+|第\s*[一二三四五六七八九十百0-9]+\s*[章节幕场景、:.：]|[0-9]+[、.．]\s*)(.*?)\s*$", re.I)
_HASH_HEADING_RE = re.compile(r"^\s*-?\s*#{1,6}\s*(.+?)\s*$")
_ANGLE_HEADING_RE = re.compile(r"^\s*[<《【].{1,80}[>》】].*$")
_NAMED_HEADING_RE = re.compile(r"^(?:概要|导入|背景|前言|准备|游戏准备|公开信息|时间线|幕后黑手|角色数据|NPC|人物|怪物|敌人|结局|Ending|True End|Bad End|Crazy End)\s*[：:：]?\s*[A-Za-z0-9一二三四五六七八九十百]*$", re.I)
_LOCATION_RE = re.compile(r"(?:车厢|房间|场景|地点|驾驶室|终点站|地下室|大厅|光幕|吊灯|客厅|卧室|走廊|厨房|书房|庭院|仓库)", re.I)
_SCENE_WORDS = ("场景", "scene", "地点", "房间", "车厢", "車廂", "驾驶室", "駕駛室", "大厅", "大廳", "光幕", "吊灯", "客厅", "卧室", "走廊", "厨房", "书房", "庭院", "仓库")
_ENDING_WORDS = ("结局", "ending", "true end", "bad end", "crazy end", "happy end", "normal end")
_PREPARATION_WORDS = ("准备", "游戏准备", "角色创建", "人物创建", "推荐技能", "推荐职业", "人数", "时长", "难度", "道具限制")
_SECTION_TYPES = {
    "导入模块": "opening", "导入": "opening", "开场": "opening", "opening": "opening",
    "背景": "background", "概要": "background", "导入": "background", "前言": "background", "幕后黑手": "background", "background": "background",
    "公开信息": "public_info", "公开资料": "public_info", "public info": "public_info",
    "游戏准备": "preparation", "准备": "preparation", "preparation": "preparation",
    "时间线": "timeline", "timeline": "timeline",
    "结局": "ending", "ending": "ending", "true end": "ending", "bad end": "ending", "crazy end": "ending", "happy end": "ending", "normal end": "ending",
    "npc": "npc", "人物": "npc", "角色数据": "npc", "怪物": "monster", "敌人": "monster", "monster": "monster",
}

_SECTION_TYPES.update({
    "导入模块": "opening", "导入": "opening", "开场": "opening",
    "背景": "background", "概览": "background", "前言": "background",
    "公开信息": "public_info", "公开资料": "public_info",
    "游戏准备": "preparation", "准备": "preparation", "时间线": "timeline",
    "结局": "ending", "True End": "ending", "Bad End": "ending", "Crazy End": "ending",
    "NPC": "npc", "人物": "npc", "角色数据": "npc", "怪物": "monster", "敌人": "monster",
})

def _clean_doc_text(text: str) -> str:
    text = text.replace("\x00", "").replace("\r\n", "\n").replace("\r", "\n")
    text = re.sub(r"[\x01-\x08\x0b\x0c\x0e-\x1f\x7f]", "", text)
    text = re.sub(r"[ \t]+\n", "\n", text)
    return re.sub(r"\n{3,}", "\n\n", text).strip()


def _extract_legacy_doc(raw: bytes) -> str:
    if olefile is None:
        raise ValueError("Legacy .doc files require the olefile package")
    try:
        ole = olefile.OleFileIO(io.BytesIO(raw))
        word = ole.openstream(["WordDocument"]).read()
    except Exception as exc:
        raise ValueError("Unable to read legacy .doc document") from exc
    fc_min = int.from_bytes(word[24:28], "little") if len(word) >= 28 else 0
    fc_mac = int.from_bytes(word[28:32], "little") if len(word) >= 32 else len(word)
    fc_min = max(0, min(fc_min, len(word))); fc_mac = max(fc_min, min(fc_mac, len(word)))
    # For the Word binary files used by the project Fib.fcMac is a byte offset
    # into WordDocument's main text stream. Keep the bounded range so binary
    # padding after the document does not become phantom paragraphs.
    payload = word[fc_min:fc_mac]
    utf16 = payload.decode("utf-16le", errors="ignore")
    text = utf16 if sum(1 for c in utf16 if "\u4e00" <= c <= "\u9fff") >= 20 else payload.decode("gb18030", errors="replace")
    text = re.sub(r"HYPERLINK\s+\"[^\"]*\"[^\r\n]*", "", text, flags=re.I)
    return _clean_doc_text(text)


def extract_script_text(source: str | Path | bytes, filename: str | None = None) -> str:
    if isinstance(source, bytes):
        raw, name = source, filename or "script.txt"
    else:
        path = Path(source)
        if isinstance(source, str) and ("\n" in source or "\r" in source) and not path.exists(): return _clean_doc_text(source)
        name, raw = path.name, path.read_bytes()
    suffix = Path(name).suffix.casefold()
    logger.debug("scenario_import.extract filename=%s suffix=%s bytes=%d", name, suffix, len(raw))
    if suffix == ".doc": return _extract_legacy_doc(raw)
    if suffix == ".docx":
        try:
            with zipfile.ZipFile(io.BytesIO(raw)) as archive: xml = archive.read("word/document.xml")
            root = ElementTree.fromstring(xml)
        except (KeyError, OSError, ValueError, ElementTree.ParseError) as exc: raise ValueError("Unable to read docx document") from exc
        ns = {"w": "http://schemas.openxmlformats.org/wordprocessingml/2006/main"}; paragraphs = []
        for paragraph in root.findall(".//w:p", ns):
            value = "".join(node.text or "" for node in paragraph.findall(".//w:t", ns)).strip()
            if not value: continue
            style = paragraph.find("./w:pPr/w:pStyle", ns); style_name = str(style.get("{http://schemas.openxmlformats.org/wordprocessingml/2006/main}val", "")) if style is not None else ""
            if style_name.casefold().startswith("heading"):
                level = re.search(r"(\d+)", style_name); value = "#" * min(int(level.group(1)) if level else 1, 6) + " " + value
            paragraphs.append(value)
        return _clean_doc_text("\n".join(paragraphs))
    if suffix in {".txt", ".md", ".markdown", ".text"} or not suffix: return _clean_doc_text(raw.decode("utf-8-sig", errors="replace"))
    raise ValueError(f"Unsupported script format: {suffix or 'unknown'}; use txt, md, docx, or doc")


def _summary(text: str, limit: int = 180) -> str:
    compact = re.sub(r"\s+", " ", text).strip(); return compact if len(compact) <= limit else compact[:limit - 1].rstrip() + "…"


def _heading_title(line: str) -> str:
    value = line.strip().replace("車廂", "车厢").replace("車頭", "车头").replace("駕駛室", "驾驶室").replace("號", "号")
    hash_match = _HASH_HEADING_RE.match(value)
    if hash_match:
        value = hash_match.group(1).strip()
    match = _HEADING_RE.match(value)
    if match: return match.group(1).strip()
    if _ANGLE_HEADING_RE.match(value):
        value = re.sub(r"^[<《【]\s*", "", value)
        value = re.sub(r"[>》】].*$", "", value)
        return value.strip()
    value = re.sub(r"^[#\s]+", "", value).strip()
    # In Word exports endings are commonly written as "结局 结局名".  The
    # marker identifies the module type; the remainder is the user-facing
    # ending title.
    ending_name = re.match(r"^(?:结局|Ending)\s+(.+)$", value, re.I)
    return ending_name.group(1).strip() if ending_name else value


def _looks_like_heading(line: str) -> bool:
    plain = line.strip().replace("車廂", "车厢").replace("車頭", "车头").replace("駕駛室", "驾驶室").replace("號", "号")
    if not plain or len(plain) > 80: return False
    if _HASH_HEADING_RE.match(plain): return True
    if plain in {"侦查", "偵查", "灵感", "靈感", "医学", "醫學", "急救", "话术", "話術", "潜行", "潛行", "敏捷", "力量", "体质", "體質", "幸运", "幸運"}: return False
    # A check/result line such as “《侦查》成功……” is prose, not a
    # section boundary.  Only accept bracket headings when the complete line
    # is the heading (optionally followed by “开始地点”).
    if re.search(r"(?:SC|检定|成功|失败|对抗|的话|则|可以|1d\d)", plain, re.I): return False
    if _HEADING_RE.match(plain) or _NAMED_HEADING_RE.match(plain): return True
    if re.match(r"^(?:准备|游戏准备|角色创建|人物创建|推荐技能|推荐职业|人数|时长|难度|道具限制)(?:\s*[：:]?\s*.*)?$", plain, re.I): return True
    if re.match(r"^[<《【].{1,40}[>》】]\s*(?:开始地点|起始地点)?\s*$", plain): return True
    # Standalone location labels exported from Word (e.g. “房间”, “大厅”)
    # are scene boundaries even without brackets or Markdown markers.
    if _LOCATION_RE.fullmatch(plain): return True
    if re.match(r"^(?:第\s*)?[0-9一二三四五六七八九十百]+\s*(?:号|號)?\s*(?:车厢|車廂)(?:开始地点|開始地點)?\s*$", plain): return True
    if re.match(r"^(?:结局|Ending)(?:\s+.+)?$", plain, re.I): return True
    # A trailing Chinese full stop usually marks prose (for example
    # "7号车厢。"), not a section heading. Only trim heading colons here.
    canonical = plain.strip().rstrip(":：")
    if canonical in {"导入模块", "导入", "开场", "背景", "概览", "前言", "公开信息", "公开资料", "游戏准备", "准备", "时间线", "结局", "Ending", "True End", "Bad End", "Crazy End", "NPC", "人物", "角色数据", "怪物", "敌人"}:
        return True
    if re.match(r"^(?:第\s*)?[0-9一二三四五六七八九十百]+\s*号?车厢(?:开始地点|起始地点)?$", canonical) or canonical in {"车头车厢", "驾驶室", "站台", "大厅", "地下室"}:
        return True
    return False


def _module_type(title: str) -> str:
    normalized = re.sub(r"[：:（）()<>《》【】]", " ", title.replace("車廂", "车厢").replace("號", "号").casefold()).strip()
    for key, value in _SECTION_TYPES.items():
        if normalized == key.casefold() or normalized.startswith(key.casefold() + " "): return value
    if any(word.casefold() in normalized for word in _PREPARATION_WORDS): return "preparation"
    if any(word in normalized for word in _ENDING_WORDS): return "ending"
    if any(word in normalized for word in ("npc", "人物", "角色")): return "npc"
    if any(word in normalized for word in ("怪物", "敌人", "monster")): return "monster"
    if any(word in normalized for word in _SCENE_WORDS) or re.search(r"[0-9一二三四五六七八九十百]+\s*(?:号|號)", normalized): return "scene"
    return "background"


def _split_sections(text: str) -> list[tuple[str, str]]:
    sections: list[tuple[str, str]] = []; title = "背景"; body: list[str] = []
    for line in text.splitlines():
        heading = _heading_title(line) if _looks_like_heading(line) else ""
        if heading:
            if body: sections.append((title, "\n".join(body).strip()))
            title, body = heading, []
        else: body.append(line)
    if body or not sections: sections.append((title, "\n".join(body).strip()))
    # Preserve every explicit source heading as its own module.  In
    # particular, do not merge overview/import/timeline sections into one
    # background block: those sections have different visibility and editor
    # purposes, and merging them is what previously produced “one huge
    # background plus one scene”.
    return [(t, c) for t, c in sections if c.strip()]


def analyze_script_structure(text: str) -> dict[str, Any]:
    source = _clean_doc_text(str(text or ""))
    if not source: raise ValueError("script text is empty")
    sections = _split_sections(source); headings = [title for title, _ in sections]; warnings: list[str] = []
    if len(sections) <= 1: warnings.append("未检测到明确章节标题，已将全文作为单个模块保留")
    if not any(_module_type(title) == "scene" for title, _ in sections): warnings.append("未检测到场景标题，请在编辑器中检查模块边界")
    if len(source) > 200_000: warnings.append("文档较长，建议发布前检查模块边界")
    return {"line_count": len(source.splitlines()), "character_count": len(source), "heading_count": len(headings), "section_count": len(sections), "headings": headings, "detected_types": [_module_type(t) for t, _ in sections], "warnings": warnings}


def _empty_module(module_id: str, module_type: str, title: str, content: str, order: int) -> dict[str, Any]:
    module: dict[str, Any] = {"id": module_id, "module_type": module_type, "title": title, "summary": _summary(content), "content": content, "source_order": order, "source_preserved": True, "send_to_ai": True, "notes": "", "visibility": "kp" if module_type in {"background", "opening"} else "public", "inputs": [], "timeline_entries": [], "attributes": {}, "battle": {}, "skills": [], "weapons": [], "triggers": []}
    if module_type == "opening": module["fixed_opening"] = False
    if module_type == "scene": module["scene_id"] = order
    if module_type == "ending": module.update({"ending_id": order, "open_ending": False})
    return module


def convert_script_to_scenario(text: str, metadata: dict[str, Any] | None = None) -> dict[str, Any]:
    source = _clean_doc_text(str(text or ""))
    if not source: raise ValueError("script text is empty")
    result: dict[str, Any] = dict(metadata or {}); result.setdefault("title", "Imported scenario"); result.setdefault("author", "Imported"); result.setdefault("playerCount", 1); result.setdefault("notes", "")
    analysis = analyze_script_structure(source)
    sections = _split_sections(source)
    modules = [_empty_module(f"{_module_type(title)}-{index}", _module_type(title), title, content, index) for index, (title, content) in enumerate(sections, 1)]
    # An explicit 导入/开场 heading is always the first runtime module. If a
    # document starts with a short unheaded prologue before its first scene,
    # keep it as opening instead of burying it in background.
    opening_indexes = [i for i, item in enumerate(modules) if item["module_type"] == "opening"]
    if opening_indexes:
        first = opening_indexes[0]
        opening = modules.pop(first)
        modules.insert(0, opening)
    elif modules and modules[0]["module_type"] == "background":
        first_title, first_content = sections[0]
        later_scene = any(item["module_type"] == "scene" for item in modules[1:])
        if later_scene and not _looks_like_heading(first_title) and len(first_content) <= 4000:
            modules[0] = _empty_module("opening-1", "opening", "导入模块", first_content, 1)
    if not any(item["module_type"] == "scene" for item in modules):
        if modules and len(modules) > 1:
            modules[0]["module_type"] = "scene"
            modules[0]["scene_id"] = 1
        else:
            modules.insert(0, _empty_module("scene-1", "scene", "场景 1", source, 1))
    if not any(item["module_type"] == "ending" for item in modules): modules.append(_empty_module(f"ending-{len(modules) + 1}", "ending", "结局", "", len(modules) + 1))
    result["modules"] = modules; result["conversion"] = {"version": 3, "source_preserved": True, "module_count": len(modules), "warnings": analysis["warnings"], "analysis": analysis, "stages": ["extract", "analyze", "classify", "build_modules", "validate"]}
    return result


def build_ai_conversion_prompt(text: str, sections: list[tuple[str, str]] | None = None, source_order_start: int = 1) -> str:
    source_sections = sections or _split_sections(text)
    blocks = "\n\n".join(f"--- SOURCE_SECTION {i} ---\nTITLE: {title}\nCONTENT:\n{content}" for i, (title, content) in enumerate(source_sections, source_order_start))
    # Keep this prompt readable and explicit.  Do not keep the old, incorrectly
    # decoded prompt here: even unreachable string literals are easy to send to
    # a provider when this function is patched by an extension.
    return f"""你是 TRPG 剧本文档结构化转换器。只做忠实结构化，不续写、不改编、不补充原文没有的事实。
先判断每个 SOURCE_SECTION 的用途，再输出 module_type。opening（导入模块）仅允许用于全文最前面明确写着“导入/开场/序幕”的旁白，最多一个；“准备/游戏准备/角色创建/推荐技能”必须是 preparation，绝不能标成 opening。background 只放 KP 幕后信息；public_info 放玩家开局可知信息；timeline 只放明确时间线。
凡是玩家可以抵达、观察、调查或行动的地点、房间、物件区域或空间阶段，均为 scene：例如“房间”“光幕”“吊灯”都应作为独立 scene；标题变化就是边界。地点过多时，只有相邻且同一空间、内容很短的地点才可合并，合并后的 title 必须列出全部地点（如“房间 / 光幕 / 吊灯”），summary 必须明确说明包含哪些地点。不得把多个不相邻地点概括成一个 scene。地点内的描述、检定成功/失败、NPC、线索和战斗留在该 scene。
ending 中 True End、BAD END、Crazy End、死亡或逃生结局各自独立；npc/monster 仅在原文有独立卡片或数值时使用。
每个 SOURCE_SECTION 必须对应一个 module（允许仅合并相邻短小 scene，但不得丢失 source_order，合并时使用 source_order 数组），不得把普通场景改成 opening。检定行不是标题。不要输出 content，服务端按 source_order 保留原文。只返回合法 JSON，module 至少含 source_order、module_type、title、summary、visibility；summary 最多180字。
参考：常闇の箱的 6/7/5/4/3/2 号车厢及车头车厢分别是 scene；True End、BAD END、Crazy End 分别是 ending；《侦查》成功/失败留在所属车厢。

原文分段：
{blocks}

兼容字段说明：每个车厢、房间必须独立；不要输出 content。
"""


def _normalize_ai_module_type(local: dict[str, Any], candidate: dict[str, Any]) -> str:
    """Apply conservative, deterministic type guards after model output."""
    title = str(candidate.get("title") or local.get("title") or "").strip()
    inferred = _module_type(title)
    candidate_type = str(candidate.get("module_type") or "").casefold()
    local_type = str(local.get("module_type") or "")
    order = int(local.get("source_order") or 0)
    # Preparation headings and location headings are stronger signals than a
    # model's generic opening label.  Opening is allowed only for the first
    # source section and an explicit marker in the title.
    if inferred == "preparation":
        return "preparation"
    if inferred == "scene" and candidate_type in {"opening", "background", "public_info", "custom", ""}:
        return "scene"
    if local_type == "scene" and inferred == "background" and candidate_type in {"opening", "background", "public_info", "custom", ""}:
        return "scene"
    if candidate_type == "opening" and (order != 1 or not re.search(r"导入|开场|序幕|opening", title, re.I)):
        return inferred if inferred in {"scene", "preparation", "ending", "public_info", "timeline", "npc", "monster"} else local.get("module_type", "background")
    return candidate_type if candidate_type in {"opening", "background", "public_info", "preparation", "timeline", "scene", "ending", "npc", "monster", "custom"} else inferred


def _merge_ai_module(local: dict[str, Any], candidate: dict[str, Any]) -> None:
    candidate_type = _normalize_ai_module_type(local, candidate)
    local["module_type"] = candidate_type
    for key in ("title", "summary", "visibility", "notes", "triggers", "attributes", "battle", "skills", "weapons", "inputs", "timeline_entries", "open_ending", "fixed_opening"):
        if key in candidate and candidate[key] is not None: local[key] = candidate[key]
    if local["module_type"] == "scene": local.setdefault("scene_id", local.get("source_order"))
    if local["module_type"] == "ending": local.setdefault("ending_id", local.get("source_order"))


def convert_with_ai(requester: Callable[[dict[str, Any]], dict[str, Any]], text: str, model: str = "local-model", metadata: dict[str, Any] | None = None, *, max_sections_per_request: int = 8, max_chars_per_request: int = 24000) -> dict[str, Any]:
    sections = _split_sections(text)
    batches: list[tuple[int, list[tuple[str, str]]]] = []
    current: list[tuple[str, str]] = []
    current_chars = 0
    for index, section in enumerate(sections, 1):
        section_chars = len(section[0]) + len(section[1])
        if current and (len(current) >= max_sections_per_request or current_chars + section_chars > max_chars_per_request):
            batches.append((index - len(current), current)); current = []; current_chars = 0
        current.append(section); current_chars += section_chars
    if current: batches.append((len(sections) - len(current) + 1, current))

    from trpg_server.logging_config import redact_sensitive
    merged_candidates: dict[int, dict[str, Any]] = {}
    ai_metadata: dict[str, Any] = {}
    total_token_count = 0
    token_count_seen = False
    for source_start, batch in batches:
        payload = {"model": model, "messages": [{"role": "system", "content": "你是严格遵守原文边界的 TRPG 剧本结构化转换器。只输出合法 JSON，不创作、不合并、不丢失任何 SOURCE_SECTION。"}, {"role": "user", "content": build_ai_conversion_prompt(text, batch, source_start)}], "temperature": 0, "response_format": {"type": "json_object"}}
        logger.info("scenario_conversion.ai_request model=%s source_start=%d sections=%d chars=%d", model, source_start, len(batch), sum(len(t) + len(c) for t, c in batch))
        logger.info("scenario_conversion.ai_request_full=%s", json.dumps(redact_sensitive(payload), ensure_ascii=False, default=str))
        response = requester(payload)
        logger.info("scenario_conversion.ai_response_full=%s", json.dumps(redact_sensitive(response), ensure_ascii=False, default=str))
        try: content = response["choices"][0]["message"]["content"]; ai_payload = json.loads(content)
        except (KeyError, IndexError, TypeError, json.JSONDecodeError) as exc: logger.exception("scenario_conversion.ai_invalid_json"); raise ValueError("AI converter returned invalid JSON") from exc
        if not isinstance(ai_payload, dict) or not isinstance(ai_payload.get("modules"), list): raise ValueError("AI converter response must contain modules")
        usage = response.get("usage") if isinstance(response, dict) else None
        if isinstance(usage, dict):
            round_tokens = usage.get("total_tokens")
            if not isinstance(round_tokens, (int, float)) and isinstance(usage.get("prompt_tokens"), (int, float)) and isinstance(usage.get("completion_tokens"), (int, float)):
                round_tokens = usage["prompt_tokens"] + usage["completion_tokens"]
            if isinstance(round_tokens, (int, float)):
                total_token_count += int(round_tokens); token_count_seen = True
        ai_metadata.update({k: ai_payload[k] for k in ("title", "author", "playerCount", "notes") if k in ai_payload})
        for item in ai_payload["modules"]:
            if not isinstance(item, dict):
                continue
            source_order = item.get("source_order")
            orders = source_order if isinstance(source_order, list) else [source_order]
            for order in orders:
                if str(order).isdigit():
                    merged_candidates[int(order)] = item
    converted = convert_script_to_scenario(text, {**(metadata or {}), **ai_metadata})
    by_order = merged_candidates
    for item in converted["modules"]:
        candidate = by_order.get(int(item.get("source_order", 0)))
        if candidate: _merge_ai_module(item, candidate)
    converted["conversion"]["ai"] = {"model": model, "request_count": len(batches), "response_module_count": len(by_order), "merged_module_count": len(by_order)}
    if token_count_seen: converted["conversion"]["ai"]["total_token_count"] = total_token_count
    logger.info("scenario_conversion.ai_complete requests=%d response_modules=%d merged=%d local_modules=%d", len(batches), len(by_order), len(by_order), len(converted["modules"]))
    return converted


convert_script = convert_script_to_scenario
parse_script = convert_script_to_scenario
load_script_text = extract_script_text
