Original path: src/_pytest/pathlib.py
Snapshot commit: d6f66d42df86624ed128b84ce57df3d173fe1b95
Original lines: 1046-1106

    If one path is relative and one is absolute, returns None.
    """
    try:
        return Path(os.path.commonpath((str(path1), str(path2))))
    except ValueError:
        return None


def bestrelpath(directory: Path, dest: Path) -> str:
    """Return a string which is a relative path from directory to dest such
    that directory/bestrelpath == dest.

    The paths must be either both absolute or both relative.

    If no such path can be determined, returns dest.
    """
    assert isinstance(directory, Path)
    assert isinstance(dest, Path)
    if dest == directory:
        return os.curdir
    # Find the longest common directory.
    base = commonpath(directory, dest)
    # Can be the case on Windows for two absolute paths on different drives.
    # Can be the case for two relative paths without common prefix.
    # Can be the case for a relative path and an absolute path.
    if not base:
        return str(dest)
    reldirectory = directory.relative_to(base)
    reldest = dest.relative_to(base)
    return os.path.join(
        # Back from directory to base.
        *([os.pardir] * len(reldirectory.parts)),
        # Forward from base to dest.
        *reldest.parts,
    )


def safe_exists(p: Path) -> bool:
    """Like Path.exists(), but account for input arguments that might be too long (#11394)."""
    try:
        return p.exists()
    except (ValueError, OSError):
        # ValueError: stat: path too long for Windows
        # OSError: [WinError 123] The filename, directory name, or volume label syntax is incorrect
        return False


def samefile_nofollow(p1: Path, p2: Path) -> bool:
    """Test whether two paths reference the same actual file or directory.

    Unlike Path.samefile(), does not resolve symlinks.
    """
    s1, s2 = p1.lstat(), p2.lstat()
    # On Windows st_ino is the file ID, which file systems are free to not support,
    # in which case it is 0 for every file -- WinFsp mounts such as sshfs-win are one
    # example. os.path.samestat() would then consider any two files on the volume to
    # be the same (python/cpython#78116), so treat a zero file ID as "unknown" and
    # leave the caller with plain path comparison (#14864).
    if s1.st_ino == 0 or s2.st_ino == 0:
        return False
    return os.path.samestat(s1, s2)
