# Ask Dashboard — Localization Guide

## Supported interface locales

- English (`en`)
- Spanish (`es`)
- French (`fr`)
- Vietnamese (`vi`)
- Indonesian (`id`)

English is the canonical source for product meaning. A translation may be longer or phrased differently, but it must preserve the same metric, scope, action, and limitation.

## Current capability boundary

The interface is multilingual, but free-text Ask Dashboard routing and generated explanations are currently English-first. Do not imply full multilingual question understanding until routing and answer-generation tests exist for that language.

Use localized limitation copy near the custom-question input rather than leaving users to infer the limitation after an unsupported answer.

## Key rules

- Every locale must contain exactly the canonical English key set.
- Do not add a key to one locale only.
- Values must be non-empty strings.
- Preserve named placeholders and format fields exactly across locales.
- Keep user-supplied player names and alliance names unchanged.
- Do not embed language-specific UI control names such as “Select all” inside instructional prose unless that label is controlled and translated by this project.
- Keep Markdown and component styling outside translation values where practical.

## Canonical terminology

| Concept | Canonical English | Meaning to preserve |
|---|---|---|
| SVS | SVS | The game event name; normally keep the acronym |
| Player | Player | A player represented by one row or identity in the selected data |
| Alliance | Alliance | The player's alliance in the selected period |
| Score Gained | Score Gained | Points earned; not the same as positive net score |
| Score Lost | Score Lost | Points lost; normally displayed as a positive magnitude in source data |
| Net Score | Net Score | Score Gained minus Score Lost |
| Positive Contribution | Positive Contribution | Positive net-score impact in the selected scope |
| Negative Contribution | Negative Contribution | Negative net-score impact in the selected scope |
| Net per Player | Net per Player | Average net score for represented players in the alliance summary |
| Excluded Players | Excluded Players | Players omitted from a selected-group comparison, not deleted from data |
| SVS Rank | SVS Rank | Competition rank supplied by the dataset |

## Semantic constraints

- Never translate **Score Gained** as “positive score” or **Score Lost** as “negative score.”
- Do not turn score results into claims about a person's motives, ability, or conduct.
- When a chart uses absolute values for negative share, state that only the chart share uses magnitudes; the underlying net impact is negative.
- Keep “full server,” “filtered scope,” and “selected players” distinct.
- Preserve approximation language for periods affected by rounded in-game values.

## Content length and layout

Translation length is not a defect by itself. Do not distort meaning merely to match English width.

Components must support wrapped labels, long translations, Vietnamese diacritics, long player and alliance names, and large positive and negative values.

When a visible caption becomes long in one or more locales, first consider moving it to contextual help rather than forcing an unnatural short translation.

## Review checklist

For each new or changed user-visible string:

1. Is it Tier 1, Tier 2, or Tier 3 content as defined in `CONTENT.md`?
2. Does it add information instead of repeating the heading or label?
3. Does the English source preserve metric and scope precision?
4. Are all five locale keys present?
5. Are placeholders identical across locales?
6. Does it avoid translating names and game identifiers?
7. Does it fit narrow layouts when rendered, including wrapping?
8. Has a fluent reviewer checked naturalness where practical?

## Test policy

Automated tests should block missing or extra locale keys, missing locale dictionaries, blank values, placeholder mismatches, and duplicate locale codes.

Rendered browser or Streamlit tests should additionally inspect wrapping, overflow, truncation, and mixed-language UI states.
