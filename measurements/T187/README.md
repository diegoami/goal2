# T187 accepted captain input correction

[derived: upstream #659/PR661, accepted1bca7fc4] Only `original_match/match.py` is re-vendored,
byte-for-byte from9d18a855, with its per-file provenance. Initial explicit captain/seed/delay inputs
remain; later captain prompts accept the original eligible highlight and never repeat startup inputs.

The inherited T119 opt-in is inert here: default `tail=True` still runs the B7FA player update,
and fixture bytes+1/+3 retain the old default write. The season/default-backend adoption is not activated.

The original E006 fixture is private. The upstream receipts compare the unhooked original and
no-instruction port on its admitted input, including a captain130→134 withdrawal, declared input keys,
startup declarations, result/events/RNG and all DS/accepted memory ranges without a new mask.
Goal2's actual worker reproduction fails before with the bench-slot captain ScreenError; after adoption
it finishes, publishes once and agrees with an original-driven reference using the existing accepted
sealed-port comparison projection. The complete final-head gate and CI are recorded on PR603.
