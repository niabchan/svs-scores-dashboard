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

- Do not repeat a tab label immediately as an identical subheader.
- Prefer one meaningful heading over a heading, subtitle, caption, and reading guide that restate each other.
- Keep filters together and make their scope explicit without repeatedly describing the same scope below every chart.
- Keep exact data tables available even when charts or summaries are present.
- Use progressive disclosure for explanations that returning users no longer need.
- Avoid nested containers and card-like decoration unless they communicate grouping or state.

## Copy rules

- Lead with the user's task or the result, not with “This section shows…”.
- A visible caption should normally be one sentence.
- Tooltips add information that the label cannot hold; they must not repeat the label.
- Empty and error states should say what happened and what the user can do next.
- Preserve the distinction among Score Gained, Score Lost, Net Score, Positive Contribution, and Negative Contribution.
- Do not use copy that implies intent, blame, skill, or behaviour from score data.

## Multilingual resilience

- Design for the longest supported translation, not only English.
- Allow controls and headings to wrap without obscuring adjacent values.
- Never use fixed widths that only fit English labels.
- Test long player and alliance names, large negative numbers, empty states, and narrow screens.
- Keep presentation markup out of translation values where practical; the component should decide whether text is a heading or bold label.

## Visual review sequence

When Impeccable or another design reviewer is available, review the rendered Streamlit app in this order:

1. `critique` — hierarchy, cognitive load, repetition, and scanability; report only.
2. `distill` — identify what can be removed, combined, or moved behind disclosure.
3. `clarify` — revise labels, captions, tooltips, empty states, and action copy.
4. `harden` — test every locale, long names, extreme values, and narrow viewports.
5. `polish` — only after the content architecture is stable.

Do not let a visual-review tool alter metric definitions, calculations, routing behaviour, privacy meaning, or data limitations without an explicit product decision.

## Current design risks

- The main translation dictionary and presentation logic are coupled in `app.py`.
- Several tabs repeat their tab name as a subheader.
- Contribution views use overlapping captions and reading guides.
- Ask Dashboard controls, privacy copy, feedback controls, suggested questions, and generated explanations are currently English-first inside a multilingual shell.
- Some translation values contain Markdown heading or bold syntax, coupling content to presentation.
