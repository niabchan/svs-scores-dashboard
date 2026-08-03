from pathlib import Path

ASK_PATH = Path("ask_dashboard.py")
TEST_PATH = Path("test_ask_dashboard.py")

ask = ASK_PATH.read_text(encoding="utf-8")

old_helpers_anchor = '''def _has_net_score_context(text):
    """Return True for standalone net-score wording without matching internet/planet."""
    return bool(
        re.search(r"(?<!\\w)net(?![\\w-])", text)
        or re.search(r"(?<!\\w)net[\\s-]+score(?:-\\w+)*(?!\\w)", text)
    )


def format_score(value):
'''

new_helpers_anchor = '''def _has_net_score_context(text):
    """Return True for standalone net-score wording without matching internet/planet."""
    return bool(
        re.search(r"(?<!\\w)net(?![\\w-])", text)
        or re.search(r"(?<!\\w)net[\\s-]+score(?:-\\w+)*(?!\\w)", text)
    )


def _is_dashboard_help_request(text):
    """Recognize explicit and natural-language requests for dashboard guidance."""
    if re.match(r"^help(?:\\s|$)", text):
        return True
    help_patterns = (
        r"how (?:do i|can i|to) use (?:the |this |ask )?dashboard",
        r"how does (?:the |this |ask )?dashboard work",
        r"what can i ask (?:the |this |ask )?dashboard",
        r"what questions can i ask",
        r"what can (?:the |this |ask )?dashboard do",
        r"show me how to use (?:the |this |ask )?dashboard",
    )
    return any(re.fullmatch(pattern, text) for pattern in help_patterns)


def _is_strong_human_inference_request(text):
    """Return True when wording explicitly asks for unsupported human inference."""
    strong_patterns = (
        r"\\b(reckless|careless|selfish|malicious|unskilled)\\b",
        r"\\b(?:good|bad)\\s+(?:svs\\s+)?player\\b",
        r"\\bplay(?:ed|ing)?\\s+badly\\b",
        r"\\bbehaviou?r\\b|\\bbehav(?:ed|ing)\\b",
        r"\\bintend(?:s|ed|ing)?\\b|\\bintent(?:ions?|ional(?:ly)?)?\\b",
        r"\\bdeliberate(?:ly)?\\b|\\bon\\s+purpose\\b",
        r"\\b(motive|motives|character)\\b",
        r"\\b(?:responsible|responsibility|to\\s+blame|whose\\s+fault|at\\s+fault)\\b",
        r"\\b(?:made|make|making)\\s+(?:a\\s+)?mistake\\b",
        r"\\bignore(?:d|s|ing)?\\s+orders?\\b",
        r"\\b(?:know|knew)\\b.*\\b(?:would|could)\\b.*\\bhappen\\b",
        r"\\b(?:try|tries|tried|trying)\\s+to\\s+(?:lose|feed|help|hurt|win|score|zero|cause|ignore)\\b",
        r"\\b(?:want|wants|wanted|mean|means|meant)\\s+to\\s+(?:lose|feed|help|hurt|win|score|zero|cause|ignore)\\b",
        r"\\bwhat\\s+kind\\s+of\\s+player\\b",
    )
    return any(re.search(pattern, text) for pattern in strong_patterns)


def _is_contextual_human_inference_request(text):
    """Recognize indirect motive or behavior questions after score routing fails."""
    contextual_patterns = (
        r"\\bwhy\\s+(?:did|does)\\b.+\\b(?:do\\s+(?:this|that)|keep\\s+|act(?:s|ed|ing)?\\b|play(?:s|ed|ing)?\\b)",
        r"\\bwhy\\s+(?:was|is)\\b.+\\b(?:trying|acting|playing)\\b",
        r"\\b(?:dashboard|scores?|data|results?)\\b.*\\b(?:show|tell|infer|determine|prove|indicate|suggest|judge|conclude|know|explain)\\b.*\\b(?:behaviou?r|intent(?:ion)?|motive|purpose|responsib|blame|fault|mistake|careless|reckless|why)\\w*\\b",
        r"\\bcan\\b.*\\b(?:tell|infer|determine|prove|judge|conclude)\\b.*\\b(?:someone|somebody|they|he|she|person|player)\\b",
        r"\\bunseen\\s+(?:gameplay|circumstances?|context)\\b",
    )
    return any(re.search(pattern, text) for pattern in contextual_patterns)


def format_score(value):
'''

if old_helpers_anchor not in ask:
    raise SystemExit("helper insertion anchor not found")
ask = ask.replace(old_helpers_anchor, new_helpers_anchor, 1)

old_pre_routing = '''    # Help is deliberately a standalone, first-word command so that words such
    # as "helpful" cannot accidentally take over an analytical question.
    if re.match(r"^help(?:\\s|$)", normalized_question):
        return _intent_contract("dashboard_help")

    # Strong, explicit human-judgment signals take precedence over analytical
    # routing. These terms directly ask for qualities that scores cannot prove.
    strong_limitation_patterns = (
        r"\\b(reckless|careless|selfish|malicious|skilled|unskilled|responsible)\\b",
        r"\\bbad\\s+(?:svs\\s+)?player\\b",
        r"\\bbehaviou?r\\b|\\bbehav(?:ed|ing)\\b",
        r"\\bintend(?:s|ed|ing)?\\b|\\bintent(?:ions?|ional(?:ly)?)?\\b",
        r"\\bdeliberate(?:ly)?\\b|\\bon\\s+purpose\\b",
        r"\\b(motive|motives|character|strategy)\\b",
        r"\\bmean\\s+to\\b|\\btrying\\s+to\\s+help\\b|\\bprove\\b.*\\bignored?\\b",
    )
    if any(re.search(pattern, normalized_question) for pattern in strong_limitation_patterns):
        return _intent_contract("dashboard_limitation")
'''

