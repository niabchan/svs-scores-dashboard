---
name: ask-dashboard-content-i18n
description: Audit and improve SVS Scores Dashboard UI copy, information hierarchy, and multilingual resilience without changing metric meaning, calculations, routing, privacy semantics, or user data.
---

# Ask Dashboard Content and I18n

Use this skill when reviewing or changing user-visible text, help content, localization, layout resilience, or information hierarchy in the SVS Scores Dashboard.

## Required context

Read these files before making recommendations or edits:

1. `PRODUCT.md`
2. `DESIGN.md`
3. `CONTENT.md`
4. `LOCALIZATION.md`
5. the relevant sections of `app.py` and `ask_dashboard.py`

Treat the product truths, metric distinctions, capability boundaries, and semantic constraints in those files as requirements.

## Default mode

Default to **report only** for a new design or content area. Do not edit code until the findings identify a clear, low-risk change or the user explicitly requests implementation.

When implementation is requested, make the smallest coherent change and preserve existing tests.

## Audit workflow

### 1. Inventory user-visible copy

Identify strings used for page, tab, section, chart, and table headings; filters and controls; captions, tooltips, guides, and expanders; empty, loading, error, and warning states; Ask Dashboard questions, answers, and feedback; and analytics or privacy explanations.

Flag hard-coded English strings that bypass the translation system.

### 2. Classify content

Classify every reviewed item as:

- **Tier 1:** always visible and required for operation
- **Tier 2:** contextual help near the relevant component
- **Tier 3:** reference, methodology, limitation, privacy, or extended guidance

Recommend moving content between tiers before rewriting it.

### 3. Check hierarchy and repetition

Look for a tab label repeated as an identical subheader; a heading, caption, and reading guide that restate the same idea; repeated filter-scope explanations; instructions that describe obvious controls; and explanatory copy that appears before the result it explains.

Prefer one task-oriented heading and one short visible sentence. Preserve extended help behind progressive disclosure.

### 4. Protect metric meaning

Never conflate Score Gained, Score Lost, Net Score, Positive Contribution, Negative Contribution, Net per Player, full-server totals, filtered-scope totals, or selected-player comparisons.

Do not infer motives, blame, ability, conduct, or unseen gameplay from score data.

### 5. Review localization

For `en`, `es`, `fr`, `vi`, and `id`:

- compare key sets against canonical English
- check blank values and placeholder parity
- flag English leakage inside translated prose
- preserve player and alliance names unchanged
- keep component markup outside translation values where practical
- test long translations, long names, large values, and narrow viewports

Do not claim multilingual free-text question support unless routing and generated-answer tests support that language.

### 6. Validate

Run or update the smallest relevant checks:

- `python -m pytest -q test_ui_copy.py`
- the existing project test suite when code changes affect runtime behaviour
- rendered Streamlit or browser checks when layout changes are involved

If rendered access is unavailable, say so and distinguish source-level findings from visual findings.

## Working with Impeccable

Impeccable is complementary to this skill.

Use Impeccable in this order when a rendered app is available:

1. critique
2. distill
3. clarify
4. harden
5. polish

Ask it to report findings before editing. Give it `PRODUCT.md` and `DESIGN.md` as context. This skill remains the authority for project terminology, metric semantics, localization boundaries, and content-tier decisions.

## Output format

Report findings in priority order:

- **P0:** misleading capability, meaning, privacy, or unusable multilingual state
- **P1:** major comprehension, hierarchy, consistency, or maintenance problem
- **P2:** polish, efficiency, or resilience improvement

For each finding include location, problem, user impact, recommended content tier, proposed change, and whether rendered verification is still needed.

End with the smallest safe implementation sequence.
