from pathlib import Path

# One-time exact patch for the English top-contributor Markdown spacing.


def replace_once(text, old, new, label):
    count = text.count(old)
    if count != 1:
        raise RuntimeError(f"{label}: expected one match, found {count}")
    return text.replace(old, new, 1)


path = Path("ask_dashboard.py")
text = path.read_text(encoding="utf-8")
old = '''        if group.get("positive_total", 0) > 0:\n            ranked_total = sum(row["net_score"] for row in group.get("players", []) if row["net_score"] > 0)\n            lines.append(f"The listed player(s) account for **{ranked_total / group['positive_total'] * 100:.1f}%** of this alliance's positive contribution in the current filter scope.")\n        lines.append(f"Alliance total net score in this scope: **{format_signed_score(group['net_total'])}**.")\n'''
new = '''        if group.get("positive_total", 0) > 0:\n            ranked_total = sum(row["net_score"] for row in group.get("players", []) if row["net_score"] > 0)\n            lines.append("")\n            lines.append(f"The listed player(s) account for **{ranked_total / group['positive_total'] * 100:.1f}%** of this alliance's positive contribution in the current filter scope.")\n        lines.append("")\n        lines.append(f"Alliance total net score in this scope: **{format_signed_score(group['net_total'])}**.")\n'''
text = replace_once(text, old, new, "English top-contributor summary spacing")
path.write_text(text, encoding="utf-8")

path = Path("test_answer_i18n.py")
text = path.read_text(encoding="utf-8")
if "def test_english_top_contributor_group_summary_spacing" in text:
    raise RuntimeError("English spacing regression test already exists")
append = r'''

def test_english_top_contributor_group_summary_spacing():
    answer = {
        "intent": "top_contributors",
        "status": "ok",
        "period": None,
        "parameters": {},
        "metrics": {"mode": "ranking", "top_n": 2},
        "rankings": {
            "alliances": [
                {
                    "alliance": "MBV",
                    "positive_total": 2000,
                    "net_total": -300,
                    "players": [
                        {
                            "player_name": "Alpha",
                            "net_score": 1200,
                            "score_gained": 1500,
                            "score_lost": 300,
                            "share_of_positive": 60.0,
                        },
                        {
                            "player_name": "Beta",
                            "net_score": 800,
                            "score_gained": 1000,
                            "score_lost": 200,
                            "share_of_positive": 40.0,
                        },
                    ],
                }
            ]
        },
    }
    rendered = render_dashboard_answer(answer, locale="en")
    assert "\n\nThe listed player(s) account for **100.0%**" in rendered
    assert "\n\nAlliance total net score in this scope: **-300**." in rendered
'''
text = text.rstrip() + "\n\n" + append.strip() + "\n"
path.write_text(text, encoding="utf-8")
