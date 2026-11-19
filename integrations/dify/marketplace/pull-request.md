# Plugin Submission

<!--
The body of the pull request to langgenius/dify-plugins that adds rollstack/rollstack/rollstack-0.0.1.difypkg.
Title: add rollstack 0.0.1
Before opening it:
1. Refresh the tools with a Rollstack API key that has every scope, made by an owner or admin, in ROLLSTACK_API_KEY
   ("Refresh the tools" in DEVELOPMENT.md), so the plugin has the tools as Rollstack's server lists them on that day.
   Then run the live tests with the same key, and replace their output and the line about them under "Local validation".
2. Run the plugin in a Dify workspace with a Rollstack API key (see "Try it in Dify" in DEVELOPMENT.md), following the
   "How to test" steps under "Reviewer notes", and correct any step that doesn't go as written.
3. Tick the three boxes left open under "Required checks": the first two are your own statement, the third is that run.
4. Replace the "Not yet run in a Dify workspace" paragraph under "Reviewer notes" with what you tested and on which Dify version.
5. Package and validate again if anything changed, and replace the output under "Local validation".
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

New plugin for [Rollstack](https://www.rollstack.com): build polished presentations using AI, with advanced charts and data connections built in. No Marketplace plugin connects to Rollstack today.

It gives a Dify agent or workflow the 121 tools of Rollstack's [MCP server](https://docs.rollstack.com/api/mcp-server) that a model calls, the same tools every other client of that server gets, with Rollstack's own names, inputs and descriptions:

- Create a deck, have Rollstack's slides agent build or change it, read its reply, and check, edit, export and restore the slides
- Bring in data: upload a CSV file or a document, find a dashboard, warehouse table or spreadsheet of a data source connected in Rollstack, add it to a deck, and shape or query its data
- Refresh decks, schedule their updates, set up and send their emails, and follow runs and sent emails
- Share decks and folders, manage templates, comments and the slides agent's memories, and make one version of a deck per audience with bursts

The four tools the server has beyond these are called only by its own viewers, never by a model, and Dify can't show those viewers: `getTemplatePickerCovers`, `getReportMessageProgress`, `getReportViewerSlideImages` and `confirmAction`.

Each tool returns Rollstack's answer as JSON, and its fields as workflow variables (`output_schema`), so a workflow can chain the tools, for example `sendReportMessage` to `getReportMessage`. Images of slides come back as image files.

Authentication is a Rollstack API key that the user creates in Rollstack with the scopes they choose.

## Risk level

- [ ] Low risk
- [ ] Medium risk
- [x] High risk

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

High risk, because through Rollstack some tools run SQL, send email, delete data and return personal data. The plugin itself runs no code or commands, opens no files, automates no browser, fetches no URL it is given, proxies nothing and bundles no binaries: every tool is one HTTPS request to Rollstack, which does the work.

**SQL, run by Rollstack.** `queryReportData` runs one read-only SQL query over the copies of a deck's data that Rollstack keeps, at most 200 rows and 30 seconds, never against a source. `previewReportDatasheetChanges` and `saveReportDatasheetChanges` define a deck's data with a query, a SQL statement or a join over those copies, and `renderReportSlides` draws slides with such unsaved changes. A deck can also take a Snowflake, Databricks or BigQuery table as a source with `addReportDatasheets`, which Rollstack's slides agent then queries in the warehouse with SQL, with the user's own access to that connection. The plugin passes the SQL to Rollstack as text and never connects to a database.

**Email.** Tools can set who a deck's email goes to and send it (`updateReportEmailConfig`, `sendReportEmail`, and their burst counterparts). Over the MCP endpoint the plugin calls, Rollstack holds every call that emails people until the user confirms it in Rollstack: the tool answers `confirmation-required` with the link to confirm at, and nothing is sent before. This covers sending an email, a run that would email, and approving a proposal of the slides agent to send one. Sharing a deck or folder emails the member at once (`shareReport`, `batchShareReports`, `shareFolder`), and the test sends go to the user alone.

**Deletes.** Rollstack holds deleting a burst and removing its variants until the user confirms them, like emails. Other deletes run at once: a template, a memory, an uploaded file, a datasheet, a parameter, a burst's email configuration, a share, and removing slides (`arrangeReportSlides`), which `restoreReportVersion` can undo. The README lists these calls, and which ones Rollstack holds. Dify has no step to approve a tool call, so the README asks app builders to give an agent only the tools it needs and the key only the scopes it needs: a key without `slide_decks:email` can set up or send no email, and a key with only `slide_decks:read` changes nothing.

**Security boundary.** The plugin makes HTTPS requests to one fixed host, `api.rollstack.com`, declared under `network.domains` in the manifest: `POST /public/v1/mcp` for every tool, and `GET /public/v1/me` to check the key when it is saved. No parameter can change the host or the path. Links a tool takes, such as a deck to import in `createReport` or a picture in a message to the slides agent, are passed to Rollstack as data: the plugin never opens them. `exportReport` and `createDatasetUpload` answer links that Rollstack creates, and the plugin fetches neither.

**Input constraints.** The tool names are fixed in the package. Each Dify parameter fills one named field of one Rollstack tool, through a static table generated from Rollstack's tool definitions. Numbers, booleans, lists and JSON inputs are validated before any request, and a value that doesn't parse fails there. Rollstack validates every call again against its schema and rejects fields it doesn't know.

**Credentials.** One Rollstack API key, a `secret-input` credential that Dify stores. It acts as the Rollstack user who created it, within the scopes they gave it. It is sent only as a bearer token to `api.rollstack.com`, never in a URL, and never appears in a tool result or an error message (tests check this).

**Timeouts and retries.** 10 seconds to connect and 90 seconds to read, as Rollstack holds a call for up to 30 seconds while work finishes. A request is sent again at most twice, and only after a connection error or a 502, 503 or 504. Writes carry an idempotency key, so Rollstack runs a repeated call once. A read timeout is never retried.

**Personal data.** Rollstack's answers can hold names and email addresses of members of the user's Rollstack organization: a deck's owner, the members it is shared with, its email recipients, and, for an owner's or admin's key with `users:read`, the member list (`listMembers`). Data the user uploads, queries or adds from a source, and the messages they write to the slides agent, hold whatever they put in them. The plugin stores and logs nothing: it passes inputs to Rollstack and answers back to the Dify app. `PRIVACY.md` covers this and links to Rollstack's privacy policy. The plugin is not built for sensitive personal data such as health, biometric or children's data.

**Dify permissions.** None: the manifest asks for no model, tool, app, node, storage or endpoint permission.

## Local validation

Package: `rollstack-0.0.1.difypkg`, 255 files, built with the Dify plugin CLI 0.6.15. Dependencies are pinned: `dify_plugin==0.11.1`, `requests==2.34.2`.

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
731 passed, 4 skipped, 2 warnings in 2.13s

$ ROLLSTACK_LIVE=1 python -m pytest tests/test_live.py
2 passed, 2 skipped in 0.77s
```

- The unit tests run every tool, loaded the way the plugin runtime loads it, against scripted Rollstack answers. They check that the plugin has every tool Rollstack's server lists but the four its viewers call, and that each tool's name, inputs and descriptions are Rollstack's.
- The live tests call `api.rollstack.com`. The two that ran need no account: a tool call and the key check, each sent with a wrong key, are refused with a clear error. The two that were skipped need a Rollstack API key: they check that the tool definitions the plugin was generated from are still the ones the server lists, and that the plugin's client can open a session. They have not been run with a key. The definitions are the ones the server listed on 17 November 2026. On 18 November, 115 of the 118 described in Rollstack's public OpenAPI document still matched it; `renderReportSlides`, `previewReportDatasheetChanges` and `saveReportDatasheetChanges` had gained an optional field in their datasheet changes.
- The packaged plugin was also started with `dify plugin run` (the CLI's local runtime, which installs the pinned dependencies and reads every tool's declaration). Credential validation and tool calls reached Rollstack and returned the expected errors for a wrong key and for bad parameters.

## Reviewer notes

**Not yet run in a Dify workspace.** The checks above ran outside Dify: unit tests, calls to Rollstack's real server that need no account, and the Dify CLI's local runtime. The plugin has not yet been installed in a Dify Cloud or Community Edition workspace, and no call has been made through it with a real Rollstack key.

**121 tools.** The plugin has every tool of Rollstack's MCP server that a model calls, so that a Dify app can do what any other client of that server can. App builders choose which tools an agent gets, and some models accept at most 128 tools in one request.

**Lists and structured inputs.** Dify has no list or object parameters for a plugin's tools. A list of strings, such as slide ids or email addresses, is text separated by commas, or a JSON array. Any other structured input, such as the `sources` of `addReportDatasheets`, is JSON text, and its description gives the JSON Schema it follows.

**Why an API key and not OAuth.** Rollstack's OAuth is OAuth 2.1 with PKCE, and its clients register themselves with Dynamic Client Registration. Dify's tool OAuth needs a client ID and secret set up for each Dify instance, since the redirect URI is per instance, and its two hooks (`_oauth_get_authorization_url`, `_oauth_get_credentials`) run as separate calls with nowhere to keep a PKCE verifier between them. An API key works the same on Dify Cloud and self-hosted, is scoped and revocable by the user, and is what Rollstack recommends for scripts and jobs, which a workflow is. Users who want to sign in with OAuth can add Rollstack's MCP server under Tools → MCP.

**Why the tools call Rollstack's MCP endpoint.** `POST /public/v1/mcp` is a documented, fixed HTTPS endpoint of Rollstack's API that takes one JSON-RPC `tools/call` per request. The plugin uses it rather than the REST routes because there Rollstack holds any call that emails people or deletes decks until the user confirms it, whatever the kind of credential.

**How to test.** Rollstack is for teams that have an account: start at https://www.rollstack.com/book-a-demo. Without a key, the key check and every tool return Rollstack's `api-key-invalid` error. With a key that has the scopes `slide_decks:read`, `slide_decks:write`, `slide_decks:run` and `slide_decks:email`, these steps work in any Rollstack account: they start from a new deck and need no existing deck, template or data source.

1. `createReport` with a `name`, such as `Alphabet 2025`. It returns the new deck's `id`, used in every step below.
2. `sendReportMessage` with `content` set to `Build five slides on Alphabet's 2025 financial results`. It returns a `messageId`.
3. `getReportMessage` with that `messageId`, again while `status` is `queued` or `running`. The slides agent's reply is in `replies`. If it asks a question (a `clarification` reply), answer with another `sendReportMessage` that passes the same `chatId`.
4. `getReportContent` returns the titles and text of the slides, and `getReportSlideImages` with the reply's `changedSlideIds` returns them as image files.
5. `createDataset` with `name` set to `Revenue` and `csv` set to `region,revenue` followed by the rows `North,120`, `South,95` and `West,80`, one per line. It returns the file's `id`. `addReportDatasheets` with `sources` set to `[{"datasetId": "<that id>"}]` returns a datasheet id, and `sendReportMessage` with `content` set to `Add a slide with a bar chart of revenue by region` and `datasheetIds` set to it adds the slide.
6. `queryReportData` with `sql` set to `SELECT SUM(revenue) AS total FROM "<datasheet id>"` returns the total.
7. `exportReport` with `format` set to `pdf` returns a `url` that downloads the deck, valid for 15 minutes.
8. `updateReportSchedules` with `schedules` set to `[{"frequency": "weekly", "cronExpression": "0 9 * * 1", "startDate": "2026-01-05T09:00:00Z", "timezone": "Europe/Paris"}]`, then `getReportSchedules`, which lists it. `updateReportSchedules` with `[]` removes it.
9. `updateReportEmailConfig` with `to` set to your own address, then `sendReportEmail`. Rollstack holds the send: the tool answers `confirmation-required` with the link to confirm at, and nothing is sent until you confirm there.
10. `listReports` with `name` set to the deck's name finds it, `getReport` reads it, and `listTemplates` lists the templates a deck can be created in.

In an Agent app, the example requests in the README's Usage section do the same in plain words.

<!-- Optional: say here how a reviewer can get a test key, if you want to offer one. -->
