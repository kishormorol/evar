Original path: tests/test_console.py
Snapshot commit: 63d3200199f6d4a01268d71f98f27dbe416ee268
Original lines: 376-424


def test_capture() -> None:
    console = Console()
    with console.capture() as capture:
        with pytest.raises(CaptureError):
            capture.get()
        console.print("Hello")
    assert capture.get() == "Hello\n"


def test_input(monkeypatch, capsys) -> None:
    def fake_input(prompt=""):
        console.file.write(prompt)
        return "bar"

    monkeypatch.setattr("builtins.input", fake_input)
    console = Console()
    user_input = console.input(prompt="foo:")
    assert capsys.readouterr().out == "foo:"
    assert user_input == "bar"


def test_input_password(monkeypatch, capsys) -> None:
    def fake_input(prompt, stream=None):
        console.file.write(prompt)
        return "bar"

    import getpass

    monkeypatch.setattr(getpass, "getpass", fake_input)
    console = Console()
    user_input = console.input(prompt="foo:", password=True)
    assert capsys.readouterr().out == "foo:"
    assert user_input == "bar"


def test_status() -> None:
    console = Console(file=io.StringIO(), force_terminal=True, width=20)
    status = console.status("foo")
    assert isinstance(status, Status)


def test_justify_none() -> None:
    console = Console(file=io.StringIO(), force_terminal=True, width=20)
    console.print("FOO", justify=None)
    assert console.file.getvalue() == "FOO\n"


def test_justify_left() -> None:
