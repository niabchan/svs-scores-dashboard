from pathlib import Path


script_path = Path(__file__).with_name("apply_roadmap_patch.py")
text = script_path.read_text(encoding="utf-8")

old = '''replace_once(
    usage_path,
    '    app_variant: str = "preview",\\n    timestamp_utc: Any = None,\\n',
    '    app_variant: str = "preview",\\n    app_version: str = "unknown",\\n    timestamp_utc: Any = None,\\n',
    "answer app version signature",
)
'''
new = '''replace_once(
    usage_path,
    '    total_player_count: int = 0,\\n    app_variant: str = "preview",\\n    timestamp_utc: Any = None,\\n    event_id: str | None = None,\\n) -> dict[str, Any]:\\n    """Build an append-only answer event with opt-in full-text fields."""\\n',
    '    total_player_count: int = 0,\\n    app_variant: str = "preview",\\n    app_version: str = "unknown",\\n    timestamp_utc: Any = None,\\n    event_id: str | None = None,\\n) -> dict[str, Any]:\\n    """Build an append-only answer event with opt-in full-text fields."""\\n',
    "answer app version signature",
)
'''

if text.count(old) != 1:
    raise RuntimeError(f"expected one ambiguous answer signature patch, found {text.count(old)}")
script_path.write_text(text.replace(old, new, 1), encoding="utf-8")
Path(__file__).unlink()
