import pytest

from trpg_server.scenario_documents import chunk_parsed_document, parse_scenario_document


def test_pdf_document_is_parsed_when_pymupdf_is_installed():
    fitz = pytest.importorskip("pymupdf")
    document = fitz.open()
    page = document.new_page()
    page.insert_text((72, 72), "PDF scenario rules")
    raw = document.tobytes()
    document.close()

    parsed = parse_scenario_document(raw, "scenario.pdf")

    assert "PDF scenario rules" in parsed.markdown
    assert parsed.page_count == 1


def test_chunk_parsed_document_tags_chapter_path_for_split_sections():
    # 同一章节被 target_max 拆成多个子块时，它们应共享同一个 chapter_path，
    # 以便检索命中后按章节回填上下文。
    markdown = (
        "# 第一章 图书馆\n\n"
        + ("图书馆里藏着线索。\n\n" * 30)
        + "# 第二章 花园\n\n"
        + ("花园里也藏着线索。\n\n" * 30)
    )
    parsed = parse_scenario_document(markdown.encode("utf-8"), "scenario.md")

    chunks = chunk_parsed_document(parsed, target_max=200)

    assert len(chunks) >= 3
    first_chapter = [chunk for chunk in chunks if chunk.chapter_path == ["第一章 图书馆"]]
    second_chapter = [chunk for chunk in chunks if chunk.chapter_path == ["第二章 花园"]]
    assert len(first_chapter) >= 2
    assert len(second_chapter) >= 1
    # 续块保留章节归属，并补上「【章节】」前缀作为语境。
    assert first_chapter[1].text.startswith("【第一章 图书馆】")
