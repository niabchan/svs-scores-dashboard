"""Backward-compatible Ask Dashboard API with improved contribution routing.

The original project keeps its implementation in ``ask_dashboard.py``. Python
prefers this package when both are present, so we can load and re-export the
stable implementation while isolating the new contribution behavior in small,
reviewable modules.
"""

from ._legacy import legacy

for _name in dir(legacy):
    if not _name.startswith("__"):
        globals()[_name] = getattr(legacy, _name)

from ._routing import (  # noqa: E402,F401
    ALLIANCE_POSITIVE_CONTRIBUTION_INTENT,
    ANALYSIS_SCOPES,
    CONTRIBUTOR_MODES,
    QUESTION_TOP_CONTRIBUTOR,
    QUESTION_TOP_CONTRIBUTORS,
    SCORE_DERIVED_INTENTS,
    SUGGESTED_QUESTIONS,
    SUPPORTED_DASHBOARD_INTENTS,
    route_dashboard_question,
    validate_intent_contract,
)
from ._calculation import (  # noqa: E402,F401
    calculate_alliance_positive_contribution_leader,
    calculate_dashboard_answer,
    calculate_player_positive_contribution_leader,
    calculate_top_contributors,
    execute_dashboard_intent,
    route_dashboard_question_hybrid,
)
from ._rendering import (  # noqa: E402,F401
    answer_dashboard_question,
    render_dashboard_answer,
)
