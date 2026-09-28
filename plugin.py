from __future__ import annotations

from LSP.plugin import ClientNotification
from LSP.plugin import ClientRequest
from LSP.plugin import ClientResponse
from LSP.plugin import LspPlugin
from LSP.plugin import OnPreStartContext
from LSP.plugin import PluginStartError
from LSP.plugin import ServerResponse
from LSP.plugin import WorkspaceFolder
from lsp_utils import NodeManager
from pathlib import Path
from sublime_lib import ResourcePath
from typing import Any
from typing_extensions import override
import sublime

OXLINT_LOCATION = Path('node_modules', 'oxlint', 'bin', 'oxlint')
OXLINT_CONFIG_FILES = ('.oxlintrc.json', '.oxlintrc.jsonc', 'oxlint.config.ts', 'oxlint.config.mts')
# The section the server requests with `workspace/configuration`.
SERVER_SECTION = 'oxc_language_server'


def remove_null_values(value: Any) -> Any:
    if isinstance(value, dict):
        return {key: remove_null_values(item) for key, item in value.items() if item is not None}
    return value


class LspOxlintPlugin(LspPlugin):

    @classmethod
    @override
    def on_pre_start_async(cls, context: OnPreStartContext) -> None:
        init_options = context.configuration.initialization_options
        if init_options.get('oxc.requireConfig') and not cls._has_oxlint_config(context.workspace_folders):
            raise PluginStartError('[LSP-oxlint] No oxlint configuration file found in the workspace folders.')
        if tsgolint_path := init_options.get('oxc.path.tsgolint'):
            context.configuration.env['OXLINT_TSGOLINT_PATH'] = tsgolint_path
        if init_options.get('oxc.suppressProgramErrors'):
            context.configuration.env['OXLINT_TSGOLINT_DANGEROUSLY_SUPPRESS_PROGRAM_DIAGNOSTICS'] = 'true'
        server_path: str | None = context.configuration.root_settings.get('server_path')
        if server_path and server_path != 'auto':
            if (oxlint_path := cls._get_workspace_relative_path(Path(server_path), context.workspace_folders)):
                context.configuration.root_settings['server_path'] = str(oxlint_path)
            else:
                raise PluginStartError(
                    f'[LSP-oxlint] Could not resolve oxlint binary from specified server_path {server_path}.')
        elif (oxlint_path := cls._get_workspace_dependency(context.workspace_folders)):
            context.configuration.root_settings['server_path'] = str(oxlint_path)
        package_name = cls.plugin_storage_path.name
        NodeManager.on_pre_start_async(
            context,
            cls.plugin_storage_path,
            ResourcePath('Packages', package_name, 'language-server'),
            OXLINT_LOCATION,
            node_version_requirement='^20.19.0 || >=22.12.0',
        )

    @classmethod
    def _has_oxlint_config(cls, workspace_folders: list[WorkspaceFolder]) -> bool:
        return any(Path(folder.path, name).is_file() for folder in workspace_folders for name in OXLINT_CONFIG_FILES)

    @classmethod
    def _get_workspace_relative_path(cls, lsp_bin: Path, workspace_folders: list[WorkspaceFolder]) -> Path | None:
        if lsp_bin.is_absolute():
            return lsp_bin
        for folder in workspace_folders:
            if (possible_path := Path(folder.path, lsp_bin)).is_file():
                return possible_path
        return None

    @classmethod
    def _get_workspace_dependency(cls, workspace_folders: list[WorkspaceFolder]) -> Path | None:
        for folder in workspace_folders:
            if (binary_path := Path(folder.path, OXLINT_LOCATION)).is_file():
                return binary_path
        return None

    def _server_options(self) -> dict[str, Any] | None:
        if not (session := self.weaksession()):
            return None
        options = remove_null_values(session.config.settings.get())
        return sublime.expand_variables(options, session.window.extract_variables())

    def _workspace_server_options(self) -> list[dict[str, Any]] | None:
        """Options for every workspace folder, in the shape that the language server expects."""
        if not (session := self.weaksession()) or (options := self._server_options()) is None:
            return None
        return [
            {'workspaceUri': folder.uri(), 'options': options} for folder in session.get_workspace_folders()
        ]

    @override
    def on_pre_send_request_async(self, request: ClientRequest, view: sublime.View | None) -> None:
        if request['method'] == 'initialize':
            # The package `initialization_options` are used only by the plugin and are not sent to the server.
            request['params']['initializationOptions'] = self._workspace_server_options()

    @override
    def on_pre_send_notification_async(self, notification: ClientNotification) -> None:
        if notification['method'] == 'workspace/didChangeConfiguration':
            notification['params']['settings'] = self._workspace_server_options()

    @override
    def on_pre_send_response_async(self, response: ClientResponse) -> None:
        if response['method'] != 'workspace/configuration' or (options := self._server_options()) is None:
            return
        # Modify the list in place as it is the one that is sent to the server.
        for index, item in enumerate(response['params']['items']):
            if item.get('section') == SERVER_SECTION:
                response['result'][index] = options

    @override
    def on_server_response_async(self, response: ServerResponse) -> None:
        if response['method'] == 'initialize':
            if (session := self.weaksession()) and (version := response['result'].get('serverInfo', {}).get('version')):
                session.set_config_status_async(version)


def plugin_loaded() -> None:
    LspOxlintPlugin.register()


def plugin_unloaded() -> None:
    LspOxlintPlugin.unregister()
