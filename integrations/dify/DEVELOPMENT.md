# Working on the Dify plugin

For maintainers. What users read is [README.md](README.md), which the Dify Marketplace shows on the plugin's page.

## How it is built

The plugin has every tool Rollstack's MCP server lists, but the four that only Rollstack's own viewers call, and its tool files are generated from the server's definitions, not written by hand:

- `tests/fixtures/mcp_tools.json`: every tool the server lists, as it lists it: name, title, description, inputs, and the scope each needs.
- `tests/fixtures/openapi_outputs.json`: what each tool answers, read from Rollstack's OpenAPI document.
- `tests/generate_tools.py` writes, from those two files: `tools/<name>.yaml` (one Dify tool per Rollstack tool, with Rollstack's own name, title, description and inputs, and the fields of its answer as workflow variables), `tools/<name>.py` (the class Dify loads for it), `rollstack_client/tools.json` (how the plugin turns the tool's Dify parameters into the Rollstack tool's arguments), the list of tools in `provider/rollstack.yaml`, and the two tables of tools in `README.md`. `EXCLUDED` in it lists the tools left out and why, and `EMAILS_OR_DELETES` the tools that email people or delete something, which the README lists.

The code that runs is small:

- `manifest.yaml`, `provider/rollstack.yaml`: the plugin and its one credential, a Rollstack API key.
- `rollstack_client/operations.py`: reads `tools.json`, and turns a Dify parameter into the value Rollstack expects. Dify has no list or object parameters for a plugin's tools, so a list of strings comes as text separated by commas, and any other structured input as JSON text, whose JSON Schema its description gives.
- `rollstack_client/mcp.py`: the HTTP client. A tool is one `tools/call` on Rollstack's MCP server.
- `rollstack_client/tooling.py`: turns Rollstack's answer into Dify messages, image files and workflow variables.

Calls go through the MCP server, not the REST API, on purpose: over MCP, Rollstack holds any call that emails people or deletes reports until the user confirms it in Rollstack, even with an API key.

## Test

Python 3.12, the version Dify runs plugins on:

```bash
uv venv --python 3.12 .venv && uv pip install --python .venv -r requirements-dev.txt
```

```bash
.venv/bin/python -m pytest tests
```

The tests answer for Rollstack with scripted responses. `tests/test_contract.py` fails when a generated file differs from what the generator writes, when the plugin's tools aren't the ones in the fixture, or when a tool's inputs aren't Rollstack's. Four more tests call Rollstack's real server:

```bash
ROLLSTACK_LIVE=1 .venv/bin/python -m pytest tests/test_live.py
```

Two of them send a wrong key and need no account. The other two are skipped unless `ROLLSTACK_API_KEY` holds a Rollstack API key, because the server answers a request only when it carries a key. It lists for a key only the tools that key may call, so the key needs every scope: `slide_decks:read`, `slide_decks:write`, `slide_decks:run`, `slide_decks:email`, `connections:read`, `smtp:read` and `users:read`. Only owners and admins can give a key `users:read`, which `listMembers` needs, so an owner or admin makes it. One of the two then fails when the server lists a tool the fixture doesn't have, or a tool differently, and the other opens a session with the key. The key is read from the environment and nowhere else: keep it out of the files of this repo.

## Refresh the tools

When the live test says the reference changed, or Rollstack adds tools, run from this folder, with the key above in `ROLLSTACK_API_KEY`:

```bash
.venv/bin/python tests/update_fixture.py
```

It saves the server's list and what each tool answers, then runs the generator. It saves nothing when the server leaves out a tool that was saved before, such as when the key lacks a scope, and names the scope. Read the diff, run the tests, then package and validate. A tool the server marks as called only by its viewers fails `test_only_the_tools_that_only_a_view_calls_are_left_out` until it is in `EXCLUDED`, and a new tool that emails or deletes belongs in `EMAILS_OR_DELETES`.

To change how the tool files are written, change `tests/generate_tools.py` and run it with `.venv/bin/python tests/generate_tools.py`, never the generated files themselves.

## Try it in Dify

Nothing replaces a run in a real workspace with a real key. Copy `.env.example` to `.env`, fill in the host and key your Dify workspace shows under Debugging, then run `.venv/bin/python -m main` from this folder. The plugin appears in the workspace while the process runs: authorize it with a Rollstack API key and call the tools from an agent or a workflow. The steps under "How to test" in [marketplace/pull-request.md](marketplace/pull-request.md) work in any Rollstack account.

## Package and validate

With the [Dify plugin CLI](https://docs.dify.ai/en/develop-plugin/getting-started/cli), from the root of the repo:

```bash
dify plugin package ./integrations/dify -o rollstack-0.0.1.difypkg
```

`.difyignore` keeps tests, the fixtures, the generator and these notes out of the package. Then run Dify's own checks, from a checkout of [dify-marketplace-toolkit](https://github.com/langgenius/dify-marketplace-toolkit) (they need `yq`):

```bash
python3 validator/validate-difypkg.py /path/to/rollstack-0.0.1.difypkg --output-dir ./validation-report --pr-body-file /path/to/integrations/dify/marketplace/pull-request.md
```

## Release

1. Set the new version in `manifest.yaml` and in `PLUGIN_VERSION` of `rollstack_client/mcp.py`. A test checks they match.
2. Test, package and validate as above.
3. Open a pull request on [langgenius/dify-plugins](https://github.com/langgenius/dify-plugins) that adds only `rollstack/rollstack/rollstack-<version>.difypkg`, titled `add rollstack <version>`, with [marketplace/pull-request.md](marketplace/pull-request.md) as its body, updated for that version. One package per pull request.
