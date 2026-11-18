# Plugin Submission

<!--
The body of the pull request to langgenius/dify-plugins that adds rollstack/rollstack/rollstack-0.0.1.difypkg.
Title: add rollstack 0.0.1
Before opening it:
1. Run the plugin in a Dify workspace with a Rollstack API key (see "Try it in Dify" in DEVELOPMENT.md), following the
   "How to test" steps under "Reviewer notes", and correct any step that doesn't go as written.
2. Tick the three boxes left open under "Required checks": the first two are your own statement, the third is that run.
3. Replace the "Not yet run in a Dify workspace" paragraph under "Reviewer notes" with what you tested and on which Dify version.
4. Run the live tests with a Rollstack API key in ROLLSTACK_API_KEY (see "Test" in DEVELOPMENT.md): two of the four are
   skipped without one. Then replace their output and the line about them under "Local validation".
These comments are not shown on the pull request.
-->

## Plugin information

- **Author**: rollstack
- **Plugin name**: rollstack
- **Version**: 0.0.1
- **Source repository**: https://github.com/Rollstack/skills/tree/main/integrations/dify
- **Contact**: support@rollstack.com

## Submission type

- [x] New plugin
- [ ] Version update

## What changed

New plugin for [Rollstack](https://www.rollstack.com), the AI presentation platform for business reporting: slide decks built from a company's data, in its own template, and kept up to date. No Marketplace plugin connects to Rollstack today.

It lets a Dify agent or workflow work with the user's Rollstack reports, with 12 tools. They are Rollstack's own tools, with the names, inputs and descriptions of its [MCP server and API](https://docs.rollstack.com/api/mcp-server):

- Find and read reports: `listReports`, `getReport`, `getReportContent`
- Build or change a deck with Rollstack's slides agent, and read its reply: `listTemplates`, `createReport`, `sendReportMessage`, `getReportMessage`
- Refresh a report from its data sources: `startReportRun`, `getReportRun`
- Set when a report updates on its own: `getReportSchedules`, `updateReportSchedules`
- Export a report as PDF or PowerPoint: `exportReport`

Each tool returns Rollstack's answer as JSON and its main fields as workflow variables (`output_schema`), so a workflow can chain them, for example `sendReportMessage` to `getReportMessage`.

Authentication is a Rollstack API key that the user creates in Rollstack with the scopes they choose (`slide_decks:read`, `slide_decks:write`, `slide_decks:run`).

## Risk level

- [ ] Low risk
- [x] Medium risk
- [ ] High risk

## Required checks

- [ ] I have read and followed the [Marketplace submission requirements](https://github.com/langgenius/dify-plugins/blob/main/docs/plugin-submission-requirements.md).
- [ ] I have read and comply with the [Plugin Development Guidelines](https://docs.dify.ai/en/develop-plugin/publishing/standards/contributor-covenant-code-of-conduct).
- [ ] I tested this plugin on Dify Community Edition and Dify Cloud, or documented any limitation below.
- [x] The package contains only files needed at runtime.
- [x] The package does not contain secrets, local credentials, `.env` files, `.git` directories, virtual environments, caches, logs, or IDE files.
- [x] The package does not contain executables or bundled binaries, or I explained why they are required below.
- [x] The plugin README includes setup steps, usage instructions, required APIs or credentials, connection requirements, and the source repository link.
- [x] The plugin includes `PRIVACY.md` or a hosted privacy policy, and `manifest.yaml` references it.
- [x] All user-facing text is primarily in English, with any localized README files following the [i18n guidance](https://docs.dify.ai/en/develop-plugin/features-and-specs/plugin-types/multilingual-readme).

## Security and privacy notes

Medium risk because the plugin writes to a third-party service and sends user content to it. It has none of the high-risk capabilities: no command or code execution, no SQL, no SSH or SFTP, no file operations, no browser automation, no fetching of user-given URLs, no proxying, no bundled binaries.

**Where data goes.** The plugin makes HTTPS requests to one fixed host, `api.rollstack.com`, declared under `network.domains` in the manifest: `POST /public/v1/mcp` for every tool, and `GET /public/v1/me` to check the key when it is saved. No parameter can change the host or the path. `createReport` takes an optional `link` to a deck to import: the plugin passes it to Rollstack as data and never opens it. `exportReport` returns a download link that Rollstack creates, valid for 15 minutes, and the plugin does not fetch it either.

**Writes.** Four tools change things in the user's Rollstack organization: `createReport`, `sendReportMessage`, `startReportRun` and `updateReportSchedules`. They act as the Rollstack user who created the key, within the scopes that user gave it. No tool deletes anything or sends an email. A run that would email a report waits for the user to confirm it in Rollstack (the tool answers `confirmation-required` with the link), and a change the slides agent proposes to schedules, email settings or sending waits for the user's approval in Rollstack. The plugin cannot approve either.

**Inputs.** The 12 tool names are fixed in the code. Each Dify parameter fills one named field of one Rollstack tool, through a static table. Numbers are checked to be whole numbers, lists of ids and JSON lists are parsed strictly, and a value that doesn't parse fails before any request. Rollstack validates every call again and rejects fields it doesn't know.

**Credentials.** One Rollstack API key, a `secret-input` credential that Dify stores. It is sent only as a bearer token to `api.rollstack.com`, never in a URL, and never appears in a tool result or an error message (tests check this).

**Timeouts and retries.** 10 seconds to connect and 90 seconds to read, as Rollstack holds a call for up to 30 seconds while work finishes. A request is sent again at most twice, and only after a connection error or a 502, 503 or 504. Writes carry an idempotency key, so Rollstack runs a repeated call once. A read timeout is never retried.

**Personal data.** Rollstack's answers can hold the name and email address of members of the user's Rollstack organization: a report's owner, the members it is shared with, and who is told when a run fails. A message to the slides agent holds whatever the user writes. The plugin stores and logs nothing: it passes inputs to Rollstack and answers back to the Dify app. `PRIVACY.md` covers this and links to Rollstack's privacy policy. The plugin is not built to process sensitive personal data such as health, biometric or children's data: a report shows the business data its organization put in it.

**Dify permissions.** None: the manifest asks for no model, tool, app, node, storage or endpoint permission.

## Local validation

Package: `rollstack-0.0.1.difypkg`, 36 files, built with the Dify plugin CLI 0.6.15. Dependencies are pinned: `dify_plugin==0.11.1`, `requests==2.34.2`.

```text
$ dify plugin package ./integrations/dify -o rollstack-0.0.1.difypkg
INFO plugin packaged successfully output_path=rollstack-0.0.1.difypkg

$ python3 validator/validate-difypkg.py rollstack-0.0.1.difypkg --output-dir ./validation-report --pr-body-file pull-request.md
Local DIFYPKG Validation Summary

- Blocking failures: 0
- Warning categories: 2
- Environment/check execution failures: 0

| Check | Type | Status | Findings |
|---|---|---|---|
| `package_contents` | blocking | PASS | No findings. |
| `package_secrets` | blocking | PASS | No findings. |
| `package_binaries` | blocking | PASS | No findings. |
| `manifest_metadata` | blocking | PASS | No findings. |
| `readme_metadata` | blocking | PASS | No findings. |
| `package_dependencies` | blocking | PASS | No findings. |
| `python_compile` | blocking | PASS | No findings. |
| `python_safety` | warning | PASS | No findings. |
| `prohibited_financial_activity` | warning | PASS | No findings. |
| `access_domains` | warning | PASS | detected 1 outbound domain(s) by static scan: |
| `dependency_vulnerabilities` | warning | PASS | dependency source: requirements.txt (2 pinned, 0 unpinned) |
| `sensitive_capabilities` | blocking | PASS | No findings. |

Skipped checks:
- PR title/body language and template checks require GitHub PR metadata
- Marketplace duplicate-version check requires Marketplace/PR workflow context
- plugin install and upload-package tests are not run by this local validator

Warnings for review:
- access_domains:
  - detected 1 outbound domain(s) by static scan:
  -   api.rollstack.com [domain] (rollstack_client/mcp.py:19, rollstack_client/mcp.py:20)
- dependency_vulnerabilities:
  - dependency source: requirements.txt (2 pinned, 0 unpinned)
  - no known vulnerabilities in the pinned dependency set

Exit code: 0
```

Tests, on Python 3.12 with the pinned dependencies:

```text
$ python -m pytest tests
182 passed, 4 skipped, 2 warnings in 0.81s

$ ROLLSTACK_LIVE=1 python -m pytest tests/test_live.py
2 passed, 2 skipped in 0.62s
```

- The unit tests run every tool, loaded the way the plugin runtime loads it, against scripted Rollstack answers, and check the tool files against Rollstack's published tool definitions.
- The live tests call `api.rollstack.com`. The two that ran need no account: a tool call and the key check, each sent with a wrong key, are refused with a clear error. The two that were skipped need a Rollstack API key, because Rollstack's server lists its tools and opens a session only for a key: they check that the tool definitions the plugin was written from are still the ones the server lists, and that the plugin's client can open a session. They have not been run with a key. The definitions were last compared with the server's list on 18 November 2026, when it still listed its tools without a key, and they matched.
- The packaged plugin was also started with `dify plugin run` (the CLI's local runtime, which installs the pinned dependencies). Credential validation and tool calls reached Rollstack and returned the expected errors for a wrong key and for bad parameters.

## Reviewer notes

**Not yet run in a Dify workspace.** The checks above ran outside Dify: unit tests, calls to Rollstack's real server that need no account, and the Dify CLI's local runtime. The plugin has not yet been installed in a Dify Cloud or Community Edition workspace, and no call has been made through it with a real Rollstack key.

**Why an API key and not OAuth.** Rollstack's OAuth is OAuth 2.1 with PKCE, and its clients register themselves with Dynamic Client Registration. Dify's tool OAuth needs a client ID and secret set up for each Dify instance, since the redirect URI is per instance, and its two hooks (`_oauth_get_authorization_url`, `_oauth_get_credentials`) run as separate calls with nowhere to keep a PKCE verifier between them. An API key works the same on Dify Cloud and self-hosted, is scoped and revocable by the user, and is what Rollstack recommends for scripts and jobs, which a workflow is. Users who want to sign in with OAuth can add Rollstack's MCP server under Tools → MCP.

**Why the tools call Rollstack's MCP endpoint.** `POST /public/v1/mcp` is a documented, fixed HTTPS endpoint of Rollstack's API that takes one JSON-RPC `tools/call` per request. The plugin uses it rather than the REST routes because there Rollstack requires the user's confirmation for any call that emails people, whatever the kind of credential.

**How to test.** Rollstack is for teams that have an account: a company starts at https://www.rollstack.com/book-a-demo. Without a key, the key check and every tool return Rollstack's `api-key-invalid` error. With a key that has the three scopes, these steps work in any Rollstack account: they start from a new deck and need no existing report, template or data source.

1. `createReport` with a `name`, such as `Alphabet 2025`. It returns the new deck's `id`, used in every step below.
2. `sendReportMessage` with `content` set to `Build five slides on Alphabet's 2025 financial results`. It returns a `messageId`.
3. `getReportMessage` with that `messageId`, again while `status` is `queued` or `running`. The slides agent's reply is in `replies`. If it asks a question (a `clarification` reply), answer with another `sendReportMessage` that passes the same `chatId`.
4. `getReportContent` returns the titles and text of the slides.
5. `exportReport` with `format` set to `pdf` returns a `url` that downloads the deck, valid for 15 minutes.
6. `updateReportSchedules` with `schedules` set to `[{"frequency": "weekly", "cronExpression": "0 9 * * 1", "startDate": "2026-01-05T09:00:00Z", "timezone": "Europe/Paris"}]`, then `getReportSchedules`, which lists it. `updateReportSchedules` with `[]` removes it.
7. `startReportRun` returns a `runId`, and `getReportRun` follows the run until it ends.
8. `listReports` with `name` set to the deck's name finds it, `getReport` reads it, and `listTemplates` lists the templates a deck can be created in.

In an Agent app, the example requests in the README's Usage section do the same in plain words.

<!-- Optional: say here how a reviewer can get a test key, if you want to offer one. -->
