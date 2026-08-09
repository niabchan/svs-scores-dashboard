# SVS Scores Dashboard — Product Context

## Product

SVS Scores Dashboard is an operational Streamlit dashboard for reviewing player and alliance performance in Evony Server 559+461. Ask Dashboard is the question-and-answer layer inside the dashboard.

This is not a marketing site. The interface should help returning users scan data, compare results, test player exclusions, and understand calculated answers quickly.

## Primary users

- Players reviewing their own or other players' SVS results
- Alliance leaders comparing alliance-level performance
- Server members trying to understand positive and negative impact
- The project owner reviewing data quality, routing behaviour, and feedback

Users may not know data-analysis terminology. Some users will use the dashboard in English, Spanish, French, Vietnamese, or Indonesian.

## Primary jobs

1. Select an SVS period and relevant alliances or net-status filters.
2. Compare score gained, score lost, net score, rank, and player counts.
3. See which alliances or players contribute to positive and negative results.
4. Test how excluding players changes the selected result.
5. Ask a supported question and receive an explanation grounded in the current filtered data.

## Product truths

- Score gained, score lost, and net score are different metrics and must never be conflated.
- Positive or negative contribution describes calculated score impact; it does not prove intent, skill, character, or unseen gameplay behaviour.
- Some score-gained values may be rounded by Evony. Where applicable, the dashboard must preserve the existing approximation notice.
- Sidebar filters affect most charts and tables, while Overview metrics intentionally use the full server total for the selected SVS period.
- Player names and alliance names are user data and must not be translated.

## Non-goals

- Judging whether a player is good, bad, reckless, malicious, or responsible for an outcome
- Inferring motive or unseen gameplay circumstances
- Replacing exact score tables with narrative summaries
- Adding decorative copy, marketing claims, or animation that slows data scanning

## Experience principles

- Operate, do not advertise.
- Show the answer before the explanation.
- Keep essential context visible; move teaching and reference material behind progressive disclosure.
- Use one canonical term for each metric in every language.
- Preserve precision even when shortening copy.
- A returning user should be able to ignore help text and still use the page efficiently.
