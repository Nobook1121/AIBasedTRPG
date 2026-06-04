from pathlib import Path


def safe_join(base, *parts):
    base_path = Path(base).resolve()
    target_path = base_path.joinpath(*parts).resolve()

    try:
        target_path.relative_to(base_path)
    except ValueError as exc:
        raise ValueError("Unsafe path") from exc

    return target_path


def is_allowed_upload(filename, allowed_extensions):
    suffix = Path(filename).suffix
    if not suffix:
        return False

    suffix = suffix.lower().lstrip(".")
    return suffix in {extension.lower().lstrip(".") for extension in allowed_extensions}
