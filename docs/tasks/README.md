# Tasks

One file per task, `T<nn>.md`, from [`TEMPLATE.md`](TEMPLATE.md). The issue's `status:*` label is the
status; this index carries none.

| Task | Title | Issue | Merge after |
| --- | --- | --- | --- |
| T01 | The walking skeleton: the package, the quick-engine seam, one fixture end to end | — | — |
| T10 | The screen framework: the character grid (80×25) and a plain-text renderer | #24 | T09 |
| T11 | The country select screen: 128 countries, cursor + keys, write the choice to the state adapter | #26 | T10 |
| T12 | The squad select screen: 20 players, pick captain, write the eleven + captain to the state adapter | #28 | T11 |
| T13 | The tactics screen: 8 team tactics bits, toggleable, write to state | #30 | T12 |
| T14 | The result screen: run the vendored engine, display score + goals, label as stand-in | #<new> | T13 |
