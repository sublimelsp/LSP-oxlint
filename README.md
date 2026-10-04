# LSP-oxlint

[Oxlint](https://oxc.rs/docs/guide/usage/linter) support for Sublime Text, provided through the [oxc language server](https://github.com/oxc-project/oxc/tree/main/crates/oxc_language_server).

## Installation

1. Install [LSP](https://packagecontrol.io/packages/LSP) and [LSP-oxlint](https://packagecontrol.io/packages/LSP-oxlint) via Package Control.
2. (Optional but recommended) Install [LSP-file-watcher-chokidar](https://github.com/sublimelsp/LSP-file-watcher-chokidar) via Package Control. The server uses file watching to reload when `.oxlintrc.json` changes.
3. Restart Sublime.

## Oxlint resolution

The package uses oxlint from the project's local dependencies (`node_modules/oxlint`) when it is present. We recommend to add oxlint as a project dependency, so that the CLI and the editor use the same version.

You can also set an explicit path with the `server_path` setting. A relative path is resolved against the workspace folder.

If the project has no oxlint dependency and `server_path` is `auto`, the package uses the oxlint version that it manages itself.

## Configuration

Open the configuration file with the Command Palette `Preferences: LSP-oxlint Settings` command or from the Sublime menu.

Oxlint rules are configured in the `.oxlintrc.json` file of the project. Refer to [Configuring oxlint](https://oxc.rs/docs/guide/usage/linter/config).

## Usage

### Fix all

Use the `LSP-oxlint: Fix All` command from the Command Palette to apply all safe fixes in the current file.

To apply fixes on save, open `Preferences: LSP Settings` from the Command Palette and set:

```json
{
    "lsp_code_actions_on_save": {
        "source.fixAll.oxc": true,
    }
}
```

Use `source.fixAllDangerous.oxc` to also apply dangerous fixes. This requires a `fixKind` setting that allows dangerous fixes.
