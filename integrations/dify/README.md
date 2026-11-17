# Rollstack

[Rollstack](https://www.rollstack.com) is the AI presentation platform for business reporting: every report is a slide deck built from your company's data, in your own template, and kept up to date.

This plugin lets a Dify agent or workflow work with your Rollstack reports:

- Find reports and read what their slides say
- Ask Rollstack's slides agent to build or change a deck, and read its reply
- Refresh a report from its data sources
- Set when a report updates on its own
- Export a report as a PDF or PowerPoint file

It needs a Rollstack account. A company that doesn't use Rollstack yet can start at https://www.rollstack.com/book-a-demo.

## Setup

1. In Rollstack, open **Settings → Connected apps → API keys** (https://app.rollstack.com/settings/connected-apps) and create an API key with the scopes `slide_decks:read`, `slide_decks:write` and `slide_decks:run`.
2. Copy the key. It starts with `rsk_` and Rollstack shows it only once.
3. In Dify, install the Rollstack plugin and authorize it: paste the key as its **Rollstack API key**. Dify saves the key once Rollstack has accepted it.
4. Add the Rollstack tools to an Agent app, or as tool nodes in a Workflow or Chatflow.

The key acts as the Rollstack user who created it, in that user's organization, and sees only what that user sees in Rollstack. Give it only the scopes your app uses: an app that only reads reports needs `slide_decks:read` alone. You can revoke the key at any time in Rollstack, on the same page.

## Tools

The tools are Rollstack's own, with the names and inputs of its [MCP server and API](https://docs.rollstack.com/api/mcp-server).

| Tool | What it does | Scope of the key |
| --- | --- | --- |
| `listReports` | Lists the reports you can see, filtered by name, type or folder | `slide_decks:read` |
| `getReport` | Reads one report: its type, schedules, latest run and link in Rollstack | `slide_decks:read` |
| `getReportContent` | Reads what the slides show: titles, text, and the values in charts and tables | `slide_decks:read` |
| `listTemplates` | Lists the templates a new deck can be built in | `slide_decks:read` |
| `createReport` | Creates a deck, empty in a template or imported from a PowerPoint or Google Slides link | `slide_decks:write` |
| `sendReportMessage` | Asks the slides agent to build or change a deck, or to answer a question about it | `slide_decks:run` |
| `getReportMessage` | Reads the slides agent's reply to a message | `slide_decks:read` |
| `startReportRun` | Refreshes a report's data and repairs its slides | `slide_decks:run` |
| `getReportRun` | Reads how a run is going and what it could not refresh | `slide_decks:read` |
| `getReportSchedules` | Lists a report's schedules | `slide_decks:read` |
| `updateReportSchedules` | Replaces a report's schedules | `slide_decks:write` |
| `exportReport` | Exports a report as PDF or PowerPoint and returns a download link | `slide_decks:read` |

The slides agent, exports and slide content work on reports whose type is `SlideDeck`, the decks built in Rollstack. Older reports, which update a Google Slides, Google Docs, PowerPoint or Word file, can be listed, refreshed and scheduled.

## Usage

### In an Agent app

Add the tools, then ask in plain words. For example:

- "Find my Q3 business review and add a slide on the top 5 accounts by revenue."
- "Refresh the weekly sales report and tell me what could not be refreshed."
- "Update the board report every Monday at 9:00, Paris time."
- "Export the Q3 business review as a PDF."

A system prompt along these lines helps the agent use them well:

```text
You help the user with their Rollstack reports. Find a report with listReports before you act on it, and check its
type. To build or change slides, send the request to the slides agent with sendReportMessage, then call
getReportMessage until its status is completed or failed. If a reply asks questions, ask the user. If a reply
proposes a change, tell the user to review it in Rollstack: nothing changes until they approve it there. Before you
replace schedules, read the current ones and show the user the full list you are about to save.
```

### In a Workflow or Chatflow

Each tool returns Rollstack's answer in its `json` output, and its main fields as variables, such as `messageId`, `status`, `runId` or `url`, that later nodes can use directly.

Work that takes a while answers at once and is followed with a second tool:

1. `sendReportMessage` returns a `messageId`. Pass it to `getReportMessage`, which waits up to 30 seconds (`waitSeconds`) and returns the `status` and the `replies`. While the status is `queued` or `running`, call it again: put the node in a Loop that ends when the status is `completed`, `failed` or `cancelled`.
2. `startReportRun` returns a `runId`. Pass it to `getReportRun` in the same way, until the status is no longer `running`.

Lists of ids, such as `slideIds`, are text separated by commas. `schedules` and `answers` are JSON text: an array of objects, described in each parameter.

For example, to export a deck once it has refreshed: `listReports` (name) → `startReportRun` (id) → `getReportRun` in a Loop (id, runId) → `exportReport` (id, format `pdf`), then use the `url` it returns within 15 minutes.

## What waits for you

The plugin has no tool that emails people or deletes anything, and Rollstack keeps these decisions with you:

- **Proposals.** When you ask the slides agent for a change to a report's schedules, email settings or parameters, or to send it by email, it replies with a proposal. Nothing changes until you approve it in Rollstack, at the `appUrl` of the reply. The plugin cannot approve a proposal.
- **Runs that email.** A run of an older report whose email goes out on every run would email its recipients. Rollstack starts such a run only once you confirm it in Rollstack: `startReportRun` then answers `confirmation-required` with the link to confirm at, as `code` and `message`.
- **Schedules.** `updateReportSchedules` replaces all the schedules of a report, and an empty list removes them. A scheduled run emails the report when you have set up its email in Rollstack.
- **Export links.** A link from `exportReport` works for 15 minutes, for anyone who has it.

## Connection requirements

- Dify must be able to make HTTPS requests to `api.rollstack.com`. The plugin calls no other host and receives no incoming requests.
- It works the same on Dify Cloud and on a self-hosted Dify. A self-hosted Dify behind a firewall needs outgoing access to that host.
- Authentication is the API key, sent as a bearer token on each request. Dify stores it encrypted with the plugin's credentials.

Rollstack limits each key to 120 requests a minute, and each user to 6 messages to the slides agent, 10 exports and 10 imports a minute. Past a limit, a tool fails with Rollstack's message, which says how long to wait.

## When a tool fails

A tool fails with the message Rollstack gave, followed by its code:

| Code | What to do |
| --- | --- |
| `api-key-invalid`, `api-key-expired` | Create a new key in Rollstack and replace it in the plugin's authorization |
| `api-key-missing-scope` | Create a key that has the scope the message names |
| `forbidden` | The message says why, such as needing edit access to the report. Trying again won't help |
| `data-validation-error` | The message names the parameter that is wrong and why |
| `rate-limit-exceeded` | Wait the time the message gives |

## More tools

This plugin covers the main jobs. Rollstack's MCP server has every tool, such as adding data sources, report emails and bursts: in Dify, add `https://api.rollstack.com/public/v1/mcp` under **Tools → MCP** and sign in with Rollstack.

## Source and support

- Source: https://github.com/Rollstack/skills/tree/main/integrations/dify (MIT license)
- Rollstack's API and MCP reference: https://docs.rollstack.com/api/mcp-server
- How keys and scopes work: https://rollstack.com/auth.md
- Questions and problems: support@rollstack.com, or https://github.com/Rollstack/skills/issues
- Privacy: [PRIVACY.md](https://github.com/Rollstack/skills/blob/main/integrations/dify/PRIVACY.md) and Rollstack's [privacy policy](https://www.rollstack.com/legal/privacy-policy)
