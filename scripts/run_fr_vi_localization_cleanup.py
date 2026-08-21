from pathlib import Path
import runpy

path = Path("scripts/apply_fr_vi_localization_cleanup.py")
text = path.read_text(encoding="utf-8")
old = '''text = replace_once(\n    text,\n    '    return rendered\\n',\n    '    return _localize_rendered_number_punctuation(rendered, locale)\\n',\n    'localize final rendered punctuation',\n)\n'''
new = '''render_tail = ''' + '"""' + '''    if _show_notice(answer):\n        rendered += "\\n\\n---\\n\\n" + _t(locale, "rounded_notice")\n    return rendered\n''' + '"""' + '''\nlocalized_tail = ''' + '"""' + '''    if _show_notice(answer):\n        rendered += "\\n\\n---\\n\\n" + _t(locale, "rounded_notice")\n    return _localize_rendered_number_punctuation(rendered, locale)\n''' + '"""' + '''\ntext = replace_once(\n    text,\n    render_tail,\n    localized_tail,\n    'localize final rendered punctuation',\n)\n'''
count = text.count(old)
if count != 1:
    raise RuntimeError(f"expected one obsolete final-return patch block, found {count}")
path.write_text(text.replace(old, new, 1), encoding="utf-8")
runpy.run_path(str(path), run_name="__main__")
