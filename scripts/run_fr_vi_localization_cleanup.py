from pathlib import Path
import runpy

path = Path("scripts/apply_fr_vi_localization_cleanup.py")
text = path.read_text(encoding="utf-8")

old_replace = '''    replacement = rf'\\1"{escaped}"\\2'\n    new_block = pattern.sub(replacement, block, count=1)\n'''
new_replace = '''    new_block = pattern.sub(\n        lambda match: f'{match.group(1)}"{escaped}"{match.group(2)}',\n        block,\n        count=1,\n    )\n'''
replace_count = text.count(old_replace)
if replace_count != 1:
    raise RuntimeError(
        f"expected one replacement-string block, found {replace_count}"
    )
text = text.replace(old_replace, new_replace, 1)

old_return = '''text = replace_once(\n    text,\n    '    return rendered\\n',\n    '    return _localize_rendered_number_punctuation(rendered, locale)\\n',\n    'localize final rendered punctuation',\n)\n'''
new_return = '''return_marker = '    return rendered\\n'\nreturn_index = text.rfind(return_marker)\nif return_index < 0:\n    raise RuntimeError('could not locate final localized renderer return')\ntext = (\n    text[:return_index]\n    + '    return _localize_rendered_number_punctuation(rendered, locale)\\n'\n    + text[return_index + len(return_marker):]\n)\n'''
return_count = text.count(old_return)
if return_count != 1:
    raise RuntimeError(
        f"expected one obsolete final-return patch block, found {return_count}"
    )
text = text.replace(old_return, new_return, 1)

path.write_text(text, encoding="utf-8")
runpy.run_path(str(path), run_name="__main__")
