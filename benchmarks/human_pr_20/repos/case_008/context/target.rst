Original path: changelog/14864.bugfix.rst
Snapshot commit: d6f66d42df86624ed128b84ce57df3d173fe1b95
Original lines: 1-1

Fixed collection on Windows collecting the whole suite instead of the given path, on file systems which do not support file IDs (``st_ino`` is ``0`` for every file, as seen for example on ``sshfs-win``/WinFsp mounts).
