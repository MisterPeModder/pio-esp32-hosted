import os
import urllib
import sys
import json
import re

from platformio.public import PlatformBase, to_unix_path


IS_WINDOWS = sys.platform.startswith("win")


class Esp32hostedPlatform(PlatformBase):
    def configure_default_packages(self, variables, targets):
        return super().configure_default_packages(variables, targets)

    def get_boards(self, id_=None):
        result = super().get_boards(id_)
        if not result:
            return result
        if id_:
            return self._add_dynamic_options(result)
        else:
            for key, value in result.items():
                result[key] = self._add_dynamic_options(result[key])
        return result

    def _add_dynamic_options(self, board):
        # upload protocols
        if not board.get("upload.protocols", []):
            board.manifest["upload"]["protocols"] = ["esptool", "espota"]
        if not board.get("upload.protocol", ""):
            board.manifest["upload"]["protocol"] = "esptool"

        # debug tools
        debug = board.manifest.get("debug", {})
        supported_debug_tools = [
            "cmsis-dap",
            "esp-prog",
            "esp-bridge",
            "iot-bus-jtag",
            "jlink",
            "minimodule",
            "olimex-arm-usb-tiny-h",
            "olimex-arm-usb-ocd-h",
            "olimex-arm-usb-ocd",
            "olimex-jtag-tiny",
            "tumpa",
        ]

        # A special case for the Kaluga board that has a separate interface config
        if board.id == "esp32-s2-kaluga-1":
            supported_debug_tools.append("ftdi")

        if board.get("build.mcu", "") in ("esp32c3", "esp32c6", "esp32s3"):
            supported_debug_tools.append("esp-builtin")

        upload_protocol = board.manifest.get("upload", {}).get("protocol")
        upload_protocols = board.manifest.get("upload", {}).get("protocols", [])
        if debug:
            upload_protocols.extend(supported_debug_tools)
        if upload_protocol and upload_protocol not in upload_protocols:
            upload_protocols.append(upload_protocol)
        board.manifest["upload"]["protocols"] = upload_protocols

        if "tools" not in debug:
            debug["tools"] = {}

        board.manifest["debug"] = debug
        return board

    def is_embedded(self):
        return False

    @staticmethod
    def extract_toolchain_versions(tool_deps):
        def _parse_version(original_version):
            assert original_version
            version_patterns = (
                r"^gcc(?P<MAJOR>\d+)_(?P<MINOR>\d+)_(?P<PATCH>\d+)-esp-(?P<EXTRA>.+)$",
                r"^esp-(?P<EXTRA>.+)-(?P<MAJOR>\d+)\.(?P<MINOR>\d+)\.?(?P<PATCH>\d+)$",
                r"^esp-(?P<MAJOR>\d+)\.(?P<MINOR>\d+)\.(?P<PATCH>\d+)(_(?P<EXTRA>.+))?$",
            )
            for pattern in version_patterns:
                match = re.search(pattern, original_version)
                if match:
                    result = "%s.%s.%s" % (
                        match.group("MAJOR"),
                        match.group("MINOR"),
                        match.group("PATCH"),
                    )
                    if match.group("EXTRA"):
                        result = result + "+%s" % match.group("EXTRA")
                    return result

            raise ValueError("Bad package version `%s`" % original_version)

        if not tool_deps:
            raise ValueError(
                ("Failed to extract tool dependencies from the remote package file")
            )

        toolchain_remap = {
            "xtensa-esp32-elf-gcc": "toolchain-xtensa-esp32",
            "xtensa-esp32s2-elf-gcc": "toolchain-xtensa-esp32s2",
            "xtensa-esp32s3-elf-gcc": "toolchain-xtensa-esp32s3",
            "riscv32-esp-elf-gcc": "toolchain-riscv32-esp",
        }

        result = dict()
        for tool in tool_deps:
            if tool["name"] in toolchain_remap:
                result[toolchain_remap[tool["name"]]] = _parse_version(tool["version"])

        return result

    @staticmethod
    def parse_tool_dependencies(index_data):
        for package in index_data.get("packages", []):
            if package["name"] == "esp32":
                for platform in package["platforms"]:
                    if platform["name"] == "esp32":
                        return platform["toolsDependencies"]

        return []

    @staticmethod
    def download_remote_package_index(url_items):
        def _prepare_url_for_index_file(url_items):
            tag = "master"
            if url_items.fragment:
                tag = url_items.fragment
            return (
                "https://raw.githubusercontent.com/%s/"
                "%s/package/package_esp32_index.template.json"
                % (url_items.path.replace(".git", ""), tag)
            )

        index_file_url = _prepare_url_for_index_file(url_items)

        try:
            from platformio.public import fetch_http_content
            content = fetch_http_content(index_file_url)
        except ImportError:
            import requests
            content = requests.get(index_file_url, timeout=5).text

        return json.loads(content)

    def configure_arduino_toolchains(self, package_index):
        if not package_index:
            return

        toolchain_packages = self.extract_toolchain_versions(
            self.parse_tool_dependencies(package_index)
        )
        for toolchain_package, version in toolchain_packages.items():
            if toolchain_package not in self.packages:
                self.packages[toolchain_package] = dict()
            self.packages[toolchain_package]["version"] = version
            self.packages[toolchain_package]["owner"] = "espressif"
            self.packages[toolchain_package]["type"] = "toolchain"

    def configure_upstream_arduino_packages(self, url_items):
        framework_index_file = os.path.join(
            self.get_package_dir("framework-arduinoespressif32") or "",
            "package",
            "package_esp32_index.template.json",
        )

        # Detect whether the remote is already cloned
        if os.path.isfile(framework_index_file) and os.path.isdir(
            os.path.join(
                self.get_package_dir("framework-arduinoespressif32") or "", ".git"
            )
        ):
            with open(framework_index_file) as fp:
                self.configure_arduino_toolchains(json.load(fp))
        else:
            print("Configuring toolchain packages from a remote source...")
            self.configure_arduino_toolchains(
                self.download_remote_package_index(url_items)
            )
 # type: ignore
