import http
from os import path

import requests

from rocks.errors import FileLoadError
from rocks.manifest import Manifest
from rocks.rockspec import Rockspec


class RockServer:

    def __init__(self, address: str):
        self.address = address

    def get_manifest(self) -> Manifest:
        return Manifest.from_lua_str(self.get_raw_file("manifest").decode("utf-8"))

    def get_raw_file(self, name: str) -> bytes:
        response = requests.get(path.join(self.address, name))

        if response.status_code < http.HTTPStatus.OK or response.status_code >= http.HTTPStatus.MULTIPLE_CHOICES:
            raise FileLoadError(
                f"Unable to get file: [{response.status_code}] {response.url}"
            )

        return response.content

    def raw_file_exists(self, name: str) -> bool:
        response = requests.head(path.join(self.address, name))
        return response.status_code == http.HTTPStatus.OK

    def file_exists(self, package_name: str, version: str, arch: str) -> bool:
        if arch == "all" or arch == "src":
            extension = f"{arch}.rock"
        else:
            extension = arch
        return self.raw_file_exists(f"{package_name}-{version}.{extension}")
