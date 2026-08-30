Original path: tests/puzzle/test_provider.py
Snapshot commit: 5ec337f4b16189427eea2862843345cd8174b5d2
Original lines: 861-909

@pytest.mark.parametrize("source_name", [None, "repo"])
def test_complete_package_with_extras_preserves_source_name(
    provider: Provider, repository: Repository, source_name: str | None
) -> None:
    package_a = Package("A", "1.0")
    package_b = Package("B", "1.0")
    dep = get_dependency("B", "^1.0", optional=True)
    package_a.add_dependency(dep)
    package_a.extras = {canonicalize_name("foo"): [dep]}
    repository.add_package(package_a)
    repository.add_package(package_b)

    dependency = Dependency("A", "1.0", extras=["foo"])
    if source_name:
        dependency.source_name = source_name

    complete_package = provider.complete_package(
        DependencyPackage(dependency, package_a)
    )

    requires = complete_package.package.all_requires
    assert len(requires) == 2
    assert requires[0].name == "a"
    assert requires[0].source_name == source_name
    assert requires[1].name == "b"
    assert requires[1].source_name is None


def test_complete_package_resolves_extra_dependency_missing_from_requires(
    provider: Provider, repository: Repository
) -> None:
    """
    A locked package's `requires` may have been pruned down to whatever extras
    were active in an earlier resolution (see locker._get_locked_package()),
    while `extras` always keeps the complete mapping. Activating an extra whose
    dependency isn't in `requires` must still resolve it from `extras`
    (regression test for #10314).
    """
    package_a = Package("A", "1.0")
    package_b = Package("B", "1.0")
    dep = get_dependency("B", "^1.0", optional=True)
    # dep is only present in `extras`, not added via package_a.add_dependency(dep)
    package_a.extras = {canonicalize_name("foo"): [dep]}
    repository.add_package(package_a)
    repository.add_package(package_b)

    dependency = Dependency("A", "1.0", extras=["foo"])

    complete_package = provider.complete_package(
