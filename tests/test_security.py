import pytest

from trpg_server.security import is_allowed_upload, safe_join


def test_safe_join_allows_child_path(tmp_path):
    result = safe_join(tmp_path, "covers", "cover.png")

    assert result == tmp_path / "covers" / "cover.png"


def test_safe_join_rejects_parent_escape(tmp_path):
    with pytest.raises(ValueError, match="Unsafe path"):
        safe_join(tmp_path, "..", "users.json")


def test_safe_join_rejects_absolute_path_outside_base(tmp_path):
    base = tmp_path / "base"
    outside = tmp_path / "outside" / "file.txt"

    with pytest.raises(ValueError, match="Unsafe path"):
        safe_join(base, outside)


def test_safe_join_rejects_sibling_prefix_escape(tmp_path):
    base = tmp_path / "base"
    outside = tmp_path / "base_evil" / "file.txt"

    with pytest.raises(ValueError, match="Unsafe path"):
        safe_join(base, outside)


def test_is_allowed_upload_checks_extension_case_insensitively():
    assert is_allowed_upload("cover.PNG", {"png", "jpg"})
    assert not is_allowed_upload("cover.exe", {"png", "jpg"})


def test_is_allowed_upload_allows_allowed_extension_with_leading_dot():
    assert is_allowed_upload("cover.PNG", {".png"})


def test_is_allowed_upload_rejects_missing_extension_even_if_allowed_set_contains_empty_value():
    assert not is_allowed_upload("README", {""})
    assert not is_allowed_upload("README", {"."})


def test_is_allowed_upload_rejects_hidden_file_without_regular_extension():
    assert not is_allowed_upload(".env", {"env"})
