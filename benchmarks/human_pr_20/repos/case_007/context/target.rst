Original path: changelog/14864.bugfix.rst
Snapshot commit: e25d981ec0ca25a6bda1f5513d6df61e5240e69e
Original lines: 1-1

Fixed collection on Windows collecting the whole suite instead of the given path, on file systems which do not support file IDs (``st_ino`` is ``0`` for every file, as seen for example on ``sshfs-win``/WinFsp mounts). The Windows-only short-path fallback used when matching collection arguments now ignores a zero file ID and compares paths instead.
