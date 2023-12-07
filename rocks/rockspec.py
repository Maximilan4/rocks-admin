from dataclasses import dataclass
from rocks.lua import interpretator, lua_type, table2dict


class DepRule:
    def __init__(self, name: str, op: str = ">=", version: str = "0.1.0", *args):
        self.name = name
        self.op = op
        self.version = version.strip(",")
        self.additional = args

    def __str__(self) -> str:
        return ','.join((f"{self.name} {self.op} {self.version}", ' '.join(self.additional)))

    @classmethod
    def from_str(cls, dep_rule: str) -> 'DepRule':
        parts = dep_rule.split(" ")

        if len(parts) == 1:
            return cls(parts[0])

        if len(parts) == 2:
            return cls(parts[0], "==", parts[1])

        if parts[1] not in ('=', '==', '>', '>=', '<', '<=', '~>'):
            return cls(parts[0], "==", parts[1], *parts[1:])

        return cls(*parts)


@dataclass
class Rockspec:
    package: str
    version: str
    source: dict
    deps_rules: list[DepRule]
    build: dict

    @classmethod
    def open(cls, path: str) -> 'Rockspec':
        with open(path) as specfile:
            content = specfile.read()
            return cls.from_string(content)

    @classmethod
    def from_string(cls, content: str) -> 'Rockspec':
        specdata = interpretator.execute(
            "do " + content + " ;return {package = package, version = version, source = source, deps = dependencies, build = build} end"
        )

        dep_rules = []
        if specdata.deps is not None:
            for rule in dict(specdata.deps).values():
                dep_rules.append(DepRule.from_str(rule))

        return Rockspec(
            package=specdata.package,
            version=specdata.version,
            source=table2dict(specdata.source),
            deps_rules=dep_rules,
            build=table2dict(specdata.build)
        )




