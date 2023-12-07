from bisect import bisect_left
from copy import deepcopy
from dataclasses import dataclass
from typing import Optional, Union, Type, TypeVar, List

import semver

from rocks.lua import interpretator


def index(a, x):
    i = bisect_left(a, x)
    if i != len(a) and a[i] == x:
        return i
    raise ValueError

T = TypeVar('T')


def get_closest_lower_version_than(a: List[T], x: T) -> T:
    pos = bisect_left(a, x)
    if pos != 0:
        return a[pos - 1]

    zero_version = a[pos]
    if zero_version < x:
        return zero_version
    else:
        return None


# def get_closest_greater_version_than(a: List[T], x: T) -> T:
#     pos = bisect_left(a, x)
#     if pos != len(a) - 1:
#         return a[pos + 1]
#
#     last_version = a[pos]
#     if last_version > x:
#         return last_version
#
#     return None


def get_closest_lower_or_eq_version_than(a: List[T], x: T) -> T:
    pos = bisect_left(a, x)
    if a[pos] == x:
        return a[pos]

    if pos != 0:
        return a[pos - 1]

    zero_version = a[pos]
    if zero_version <= x:
        return zero_version
    else:
        return None



class Version:
    def __init__(self, name: str, arch: list = list):
        self.name = name
        self.arch = arch
        self.is_main = name.startswith("scm")

    def get_arch(self, arch: str) -> Optional[str]:
        try:
            return self.arch[index(self.arch, arch)]
        except ValueError:
            return None

    def has_arch(self, arch: str) -> bool:
        try:
            return index(self.arch, arch) >= 0
        except ValueError:
            return False

    def __str__(self) -> str:
        return self.name

    def __unicode__(self):
        return self.name

    def __hash__(self):
        return hash(self.name)

    def __lt__(self, obj: 'Version'):
        if isinstance(obj, str):
            obj = Version(obj)
        if self.is_main and not obj.is_main:
            return False

        if not self.is_main and obj.is_main:
            return True

        return self.name < obj.name

    def __gt__(self, obj: 'Version'):
        if isinstance(obj, str):
            obj = Version(obj)

        if self.is_main and not obj.is_main:
            return True

        if not self.is_main and obj.is_main:
            return False

        return self.name > obj.name

    def __le__(self, obj: 'Version'):
        if isinstance(obj, str):
            obj = Version(obj)

        if self.is_main and not obj.is_main:
            return False

        if not self.is_main and obj.is_main:
            return True

        return self.name <= obj.name

    def __ge__(self, obj: 'Version'):
        if isinstance(obj, str):
            obj = Version(obj)

        if self.is_main and not obj.is_main:
            return True

        if not self.is_main and obj.is_main:
            return False

        return self.name >= obj.name

    def __eq__(self, obj: 'Version'):
        if isinstance(obj, str):
            obj = Version(obj)

        return self.name == obj.name


class SemanticVersion(semver.Version):

    def __init__(self, name: str, arch: list = list, semv: Optional[semver.Version] = None):
        self.arch = arch
        if semv is not None:
            self.name = str(semv)
            super().__init__(*semv.to_tuple())
        else:
            self.name = name
            super().__init__(*semver.Version.parse(name, True).to_tuple())

    def bump_major(self) -> "SemanticVersion":
        return type(self)(name="", arch=self.arch, semv=semver.Version(self.major + 1))

    def bump_minor(self) -> "SemanticVersion":
        return type(self)(name="", arch=self.arch, semv=semver.Version(self.major, self.minor + 1))

    def bump_patch(self) -> "SemanticVersion":
        return type(self)(name="", arch=self.arch, semv=semver.Version(self.major, self.minor, self.patch + 1))

    def bump_prerelease(self, token: Optional[str] = "rc") -> "SemanticVersion":
        cls = type(self)
        if self._prerelease is not None:
            prerelease = self._prerelease
        elif token == "":
            prerelease = "0"
        elif token is None:
            prerelease = "rc.0"
        else:
            prerelease = str(token) + ".0"

        prerelease = cls._increment_string(prerelease)
        return cls(name="", arch=self.arch, semv=semver.Version(self.major, self.minor, self.patch, prerelease))

    def bump_build(self, token: Optional[str] = "build") -> "SemanticVersion":
        cls = type(self)
        if self._build is not None:
            build = self._build
        elif token == "":
            build = "0"
        elif token is None:
            build = "build.0"
        else:
            build = str(token) + ".0"

        # self._build or (token or "build") + ".0"
        build = cls._increment_string(build)
        if self._build is not None:
            build = self._build
        elif token == "":
            build = "0"
        elif token is None:
            build = "build.0"
        else:
            build = str(token) + ".0"

        # self._build or (token or "build") + ".0"
        build = cls._increment_string(build)
        return cls(name="", arch=self.arch, semv=semver.Version(
            self.major, self.minor, self.patch, self.prerelease, build
        ))

    def get_arch(self, arch: str) -> Optional[str]:
        try:
            return self.arch[index(self.arch, arch)]
        except ValueError:
            return None

    def has_arch(self, arch: str) -> bool:
        try:
            return index(self.arch, arch) >= 0
        except ValueError:
            return False

    def __str__(self) -> str:
        return f'{self.major}.{self.minor}.{self.patch}'

    def __unicode__(self):
        return str(self)

    def __hash__(self):
        return hash(str(self))


