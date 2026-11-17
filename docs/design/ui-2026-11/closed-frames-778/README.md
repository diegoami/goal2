# Closed panel outlines

[designed: owner playtest #778, 2026-11-18]
Panel sides, bottom lines and fact dividers remain in front of their visible
content. Opaque labels, fields and highlights must not erase the outline.
The foreground layer is transparent to mouse input and adds no layout padding;
the original32px text, cell positions, colours and controls remain unchanged.

The [receipt](receipt.json) records the pinned before source, screenshot hashes
and three window sizes. Every changed screenshot pixel becomes the existing
frame colour; no text or content is moved. The opaque-body reproduction loses
336side-edge pixels before the fix and zero afterwards. Its regression also
checks late-added content, resizing, fact values, click-through behavior and
geometry in never-shown layouts. Outlines are layout-managed so they do not
keep Qt's initial640×480 size while resize events are deferred.
All15 assistant-state captures retain the existing fit/density checks.

| Window | Before | After |
| --- | --- | --- |
| 1440×900 | [Before](before-1440x900.png) | [After](after-1440x900.png) |
| 1440×1080 | [Before](before-1440x1080.png) | [After](after-1440x1080.png) |
| 2110×1213 | [Before](before-2110x1213.png) | [After](after-2110x1213.png) |

```sh
python -m unittest goal2.tests.test_ui_closed_frames_778 -v
```