new_pre_routing = '''    if _is_dashboard_help_request(normalized_question):
        return _intent_contract("dashboard_help")

    # Explicit human-judgment requests take precedence because no supported
    # score analysis can establish these qualities from the available data.
    if _is_strong_human_inference_request(normalized_question):
        return _intent_contract("dashboard_limitation")
'''

if old_pre_routing not in ask:
    raise SystemExit("pre-routing block not found")
ask = ask.replace(old_pre_routing, new_pre_routing, 1)

old_contextual = '''    # Contextual inference wording is checked only after every supported score
    # analysis. This preserves requests to explain score mathematics while
    # still preventing ambiguous human-inference questions from reaching AI.
    contextual_limitation_patterns = (
        r"\\b(?:scores?|dashboard)\\b.*\\b(?:show|tell|determine|prove)\\b.*\\bwhy\\b.*\\bplayer\\b",
        r"\\bwhy\\s+(?:did|does)\\b.*\\bplayer\\b.*\\b(?:do|keep|act(?:s|ed|ing)?|play(?:s|ed|ing)?)\\b",
        r"\\bwhy\\b.*\\bplayer\\b.*\\b(?:did|does|acted|played)\\b",
        r"\\bunseen\\s+(?:gameplay|circumstances?|context)\\b",
    )
    if any(re.search(pattern, normalized_question) for pattern in contextual_limitation_patterns):
        return _intent_contract("dashboard_limitation")
'''

new_contextual = '''    # Indirect human-inference wording is checked only after every supported
    # score analysis. It intentionally does not depend on knowing the subject's
    # player or alliance name.
    if _is_contextual_human_inference_request(normalized_question):
        return _intent_contract("dashboard_limitation")
'''

if old_contextual not in ask:
    raise SystemExit("contextual block not found")
ask = ask.replace(old_contextual, new_contextual, 1)
ASK_PATH.write_text(ask, encoding="utf-8")

tests = TEST_PATH.read_text(encoding="utf-8")
addition = r'''

@pytest.mark.parametrize("question", [
    "How to use dashboard",
    "How to use the dashboard",
    "How do I use the dashboard?",
    "How can I use this dashboard?",
    "How does Ask Dashboard work?",
    "What can I ask the dashboard?",
    "What questions can I ask?",
    "What can this dashboard do?",
    "Show me how to use the dashboard",
])
def test_natural_help_requests_are_rule_first(question):
    hybrid = __import__("ask_dashboard").route_dashboard_question_hybrid(
        question,
        ["AAA"],
        ai_enabled=True,
        ai_extractor=lambda *_: pytest.fail("AI fallback called"),
    )
    assert hybrid["contract"]["intent"] == "dashboard_help"
    assert hybrid["contract"]["source"] == "rule"
    assert hybrid["ai_attempted"] is False

    answer = execute_dashboard_intent(hybrid["contract"], sample_data(), "2026-W29")
    rendered = render_dashboard_answer(answer)
    assert "How to use Ask Dashboard" in rendered
    assert "I could not map that question" not in rendered
    assert "Data note:" not in rendered


@pytest.mark.parametrize("question", [
    "Why did T do this?",
    "Why does Ministry keep losing points?",
    "Was SnS trying to lose points?",
    "Is A1 responsible for the loss?",
    "Was A1 playing badly?",
    "Did they ignore orders?",
    "Who is to blame?",
    "Was this A1's fault?",
    "What kind of player is A1?",
    "Can the dashboard tell whether A1 made a mistake?",
    "Can these scores show whether someone made a mistake?",
    "Does this prove A1 ignored orders?",
])
def test_human_inference_routing_does_not_require_known_names(question):
    hybrid = __import__("ask_dashboard").route_dashboard_question_hybrid(
        question,
        ["AAA"],
        ai_enabled=True,
        ai_extractor=lambda *_: pytest.fail("AI fallback called"),
    )
    assert hybrid["contract"]["intent"] == "dashboard_limitation"
    assert hybrid["contract"]["source"] == "rule"
    assert hybrid["ai_attempted"] is False

    answer = execute_dashboard_intent(hybrid["contract"], sample_data(), "2027-W01")
    rendered = render_dashboard_answer(answer)
    assert "cannot determine" in rendered
    assert "I could not map that question" not in rendered
    assert "Data note:" not in rendered


@pytest.mark.parametrize(("question", "intent"), [
    ("Why did the negative percentage increase?", "negative_share_change"),
    ("Can the dashboard show why the negative percentage increased?", "negative_share_change"),
    ("Why does the top net-score alliance rank second in positive contribution?", "net_vs_positive_ranking"),
    ("Why did Player A have the highest net score?", "player_net_score_leader"),
    ("Who contributed most in SnS?", "top_contributors"),
])
def test_concept_based_limitation_preserves_supported_analytics(question, intent):
    hybrid = __import__("ask_dashboard").route_dashboard_question_hybrid(
        question,
        ["SnS", "AAA", "BBB"],
        ai_enabled=True,
        ai_extractor=lambda *_: pytest.fail("AI fallback called"),
    )
    assert hybrid["contract"]["intent"] == intent
    assert hybrid["ai_attempted"] is False
'''

if "def test_natural_help_requests_are_rule_first" in tests:
    raise SystemExit("tests already patched")
TEST_PATH.write_text(tests + addition, encoding="utf-8")
