Original path: tests/masonry/builders/test_editable_builder.py
Snapshot commit: 3a95c37c5d5ec600556f519e60e4340f35bbcac1
Original lines: 241-289

"""

    assert tmp_venv._bin_dir.joinpath("baz").read_text(encoding="utf-8") == baz_script

    foo_script = f"""\
#!{tmp_venv.python}
import sys
from foo import bar

if __name__ == '__main__':
    sys.exit(bar())
"""

    assert tmp_venv._bin_dir.joinpath("foo").read_text(encoding="utf-8") == foo_script

    fox_script = f"""\
#!{tmp_venv.python}
import sys
from fuz.foo import bar

if __name__ == '__main__':
    sys.exit(bar.baz())
"""

    assert tmp_venv._bin_dir.joinpath("fox").read_text(encoding="utf-8") == fox_script


@pytest.mark.parametrize("windows", (True, False))
def test_builder_installs_project_gui_scripts(
    tmp_path: Path,
    fixture_dir: FixtureDirGetter,
    mocker: MockerFixture,
    windows: bool,
) -> None:
    project = tmp_path / "simple_project"
    shutil.copytree(fixture_dir("simple_project"), project)
    with project.joinpath("pyproject.toml").open("a", encoding="utf-8") as f:
        f.write('\n[project.gui-scripts]\nfoo-gui = "foo:bar"\n')

    poetry = Factory().create_poetry(project)
    env_manager = EnvManager(poetry)
    venv_path = tmp_path / "venv"
    env_manager.build_venv(venv_path)
    tmp_venv = VirtualEnv(venv_path)
    mocker.patch("poetry.masonry.builders.editable.WINDOWS", windows)

    EditableBuilder(poetry, tmp_venv, NullIO()).build()

    script_file = tmp_venv._bin_dir.joinpath("foo-gui")