def version_from_string(version: str) -> Union[SemanticVersion, Version]:
    try:
        if version == "0":
            version = "scm-1"

        if version == "" or not version[0].isdigit():
            raise ValueError("not a semver string")
        if version.find("-") == -1:
            version += "-1"

        return SemanticVersion(version)
    except ValueError:
        return Version(version)


class Package:

    def __init__(self, name: str):
        self.name = name
        self.semver_versions = []
        self.other_versions = []

    def get_version_by_rule(self, operator: str, version: Union) -> Optional[Union[Version, SemanticVersion]]:
        if operator == "=" or operator == "==":
            version = self.get_version(version)
        elif operator == "<":
            version = self.get_lower_version(version)
        elif operator == "<=":
            version = self.get_lower_or_eq_version(version)
        elif operator == ">":
            version = self.get_greater_version(version)
        elif operator == ">=":
            version = self.get_greater_or_eq_version(version)
        elif operator == "~>":
            version = self.get_pessimistic_version(version)

        return version

    @property
    def latest_scm(self) -> Optional[Version]:
        for version in reversed(self.other_versions):
            if not version.name.startswith("scm"):
                continue

            return version

    @property
    def latest_semver(self) -> Optional[SemanticVersion]:
        if len(self.semver_versions) == 0:
            return None

        return self.semver_versions[len(self.semver_versions) - 1]

    def get_pessimistic_version(self, version: str) -> Optional[Union[Version, SemanticVersion]]:
        version = version_from_string(version)
        if not isinstance(version, SemanticVersion):
            return None

        if version.minor == 0:
            border = version.bump_major()
        else:
            border = version.bump_minor()

        max_found = version
        for v in self.semver_versions:
            if version <= v < border and v > max_found:
                max_found = v

        return max_found

    def get_greater_version(self, version: str) -> Optional[Union[Version, SemanticVersion]]:
        version = version_from_string(version)
        if version is None:
            return None

        if isinstance(version, SemanticVersion):
            return self.latest_semver if (self.latest_semver > version and
                                          self.latest_semver is None) else self.latest_scm

        return self.latest_scm if self.latest_scm > version and self.latest_scm is None else None

    def get_greater_or_eq_version(self, version: str) -> Optional[Union[Version, SemanticVersion]]:
        version = version_from_string(version)
        if version is None:
            return None

        if isinstance(version, SemanticVersion):
            return self.latest_semver if (self.latest_semver is not None and
                                          self.latest_semver >= version) else self.latest_scm

        return self.latest_scm if self.latest_scm is not None and self.latest_scm >= version else None

    def get_lower_version(self, version: str) -> Optional[Union[Version, SemanticVersion]]:
        version = version_from_string(version)
        if version is None:
            return None

        if isinstance(version, SemanticVersion):
            return get_closest_lower_version_than(self.semver_versions, version)

        return get_closest_lower_version_than(self.other_versions, version)

    def get_lower_or_eq_version(self, version: str) -> Optional[Union[Version, SemanticVersion]]:
        version = version_from_string(version)
        if version is None:
            return None

        if isinstance(version, SemanticVersion):
            return get_closest_lower_or_eq_version_than(self.semver_versions, version)

        return get_closest_lower_or_eq_version_than(self.other_versions, version)

    def get_version(self, version: str) -> Optional[Union[Version, SemanticVersion]]:
        try:
            if version.find("-") == -1:
                version += "-1"

            return self.semver_versions[index(self.semver_versions, SemanticVersion(version))]
        except ValueError:
            try:
                return self.other_versions[index(self.other_versions, version)]
            except ValueError:
                return None

    def __str__(self) -> str:
        return self.name

    def __unicode__(self):
        return self.name

    def __hash__(self):
        return hash(self.name)

    def __len__(self):
        return len(self.name)

    def __lt__(self, obj: Union['Package', str]):
        return self.name < str(obj)

    def __gt__(self, obj: Union['Package', str]):
        return self.name > str(obj)

    def __le__(self, obj: Union['Package', str]):
        return self.name <= str(obj)

    def __ge__(self, obj: Union['Package', str]):
        return self.name >= str(obj)

    def __eq__(self, obj: Union['Package', str]):
        return self.name == str(obj)


@dataclass
class Manifest:
    commands: dict
    modules: dict
    packages: list[Package]

    def search(self, package_name: str) -> Optional[Package]:
        try:
            return self.packages[index(self.packages, package_name)]
        except ValueError:
            return None

    @classmethod
    def from_lua_str(cls, content: str) -> 'Manifest':
        manifest_data = interpretator.execute(
            "do " + content + " ;return {commands = commands, modules = modules, packages = repository} end"
        )
        packages = []
        for package_name, package_meta in manifest_data.packages.items():
            package = Package(name=package_name)
            for package_version, version_meta in package_meta.items():
                arches = [e.arch for e in version_meta.values()]

                if len(package_version) != 0 and semver.Version.is_valid(package_version):
                    package.semver_versions.append(
                        SemanticVersion(package_version, arches)
                    )

                else:
                    package.other_versions.append(Version(package_version, arches))

            package.semver_versions = sorted(package.semver_versions)
            package.other_versions = sorted(package.other_versions)
            packages.append(package)
        packages.sort()

        return cls(
            commands=dict(manifest_data.commands),
            modules=dict(manifest_data.modules),
            packages=packages
        )