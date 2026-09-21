import pytest

from trpg_server.scenario_documents import parse_scenario_document


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
