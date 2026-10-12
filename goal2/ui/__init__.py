"""The screen framework: character grid and renderers.

[confirmed: plan.md, the owner's 2026-10-12 decision] Screens draw into a
character grid (80x25 cells: character, foreground, background), never straight
to a terminal. Renderers: a plain-text one for tests and logs, and a window one
that scales (zoom), uses a readable font, and can later add what the original
lacks. A screen is tested by its grid, not its pixels.
"""
