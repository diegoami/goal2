# GOAL2 whole-game redesign: decision package #253

[designed: owner request #253,2026-10-19] This package proposes a desktop football management game built around managing a country: **Country desk** for the campaign, **Team** for decisions, and **Match centre** for preparation, live play and results. It is planning only. The owner must explicitly select/approve a direction before any redesign implementation or child issue starts. A documentation review, issue filing or merge of this package is not that approval. No toolkit, language or architecture migration is authorized.

[designed: #253] The recommendation is a compact country-management workspace with a persistent next-match action, a comparison-first player desk and one continuous match centre. The information contract is independent of the frontend. Retaining the Python backend is the working recommendation; frontend alternatives and the cost of changing them will be evaluated in this package.

[confirmed: accepted manual PR247] Original references use manual commit `ebdd6879d469a574f6d4b446f59b33a6be3ffd81`. The current-build audit is pinned to `3335da830d289cc869f989b73816926c54360ff1`. All63 game PNGs and the separately indexed DOS shell were visually inspected at native640×400 in readable contact sheets; no new original asset is added. Observations, printed hints, unknown meanings and proposed choices remain distinct.

[designed: #253] The complete decision package is being assembled in this task branch. The final PR will link the experience assessment, field-level parity matrix, annotated static layouts, journeys, technology/owner decisions and implementation backlog here. No application or engine change belongs to this issue.
