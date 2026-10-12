"""goal2.ai: computer-opponent logic (stand-ins).

[assumed: Q035 is open; the owner's C key is the game's own choice.]
[A-CPU-1] The computer's eleven: the best-rated player per position of
the country's formation, fit players only. T15 ships a stand-in: the top
11 of the country's 20 squad members by ability, ignoring formation
(the per-position refinement waits for Q035).
[A-CPU-2] The computer's tactics: its country's stored set; it changes
tactics when more than 2 goals behind. T15 ships the read side (return
the country's stored byte from country[+0x2D] per F010); the
change-when-behind loop is a follow-up.
[confirmed: F007] Player record ability byte at +1, position byte at +6.
[confirmed: F010] Country tactics byte at country[+0x2D].
"""
