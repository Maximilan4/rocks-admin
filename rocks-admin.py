import difflib
from copy import copy
from os import path

import click


from rocks.errors import FileLoadError
from rocks.manifest import Manifest
from rocks.rockspec import Rockspec
from rocks.server import RockServer


@click.group()
@click.option('--server', help='http url of rocks server')
@click.pass_context
def main(ctx: click.Context, server: str):
    ctx.ensure_object(dict)
    ctx.obj["server"] = RockServer(server)


@main.command()
@click.argument("package", default="")
@click.pass_context
def manifest(ctx: click.Context, package: str):
    rocks_server: RockServer = ctx.obj["server"]
    manifest_data = rocks_server.get_manifest()

    if package != "":
        searched = manifest_data.search(package)
        if searched is None:
            click.echo(f"package {package} not found", err=True)
            packages = difflib.get_close_matches(package, [str(p) for p in manifest_data.packages])
            if len(packages) > 0:
                click.echo(f'try next: {",".join(packages)}', nl=True)
            return
        packages = [searched]
    else:
        packages = manifest_data.packages

    for pos, package in enumerate(packages, 1):
        click.echo(f"{pos}. {package.name}:")
        for version in package.other_versions:
            click.echo(f"\t- {version} [{','.join([arch for arch in version.arch])}]")

        for version in package.semver_versions:
            click.echo(f"\t- {version} [{','.join([arch for arch in version.arch])}]")


@main.group(invoke_without_command=True)
@click.argument("package_name")
@click.pass_context
def rockspec(ctx: click.Context, package_name: str):
    rocks_server: RockServer = ctx.obj["server"]
    if package_name == "":
        click.echo(ctx.get_usage())
        return

    manifest_data = rocks_server.get_manifest()
    ctx.obj["manifest"] = manifest_data

    if path.exists(package_name):
        with open(package_name) as specfile:
            ctx.obj["content"] = specfile.read()
            return

    meta = package_name.split('@')

    package = manifest_data.search(meta[0])
    if package is None:
        click.echo(f"not found: {meta[0]}", err=True)
        return

    if len(meta) > 1:
        version = package.get_version(meta[1])
        if version is None:
            click.echo(f"version not found: {meta[1]}", err=True)
            return
    else:
        version = package.latest_scm
        if version is None:
            version = package.latest_semver

        if version is None:
            click.echo("unable to find any latest version", err=True)
            return

    if not version.get_arch("rockspec"):
        click.echo(f"version {version.name}: has no `rockspec` arch")
        return

    ctx.obj["content"] = rocks_server.get_raw_file(f"{package.name}-{version.name}.rockspec")


@rockspec.command()
@click.pass_context
def show(ctx: click.Context):
    if isinstance(ctx.obj["content"], str):
        click.echo(ctx.obj["content"])
        return

    click.echo(ctx.obj["content"].decode("utf-8"))


@rockspec.command()
@click.option("--check-arch", default="rockspec")
@click.pass_context
def deptree(ctx: click.Context, check_arch: str):
    if isinstance(ctx.obj["content"], str):
        content = ctx.obj["content"]
    else:
        content = ctx.obj["content"].decode("utf-8")
    spec = Rockspec.from_string(content)
    server: RockServer = ctx.obj["server"]
    manifest_data: Manifest = ctx.obj["manifest"]
    excluded_rules = ["tarantool", "lua"]  # no need package check
    print_deps_recursive(server, manifest_data, spec, excluded_rules, 1, check_arch)
        # print(package)


def print_deps_recursive(
        server: RockServer,
        man: Manifest,
        spec: Rockspec,
        excluded: list[str],
        level: int = 1,
        check_arch: str = "rockspec",
):
    mark = u'\u2713'
    unmark = 'x'
    excluded = copy(excluded)

    padding = '\t' * level
    for rule in spec.deps_rules:
        if rule.name in excluded:
            click.echo(f"{padding} {rule} [{mark}, excluded]")
            continue

        if rule.name == spec.package:
            click.echo(f"{padding} {rule} [{mark}, cyclicdep]")
            continue

        package = man.search(rule.name)
        if package is None:
            click.echo(f"{padding} {rule} [{unmark}, not found in manifest]")
            continue

        current_version = package.get_version_by_rule(rule.op, rule.version)
        if current_version is None:
            click.echo(f"{padding} {rule} [{unmark}, version not found]")
            continue

        has_arch = mark if current_version.has_arch(check_arch) else unmark
        has_arch_file = mark if server.file_exists(package.name, current_version.name, check_arch) else unmark

        try:
            cur_spec = Rockspec.from_string(
                server.get_raw_file(f"{rule.name}-{current_version.name}.rockspec").decode("utf-8")
            )

            click.echo(
                f"{padding} {rule} [{current_version} {check_arch}: manifest({has_arch})/file({has_arch_file}) ]")
            print_deps_recursive(server, man, cur_spec, excluded, level + 1)
        except FileLoadError:
            click.echo(f"{padding} {rule} [{current_version} {unmark}, has rockspec in manifest, but file not found]")


if __name__ == '__main__':
    main()
