# Ask Dashboard — Localization Guide

## Supported interface locales

- English (`en`)
- Spanish (`es`)
- French (`fr`)
- Vietnamese (`vi`)
- Indonesian (`id`)

English is the canonical source for product meaning. A translation may be longer or phrased differently, but it must preserve the same metric, scope, action, and limitation.

## Current capability boundary

The interface and deterministic Ask Dashboard explanations support English, Spanish, French, Vietnamese, and Indonesian. Final answer rendering follows the selected dashboard UI locale after the structured answer has been calculated.

Free-text question routing remains English-first, so custom questions currently work best when entered in English. Suggested questions keep their canonical English/internal values for routing and are localized only for display. Do not imply full multilingual question understanding until routing tests exist for those languages.

Localized answer rendering is a presentation layer only: it does not send score rows, player names, alliance names, rankings, or calculated values to a translation model. Player and alliance names remain unchanged, and metric meanings and scope boundaries must match the English canonical answer.

Keep localized limitation copy near the custom-question input so users understand this distinction before submitting a free-text question.

## Key rules

- Every locale must contain exactly the canonical English key set.
- Do not add a key to one locale only.
- Values must be non-empty strings.
- Preserve named placeholders and format fields exactly across locales.
- Keep user-supplied player names and alliance names unchanged.
- When a framework-generated control label cannot be localized, preserve the exact label the user will see and translate the surrounding instruction.
- Document every framework-owned label exception so it is not mistaken for accidental language leakage.
- Keep Markdown and component styling outside translation values where practical.

## Framework-owned label exception

The alliance multiselect exposes a Streamlit-generated option labelled **Select all**. The project cannot currently localize that option. Ranking guidance therefore keeps the literal English label in every locale so users can identify the correct control and switch to a server-wide ranking.

For this exception:

- keep **Select all** unchanged;
- translate the rest of the instruction naturally;
- use consistent emphasis to show that it is an exact UI label;
- keep the guidance near the ranking interaction;
- revisit it only if the control later becomes localizable or is replaced.

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
7. Is any untranslated UI term a documented exact control label rather than accidental leakage?
8. Does it fit narrow layouts when rendered, including wrapping?
9. Has a fluent reviewer checked naturalness where practical?

## Test policy

Automated tests should block missing or extra locale keys, missing locale dictionaries, blank values, placeholder mismatches, and duplicate locale codes.

Automated checks should not reject a documented exact framework label such as **Select all** merely because it remains English inside translated guidance.

Rendered browser or Streamlit tests should additionally inspect wrapping, overflow, truncation, and mixed-language UI states.
