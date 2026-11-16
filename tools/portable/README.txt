goal2 0.1.0 for Windows
=======================

What goal2 is
-------------
goal2 plays goal (version 2), the international football management game New Era
Software published in 1993, in a modern window. In version 0.1 the original game
itself runs inside goal2, emulated, and goal2 shows its screens, its match and its
choices in its own window: the management pages, the pitch window for a watched
match, the bench and the tactics during a match.

goal2 is an independent project. It has no connection with New Era Software.

The files goal2 needs, and where they come from
-----------------------------------------------
goal2 contains no file of the original game. It needs two files of your own copy of
goal (version 2), from the folder you installed it in:

  GOAL.EXE   the game's program; goal2 starts the original from it
  GOAL.DAT   the game's data

GOAL.HLP, the original's help file, is taken too when the folder has it; it is not
required. goal2 checks each file against the released game's own file and tells you,
file by file, which is missing or is not the right one. Nothing is copied from a
folder it refuses.

How to start
------------
1. Unzip this folder anywhere (a path with spaces is fine). Nothing is installed.
2. Double-click goal2.cmd.
3. The first time, goal2 asks for the folder of your goal (version 2): choose the
   folder that holds GOAL.EXE and GOAL.DAT. goal2 checks them and copies them to its
   data folder (below). It does not ask again.
4. On the start window choose New career: the start year, a country, your manager's
   name, then Start. The original's new game runs, with its bulletins, and the
   management window opens.
5. "play next game" plays the next match. Kick off and watch to see it in the pitch
   window, or take the original's quick result.

Python is not needed: goal2 brings its own. goal2.cmd is the only file to start.

Where your files are
--------------------
  %LOCALAPPDATA%\goal2\data    the copies of GOAL.EXE and GOAL.DAT (and GOAL.HLP)
  %LOCALAPPDATA%\goal2\saves   your career: desktop.g2core

Paste %LOCALAPPDATA%\goal2 into the Explorer address bar to open it. Your career is
saved when you save it in the management window (Ctrl+S); the next start offers to
resume it. Importing the original's files again never touches your saves. To remove
goal2, delete this folder and %LOCALAPPDATA%\goal2.

Known limits of version 0.1
---------------------------
- No sound. Where the original plays a sound (a whistle, a tune), the window waits for
  as long as the sound lasts and says which sound it is.
- Windows only, 64-bit.
- This is the first version for players: please report what goes wrong at
  https://github.com/diegoami/goal2/issues
- goal2 later replaces the emulated original with its own engine; careers of version
  0.1 may not carry over to it.

goal2's source: https://github.com/diegoami/goal2
