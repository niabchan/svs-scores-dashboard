# Ask Dashboard — Content Design Audit

## Scope of this first pass

This audit reviews the current `ask-dashboard-wip` interface as an operational multilingual dashboard. It does not change calculations, question routing, analytics collection, or metric meaning.

## Priority findings

### P0 — Multilingual shell, English Ask Dashboard

The main dashboard supports English, Spanish, French, Vietnamese, and Indonesian, but the Ask Dashboard dialog still contains hard-coded English controls, privacy text, feedback controls, suggested questions, and explanation headings. Generated answers are also English-first.

This creates a false expectation that changing the UI language changes the complete experience. Until multilingual questions and answers are supported, the interface should state the language limitation clearly in every locale.

### P1 — Repeated explanation competes with the data

Several views repeat the same idea across a tab label, matching subheader, caption, chart heading, and reading guide. The Contribution and Player Selection views are the clearest examples.

Recommended treatment:

- Keep one task-oriented heading.
- Keep one short visible sentence only when interpretation is not obvious.
- Move instructions, examples, and calculation details into a collapsed help expander.
- Avoid repeating “current sidebar filters” under every chart; explain scope once and show exceptions locally.

### P1 — Translation content and Streamlit presentation are coupled

The `TEXT` dictionary is embedded in `app.py`, while many new Ask Dashboard strings bypass it entirely. This makes key parity, review, translation, and reuse harder.

Recommended treatment:

- Move locale dictionaries into a dedicated module or structured locale files in a later refactor.
- Route every user-visible string through one translation function.
- Keep canonical English text as the source of meaning.
- Add automated key and placeholder checks before moving files.

### P1 — A translated sentence contains an English UI instruction

The Spanish ranking guide refers to the Streamlit control text **Select all** in English. Similar embedded control names should be audited in every locale. Control instructions should either use a localized label or avoid quoting framework-generated text that cannot be translated reliably.

### P2 — Presentation markup lives inside translations

Some values include `###` or `**`. This forces translators to preserve Markdown syntax and makes it harder to change heading level without editing every locale.

Recommended treatment: store plain text in translations and apply `st.subheader`, `st.markdown`, or other presentation in code.

### P2 — Privacy copy is important but long

The analytics and privacy explanation is correctly placed in a collapsed expander, but it remains English-only. Preserve its meaning and opt-in details; localize it rather than shortening it aggressively.

### P2 — Free-text language capability is not explicit

The rule-based question router is built around English terms. The current language selector can therefore imply support that the free-text router does not yet provide.

Recommended treatment: separate **interface language** from **question language support** in the copy until multilingual routing is implemented and tested.

## Content tiers

### Tier 1 — Always visible

- Page and tab names
- Filter labels
- Metric labels and values
- Chart or table title when the visual needs one
- Status, empty-state summary, and primary action
- One sentence needed to prevent a likely misinterpretation

### Tier 2 — Contextual help

- How to read a chart
- Filter-scope clarification
- Why a negative pie uses absolute values
- What excluding players changes
- Why a result may be approximate

Use a tooltip, concise caption, or collapsed expander near the relevant component.

### Tier 3 — Reference

- Full metric glossary
- Calculation methods
- Data limitations
- Supported and unsupported Ask Dashboard questions
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

## Copy pattern

Prefer:

> Compare average net score per player across alliances.

Instead of:

> This section shows a chart that allows you to compare the average net score per player across the alliances based on the current sidebar filters.

Prefer:

> Negative share uses absolute values so alliance shares can be compared.

Instead of repeating separate explanations above and below the same chart.

## Implementation order

1. Add key-parity and placeholder tests.
2. Establish product, design, content, and localization context files.
3. Inventory all hard-coded user-visible strings in `app.py` and `ask_dashboard.py`.
4. Localize the Ask Dashboard shell and state its question-language limitation.
5. Remove duplicate tab/subheader pairs and consolidate repeated captions.
6. Move extended guidance into contextual expanders.
7. Separate locale data from Streamlit presentation.
8. Run rendered reviews for all five locales and narrow viewports.
