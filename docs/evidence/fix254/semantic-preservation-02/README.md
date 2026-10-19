# Scope and assertion preservation

[confirmed: report.json; reproducible check.py] The entire original controller AST matches accepted84af745c after reversing only its status-read call. Every original viewer function matches after reversing only its status-replace call. All assertions/assert-calls in all13original sharing tests remain identical;16tests now exist. New helpers have separate native/ownership regressions. This is not native execution or independent review.

[designed: guard] The script refuses a checkout lacking the new helpers or13original/16current test inventory. A preliminary invocation from main is excluded. The retained report names actual fix head148042e193fe0195785a9b143da59fcdb923aa91 and the script hash.
