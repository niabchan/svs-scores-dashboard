# Ask Dashboard — Content Design Status

## Current state

The initial content audit has been implemented through the multilingual Ask Dashboard and routing work. This file now records the v1 content decisions, remaining capability boundary, and deferred maintenance rather than treating already-resolved findings as open defects.

The dashboard is an operational multilingual analytics interface. Content changes must not alter score calculations, metric meaning, privacy semantics, or routing contracts unless that product change is explicitly intended and tested.

## Completed v1 content work

### Multilingual Ask Dashboard shell and answers

Ask Dashboard controls, privacy copy, feedback controls, suggested-question labels, and deterministic generated explanations are localized for English, Spanish, French, Vietnamese, and Indonesian.

Suggested-question backend values remain canonical English/internal values so display localization does not mutate routing or analytics contracts. Final deterministic answer rendering follows the selected dashboard locale after the structured answer has been calculated.

### Free-text capability wording

Free-text routing is no longer strictly English-only. Common tested best-player and best-contributor wording is recognized across the five interface languages, with additional multilingual contribution/grouping vocabulary and selected Thai custom-question coverage.

English still has the broadest deterministic free-text coverage. The UI and documentation must therefore avoid both extremes:

- do not claim that custom questions must be written in English;
- do not claim unrestricted multilingual natural-language understanding.

Preferred capability wording: common questions can work in several languages, while English currently has the broadest free-text coverage. Generated deterministic explanations follow the selected dashboard language.

### Responsive chart references

Player Selection Insight may place Before Exclusion and After Exclusion charts side by side or stack them on narrow screens. Copy identifies those charts by their visible names rather than by left/right or top/bottom placement.

Repeated per-chart scope remarks were removed after one shared explanation became sufficient. The chart headings remain because rendered review showed that they improve orientation.

### Translation and empty-state quality

- locale key and placeholder parity are covered by automated tests;
- literal translation-key references are checked so internal keys do not leak into the UI;
- exclusion empty states use human-readable localized copy;
- framework-owned **Select all** remains an intentional exact English UI reference inside translated ranking guidance because users must match the label Streamlit actually renders.

### Ask Dashboard answer hierarchy

Answers lead with the result and then add only the context required to interpret it. Broad player “best” questions use Net Score as the dashboard's default overall-result measure, while contribution questions remain separate and use positive net contribution. Copy must state metric choices without converting them into judgments about ability or character.

## Remaining v1 capability boundary

### Free-text understanding is tested, not universal

The deterministic router contains tested multilingual patterns but does not implement a general tokenizer or full natural-language grammar for every supported language. AI fallback can classify unfamiliar wording into the existing intent contract when enabled, but it does not calculate scores or generate final narrative answers.

For this reason, capability copy should say that English has the broadest free-text coverage rather than promising complete multilingual question understanding.

### Analytics is optional infrastructure

Usage analytics and feedback are not required for the dashboard to calculate or display answers. Persistent analytics may be disabled. Custom question and generated answer text are stored only when the user explicitly opts in for that question.

Developer/admin analytics controls are not part of the normal user experience and must remain protected when enabled.

## Content tiers

### Tier 1 — Always visible

- Page and tab names
- Filter labels
- Metric labels and values
- Chart or table title when the visual needs one
- Status, empty-state summary, and primary action
- One sentence needed to prevent a likely misinterpretation
- A concise custom-question capability note when relevant

### Tier 2 — Contextual help

- How to read a chart
- Filter-scope clarification
- Why a negative pie uses absolute values
- What excluding players changes
- Why a result may be approximate
- How to identify responsive charts when their screen position can change

Use a tooltip, concise caption, or collapsed expander near the relevant component.

### Tier 3 — Reference

- Full metric glossary
- Calculation methods
- Data limitations
- Supported and unsupported Ask Dashboard behaviour
- Privacy and analytics details
- Translation and terminology guidance

Keep this material available without placing it in the main scanning path.

## Canonical metric meanings

- **Score Gained:** points earned during the selected SVS period.
- **Score Lost:** points lost during the selected SVS period.
- **Net Score:** Score Gained minus Score Lost.
- **Positive Contribution:** positive net-score impact within the selected scope.
- **Negative Contribution:** negative net-score impact within the selected scope. Charts may use absolute values to show share, but the underlying impact remains negative.
- **Net per Player:** alliance total net score divided by the number of included players represented in that summary.
- **Excluded Player:** a player removed from the selected-group comparison, not removed from the source data.

## Copy patterns

Prefer:

> Compare average net score per player across alliances.

Instead of:

> This section shows a chart that allows you to compare the average net score per player across the alliances based on the current sidebar filters.

Prefer:

> Negative share uses absolute values so alliance shares can be compared.

Instead of repeating separate explanations above and below the same chart.

Prefer:

> The Before Exclusion chart shows all players in the current filter scope. The After Exclusion chart shows only the players currently selected for analysis.

Instead of referring to the same charts as left/right or top/bottom.

For empty states, describe the actual condition that prevents a visual from rendering rather than exposing an internal key or claiming broadly that no data exists. For the exclusion pie charts, distinguish the current filter scope from the currently selected players.

## Deferred maintenance after v1

These are not release blockers:

- move the main locale dictionaries out of `app.py` when a larger localization refactor is justified;
- move remaining Markdown presentation syntax out of translation values;
- refactor the compatibility package around the historical root `ask_dashboard.py` only with dedicated regression coverage;
- consider Thai word tokenization only if future characterization tests demonstrate segmentation-specific failures;
- continue natural-language coverage based on real questions and feedback rather than expanding phrase lists speculatively.

## Close-out maintenance rule

After v1, prefer data updates, bug fixes, dependency/security maintenance, and evidence-based routing additions over broad feature expansion. A new feature should solve a demonstrated user problem rather than keep the project permanently “almost finished.”
