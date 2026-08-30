Original path: src/poetry/masonry/builders/editable.py
Snapshot commit: 6208f6e1f5a6eb945c8d8c101b89def75a111d24
Original lines: 102-212

            pip_install(self._path, self._env, upgrade=True, editable=True)
        finally:
            if not has_setup:
                os.remove(setup)

    def _add_pth(self) -> list[Path]:
        paths = {
            include.base.resolve().as_posix()
            for include in self._module.includes
            if isinstance(include, PackageInclude)
            and (include.is_module() or include.is_package())
        }

        content = "".join(decode(path + os.linesep) for path in paths)
        pth_file = Path(self._module.name).with_suffix(".pth")

        # remove any pre-existing pth files for this package
        for file in self._env.site_packages.find(path=pth_file, writable_only=True):
            self._debug(
                f"  - Removing existing <c2>{file.name}</c2> from <b>{file.parent}</b>"
                f" for {self._poetry.file.path.parent}"
            )
            file.unlink(missing_ok=True)

        try:
            pth_file = self._env.site_packages.write_text(
                pth_file, content, encoding=getencoding()
            )
            self._debug(
                f"  - Adding <c2>{pth_file.name}</c2> to <b>{pth_file.parent}</b> for"
                f" {self._poetry.file.path.parent}"
            )
            return [pth_file]
        except PermissionError:
            self._io.write_error_line(
                f"  - Failed to create <c2>{pth_file.name}</c2> for"
                f" {self._poetry.file.path.parent}"
            )
            return []

    def _add_scripts(self) -> list[Path]:
        added = []
        entry_points = self.convert_entry_points()

        for scripts_path in self._env.script_dirs:
            if is_dir_writable(path=scripts_path, create=True):
                break
        else:
            self._io.write_error_line(
                "  - Failed to find a suitable script installation directory for"
                f" {self._poetry.file.path.parent}"
            )
            return []

        scripts = entry_points.get("console_scripts", []) + entry_points.get(
            "gui_scripts", []
        )
        for script in scripts:
            name, script_with_extras = script.split(" = ")
            script_without_extras = script_with_extras.split("[")[0]
            try:
                module, callable_ = script_without_extras.split(":")
            except ValueError as exc:
                msg = (
                    f"Bad script ({name}): script needs to specify a function within a"
                    " module like: module(.submodule):function\nInstead got:"
                    f" {script_with_extras}"
                )
                if "not enough values" in str(exc):
                    msg += (
                        "\nHint: If the script depends on module-level code, try"
                        " wrapping it in a main() function and modifying your script"
                        f' like:\n{name} = "{script_with_extras}:main"'
                    )
                elif "too many values" in str(exc):
                    msg += '\nToo many ":" found!'

                raise ValueError(msg)

            callable_holder = callable_.split(".", 1)[0]

            script_file = scripts_path.joinpath(name)
            self._debug(
                f"  - Adding the <c2>{name}</c2> script to <b>{scripts_path}</b>"
            )
            with script_file.open("w", encoding="utf-8") as f:
                f.write(
                    decode(
                        SCRIPT_TEMPLATE.format(
                            python=self._env.python,
                            module=module,
                            callable_holder=callable_holder,
                            callable_=callable_,
                        )
                    )
                )

            script_file.chmod(0o755)

            added.append(script_file)

            if WINDOWS:
                cmd_script = script_file.with_suffix(".cmd")
                cmd = WINDOWS_CMD_TEMPLATE.format(python=self._env.python, script=name)
                self._debug(
                    f"  - Adding the <c2>{cmd_script.name}</c2> script wrapper to"
                    f" <b>{scripts_path}</b>"
                )

                with cmd_script.open("w", encoding="utf-8") as f:
                    f.write(decode(cmd))
