Linux Witcher 2 Savegame Manager

ABOUT
-----

This utility provides a simple way to delete old Witcher 2 savegames on a
Linux box.  The game has a habit of leaving quite a few savegames behind,
which can end up consuming a non-trivial amount of space.  It's difficult
to manage these from inside the game itself, and while it's not hard to
delete them from the CLI (or file manager), this app provides a much
quicker window into the saves (including the screenshots).

The app's UI is lifted almost fully from an existing utility for Windows
(written using Delphi) which can be found here:
http://www.nexusmods.com/witcher2/mods/10/

The utilty could be pretty easily modified to support OSX as well.  Its
value on Windows is somewhat questionable since the other application
already exists and apparently works well.

The app is a Python script written using PyQt for the GUI, so it'll require
PyQt4.  It's licensed under the New/Modified BSD license.

USAGE
-----

Just run "witcher2saves.py" from the CLI or from a GUI launcher and have at
it.

TODO
----

* The thing should probably follow PEP8 guidelines and get packaged up
  properly like a good Python app instead of just a script I cobbled
  together.

* The Windows app has a function to back up savegames to an alternate
  directory.  It probably wouldn't hurt to support that as well.

* Add an option to check currently-selected savegames, so a bunch can be
  easily checked from the GUI, rather than having to check every single
  one.

