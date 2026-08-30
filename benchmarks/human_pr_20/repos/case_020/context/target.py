Original path: src/poetry/puzzle/provider.py
Snapshot commit: 62ffee2c98f36c065bc45f482837229ee142db06
Original lines: 533-643

            else:
                pool_package = self.get_package_from_pool(
                    package.pretty_name,
                    package.version,
                    repository_name=dependency.source_name,
                )
            if package.files and self._files_list_for_cmp(
                package.files
            ) != self._files_list_for_cmp(pool_package.files):
                # This happens if additional artifacts are uploaded later. Either our own cache
                # is outdated or the lockfile has been created with an outdated cache.
                # Refresh to cover the first case. (It does not hurt much in the second case.)
                pool_package = self.pool.refresh(pool_package)
                self._refreshed.add(
                    (package.pretty_name, package.version, dependency.source_name)
                )
            dependency_package = DependencyPackage(dependency, pool_package)

            package = dependency_package.package
            dependency = dependency_package.dependency
            requires = package.requires

        found_extras = set()
        optional_dependencies = set()
        _dependencies = []

        if dependency.extras:
            # Find all the optional dependencies that are wanted - taking care to allow
            # for self-referential extras.
            stack = sorted(dependency.extras)

            # For direct origin dependencies from the lock file,
            # only used extra dependencies are found in `requires`.
            # If the package locked for a direct origin dependency is reused,
            # its `requires` have been pruned down to whatever extras were active
            # in an earlier resolution. This is an issue in subsequent resolutions
            # if an additional extra is requested via changes in the pyproject.toml.
            # (Dependencies from repositories are looked up again
            # so that this is not issue for them.)
            if is_direct_origin:
                requires = requires.copy()
                requires_extras = {extra for dep in requires for extra in dep.in_extras}

            while stack:
                extra = stack.pop()
                if extra in found_extras:
                    continue
                found_extras.add(extra)

                extra_dependencies = package.extras.get(extra, [])
                for extra_dependency in extra_dependencies:
                    if extra_dependency.name == dependency.name:
                        stack += sorted(extra_dependency.extras)
                    else:
                        optional_dependencies.add(extra_dependency.name)
                        if is_direct_origin and extra not in requires_extras:
                            requires.append(extra_dependency)

            # If some extras/features were required, we need to add a special dependency
            # representing the base package to the current package.

            dependency_package = dependency_package.with_features(dependency.extras)
            package = dependency_package.package
            dependency = dependency_package.dependency
            new_dependency = package.without_features().to_dependency()
            new_dependency.marker = dependency.marker

            # When adding dependency foo[extra] -> foo, preserve foo's source, if it's
            # specified. This prevents us from trying to get foo from PyPI
            # when user explicitly set repo for foo[extra].
            if not new_dependency.source_name and dependency.source_name:
                new_dependency.source_name = dependency.source_name

            _dependencies.append(new_dependency)

        for dep in requires:
            if not self._python_constraint.allows_any(dep.python_constraint):
                continue

            if dep.name in self.UNSAFE_PACKAGES:
                continue

            # When this run is restricted to a set of markers (see MARKER_SPLIT),
            # skip any dependency that cannot apply within that set; otherwise its
            # requirements would leak into a run where it never applies (see
            # #5506).
            if self._overrides_marker_intersection.intersect(dep.marker).is_empty():
                continue

            if self._env:
                marker_values = (
                    self._marker_values(self._active_root_extras)
                    if package.is_root()
                    else self._env.marker_env
                )
                if not dep.marker.validate(marker_values):
                    continue

            if not package.is_root() and (
                (dep.is_optional() and dep.name not in optional_dependencies)
                or (dep.in_extras and not set(dep.in_extras).intersection(found_extras))
            ):
                continue

            # For normal dependency resolution, we have to make sure that root extras
            # are represented in the markers. This is required to identify mutually
            # exclusive markers in cases like 'extra == "foo"' and 'extra != "foo"'.
            # However, for installation with re-resolving (installer.re-resolve=true,
            # which results in self._env being not None), this spoils the result
            # because we have to keep extras so that they are uninstalled
            # when calculating the operations of the transaction.
