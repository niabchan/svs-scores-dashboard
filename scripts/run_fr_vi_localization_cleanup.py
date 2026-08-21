from pathlib import Path
import runpy

path = Path("scripts/apply_fr_vi_localization_cleanup.py")
text = path.read_text(encoding="utf-8")
old = '''text = replace_once(\n    text,\n    '    return rendered\\n',\n    '    return _localize_rendered_number_punctuation(rendered, locale)\\n',\n    'localize final rendered punctuation',\n)\n'''
new = '''return_marker = '    return rendered\\n'\nreturn_index = text.rfind(return_marker)\nif return_index < 0:\n    raise RuntimeError('could not locate final localized renderer return')\ntext = (\n    text[:return_index]\n    + '    return _localize_rendered_number_punctuation(rendered, locale)\\n'\n    + text[return_index + len(return_marker):]\n)\n'''
count = text.count(old)
if count != 1:
    raise RuntimeError(f"expected one obsolete final-return patch block, found {count}")
path.write_text(text.replace(old, new, 1), encoding="utf-8")
runpy.run_path(str(path), run_name="__main__")
