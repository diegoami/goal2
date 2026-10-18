# Footer caption correction

[derived: main-caption-inventory.json] The immutable native probes use `initStyleOption` and `SE_PushButtonContents`: at Windows 200%, focused Confirm had 132 logical pixels for 135 pixels of text and Discard had 75 for 79. Native-02 established cancellation cleanup and frame geometry, but these measurements invalidate complete focused-caption readability. The runtime-only border mock is feasibility evidence, not source acceptance.

[confirmed: scenario-before/report.json; scenario-before.log] The new interaction assertion fails before the scoped style correction at Linux offscreen 200%: focused Discard has 88 pixels for 90 pixels of text. It checks actual QStyle content width/height against the active font in both focused and unfocused states.

[confirmed: scenario-after/report.json; scenario-after/scale-2/report.json; scenario-after.log] Stable three-pixel borders within `draftBar` preserve focus contrast and prevent the focused border from shrinking the text rectangle. The complete squad scenario passes at both scales, including footer containment, no content overlap, all20 rows/fields, complete long detail/board reading coverage, keyboard actions, drafts, availability, IDs and actual cancellation cleanup. The caption measurements cover both actions, both focus states and every supported size/scroll position (36 records at100%,12 at200%). Final native Windows acceptance must use the corrected composed source.

[designed: T76] `style.py` changes only scoped footer borders. `squad_scenario.py` adds glyph-content checks and restores the old border behavior as a saved-source negative control; all existing behavioral oracles remain.

[confirmed: negative-controls/negative-controls.json; negative-controls.log] All six intended mutation assertions fail, including old focused-caption borders at200%; the four saved product sources restore byte-for-byte. Legacy coverage outcomes are recorded without claiming isolation checks that those scripts do not contain.
