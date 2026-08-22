# SVS Scores Dashboard — Design Context

## Design mode

This is an operational analytics interface. Optimise for scanning, comparison, comprehension, and confidence rather than visual novelty.

## Information hierarchy

Use three content layers:

1. **Always visible:** page or section title, control label, metric label, status, and at most one short sentence needed to interpret the view.
2. **Contextual help:** tooltip, help icon, short caption, or collapsed expander that answers a likely question at the point of use.
3. **Reference:** glossary, calculation method, data limitations, examples, privacy details, and extended guidance.

Do not show all three layers at once unless the user is in a dedicated help or reference view.

## Layout rules

- Repeated wording can serve different structural roles. Keep a tab label and matching in-page heading when the heading materially improves orientation in a long dashboard view.
- Prefer one meaningful heading over a heading, subtitle, caption, and reading guide that restate each other.
- Keep filters together and make their scope explicit without repeatedly describing the same scope below every chart.
- Keep exact data tables available even when charts or summaries are present.
- Use progressive disclosure for explanations that returning users no longer need.
- Avoid nested containers and card-like decoration unless they communicate grouping or state.
- Do not identify responsive components by screen position such as “left”, “right”, “above”, or “below” when their position can change across viewport sizes. Refer to charts and controls by their visible names instead.

## Copy rules

- Lead with the user's task or the result, not with “This section shows…”.
- A visible caption should normally be one sentence.
- Tooltips add information that the label cannot hold; they must not repeat the label.
- Empty and error states should say what happened and what the user can do next.
- Preserve the distinction among Score Gained, Score Lost, Net Score, Positive Contribution, and Negative Contribution.
- Do not use copy that implies intent, blame, skill, or behaviour from score data.
- Capability copy must distinguish interface language, rendered-answer language, and free-text routing coverage.

## Multilingual resilience

- The supported interface locales are English, Spanish, French, Vietnamese, and Indonesian.
- Design for the longest supported translation, not only English.
- Allow controls and headings to wrap without obscuring adjacent values.
- Never use fixed widths that only fit English labels.
- Test long player and alliance names, large negative numbers, empty states, and narrow screens.
- Keep presentation markup out of translation values where practical; the component should decide whether text is a heading or bold label.
- Generated deterministic answers should follow the selected UI locale without translating player or alliance names.
- Do not imply unrestricted multilingual free-text support. English has the broadest deterministic routing coverage; common tested patterns also exist in the other supported languages, plus selected Thai custom-question wording.

## Ask Dashboard interaction model

Ask Dashboard should feel like a deterministic analytics feature with a language-understanding assist, not like an unconstrained chatbot.

- Run deterministic rules first.
- Use AI fallback only when enabled and local routing does not confidently handle the wording.
- Keep calculation and final rendering in Python.
- Show direct results before explanatory context.
- Preserve the current scope visibly enough that the answer can be interpreted without guessing which filters were active.
- Keep privacy and analytics controls understandable without exposing developer infrastructure in the normal interaction path.

## Visual review sequence

When Impeccable or another design reviewer is available, review the rendered Streamlit app in this order:

1. `critique` — hierarchy, cognitive load, repetition, and scanability; report only.
2. `distill` — identify what can be removed, combined, or moved behind disclosure.
3. `clarify` — revise labels, captions, tooltips, empty states, and action copy.
4. `harden` — test every locale, long names, extreme values, and narrow viewports.
5. `polish` — only after the content architecture is stable.

Do not let a visual-review tool alter metric definitions, calculations, routing behaviour, privacy meaning, or data limitations without an explicit product decision.

## Closed v1 design decisions

- Ask Dashboard shell, privacy copy, feedback controls, suggested-question labels, and deterministic generated explanations are localized for all five supported interface locales.
- Before Exclusion / After Exclusion guidance identifies charts by visible names rather than left/right placement.
- Matching tab and in-page headings are intentionally retained where rendered review showed that they improve orientation.
- Repeated per-chart scope remarks under the exclusion charts were removed after the shared section explanation made them redundant.
- Dense alliance-summary table labels may be shorter than canonical terminology when header help preserves the full metric meaning.

## Deferred maintenance, not v1 blockers

- The main `TEXT` dictionary remains coupled to presentation logic in `app.py`.
- Some translation values still contain Markdown heading or bold syntax.
- `ask_dashboard/` remains a compatibility layer around the historical root-level `ask_dashboard.py`; a larger direct refactor can be considered only if future maintenance justifies the regression risk.
- A dedicated Thai tokenizer such as PyThaiNLP is not required by the routing failures observed so far. Reconsider it only if future tests identify genuine word-segmentation failures rather than Unicode-normalization or vocabulary gaps.
