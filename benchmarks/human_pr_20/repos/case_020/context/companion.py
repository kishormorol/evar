Original path: tests/puzzle/test_provider.py
Snapshot commit: 62ffee2c98f36c065bc45f482837229ee142db06
Original lines: 861-909

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
    root: ProjectPackage, repository: Repository, pool: RepositoryPool
) -> None:
    """
    A locked package's `requires` may have been pruned down to whatever extras
    were active in an earlier resolution (see locker._get_locked_package()),
    while `extras` always keeps the complete mapping. Activating an extra whose
    dependency isn't in `requires` must still resolve it from `extras`
    (regression test for #10314).
    """
    package_a = Package("A", "1.0", source_type="url", source_url=SOME_URL)
    package_b = Package("B", "1.0")
    dep = get_dependency("B", "^1.0", optional=True)
    # dep is only present in `extras`, not added via package_a.add_dependency(dep)
    package_a.extras = {canonicalize_name("foo"): [dep]}
    repository.add_package(package_a)
    repository.add_package(package_b)

    locked_package = Package("A", "1.0", source_type="url", source_url=SOME_URL)
    provider = Provider(root, pool, NullIO(), locked=[locked_package])

    dependency = Dependency("A", "1.0", extras=["foo"])
