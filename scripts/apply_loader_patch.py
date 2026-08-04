from pathlib import Path


APP_PATH = Path("app.py")
WORKFLOW_PATH = Path(".github/workflows/apply-loader-patch.yml")
SCRIPT_PATH = Path(__file__)


text = APP_PATH.read_text(encoding="utf-8")

old_import = "import re\n"
new_import = "import re\n\nfrom data_loading import coerce_numeric_columns\n"
if "from data_loading import coerce_numeric_columns" not in text:
    if text.count(old_import) != 1:
        raise RuntimeError("Expected exactly one app.py import anchor")
    text = text.replace(old_import, new_import, 1)

old_loader = '''    for col in score_columns:
        df[col] = (
            df[col]
            .astype(str)
            .str.replace(",", "", regex=False)
            .str.strip()
        )
        df[col] = pd.to_numeric(df[col], errors="coerce")

    return df
'''
new_loader = '''    # Remove separators and all whitespace inside numeric fields before
    # coercion. This preserves signed values such as "- 546,738,937".
    return coerce_numeric_columns(df, score_columns)
'''
if old_loader in text:
    text = text.replace(old_loader, new_loader, 1)
elif new_loader not in text:
    raise RuntimeError("Expected loader block was not found in app.py")

APP_PATH.write_text(text, encoding="utf-8")

# Keep the branch clean: this workflow and script exist only to apply the
# narrow patch through GitHub Actions.
WORKFLOW_PATH.unlink(missing_ok=True)
SCRIPT_PATH.unlink(missing_ok=True)
