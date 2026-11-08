# Tentative659: transient Qt layout, not a demonstrated product defect

Unchanged main/e879 reproduces immediate pending-layout widths after a goal
question, but normal20ms Qt settling gives no bounds problems, and the painted
question fits. The three-size focused control passes BEFORE the tentative
geometry patch. No production fix is justified; the scratch patch is withdrawn
by writing back the saved HEAD bytes. No game assertions are changed.
The audit snap helper must settle normal Qt layout before checking/capturing.
The natural657v2 failure remains an unaccepted harness-timing calibration.
