Original path: tests/data/cases/fmtonoff9.py
Snapshot commit: 6ca34c38c7706bf74bf408bb8ba12f086dc1fe45
Original lines: 1-25

# Regression test for https://github.com/psf/black/issues/2877.
# Blank lines that terminate a `# fmt: off` region are inside the region, so
# they must be preserved rather than collapsed to the usual maximum.
x = 1
# fmt: off
a = 1



# fmt: on
y = 2


def f():
    x = 1
    # fmt: off
    a = 1




    # fmt: on
    y = 2
