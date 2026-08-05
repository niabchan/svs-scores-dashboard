from pathlib import Path


script_path = Path(__file__).with_name("apply_roadmap_patch.py")
text = script_path.read_text(encoding="utf-8")

workflow_block = '''# CI compiles the new tests.
replace_once(
    workflow_path,
    'usage_analytics.py test_ask_dashboard.py test_data_loading.py test_usage_analytics.py\\n',
    'usage_analytics.py test_ask_dashboard.py test_alliance_score_overview.py test_data_loading.py test_usage_analytics.py\\n',
    "CI compile list",
)

'''
if text.count(workflow_block) != 1:
    raise RuntimeError(
        f"expected one workflow patch block, found {text.count(workflow_block)}"
    )
text = text.replace(
    workflow_block,
    "# The final CI workflow is updated separately through the repository connector.\n\n",
    1,
)

workflow_delete = "self_workflow_path.unlink(missing_ok=True)\n"
if text.count(workflow_delete) != 1:
    raise RuntimeError(
        f"expected one workflow deletion, found {text.count(workflow_delete)}"
    )
text = text.replace(
    workflow_delete,
    "# Workflow files are removed separately because the Actions token cannot modify them.\n",
    1,
)

script_path.write_text(text, encoding="utf-8")
Path(__file__).unlink()
