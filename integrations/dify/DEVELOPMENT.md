# Working on the Dify plugin

For maintainers. What users read is [README.md](README.md), which the Dify Marketplace shows on the plugin's page.

## How it is built

- `manifest.yaml`, `provider/rollstack.yaml`: the plugin and its one credential, a Rollstack API key.
- `tools/<name>.yaml`: one Dify tool per Rollstack tool, with Rollstack's own name, title, inputs and descriptions.
- `tools/<name>.py`: the class Dify loads for the tool. Each one only names the Rollstack tool it calls.
- `rollstack_client/operations.py`: which Rollstack field each Dify parameter fills, and how text becomes a list.
- `rollstack_client/mcp.py`: the HTTP client. A tool is one `tools/call` on Rollstack's MCP server.
- `rollstack_client/tooling.py`: turns Rollstack's answer into Dify messages and workflow variables.

Calls go through the MCP server, not the REST API, on purpose: over MCP, Rollstack makes the user confirm in Rollstack any call that emails people, even with an API key. Don't add a tool that emails or deletes: see `test_no_tool_emails_people_or_deletes_anything`.

## Test

Python 3.12, the version Dify runs plugins on:

```bash
uv venv --python 3.12 .venv && uv pip install --python .venv -r requirements-dev.txt
```

```bash
.venv/bin/python -m pytest tests
```

The tests answer for Rollstack with scripted responses. Four more call Rollstack's real server and need no account, since it lists its tools and refuses a wrong key without one:

```bash
ROLLSTACK_LIVE=1 .venv/bin/python -m pytest tests/test_live.py
```

`tests/fixtures/mcp_tools.json` is the definition of the plugin's tools as Rollstack's MCP server lists them, and `tests/test_contract.py` keeps the tool files true to it. When the live test says the reference changed, refresh it with `.venv/bin/python tests/update_fixture.py`, read the diff, and bring `tools/*.yaml` and `operations.py` in line. A description may only drop whole sentences of the reference, or add one of the notes listed in `test_contract.py`.

## Try it in Dify

Nothing replaces a run in a real workspace with a real key. Copy `.env.example` to `.env`, fill in the host and key your Dify workspace shows under Debugging, then run `.venv/bin/python -m main` from this folder. The plugin appears in the workspace while the process runs: authorize it with a Rollstack API key and call the tools from an agent or a workflow.

## Package and validate

With the [Dify plugin CLI](https://docs.dify.ai/en/develop-plugin/getting-started/cli), from the root of the repo:

```bash
dify plugin package ./integrations/dify -o rollstack-0.0.1.difypkg
```

`.difyignore` keeps tests and these notes out of the package. Then run Dify's own checks, from a checkout of [dify-marketplace-toolkit](https://github.com/langgenius/dify-marketplace-toolkit) (they need `yq`):

```bash
python3 validator/validate-difypkg.py /path/to/rollstack-0.0.1.difypkg --output-dir ./validation-report --pr-body-file /path/to/integrations/dify/marketplace/pull-request.md
```

## Release

1. Set the new version in `manifest.yaml` and in `PLUGIN_VERSION` of `rollstack_client/mcp.py`. A test checks they match.
2. Test, package and validate as above.
3. Open a pull request on [langgenius/dify-plugins](https://github.com/langgenius/dify-plugins) that adds only `rollstack/rollstack/rollstack-<version>.difypkg`, titled `add rollstack <version>`, with [marketplace/pull-request.md](marketplace/pull-request.md) as its body, updated for that version. One package per pull request.
