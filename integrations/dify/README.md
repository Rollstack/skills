# Rollstack

Create polished presentations with advanced charts, right from your favourite agent. Plug in your own data whenever you need it.

This plugin brings [Rollstack](https://www.rollstack.com) to Dify agents and workflows, with every tool of Rollstack's MCP server:

- Create a deck, have Rollstack's slides agent build or change its slides, then read, check and export them
- Bring in data when a slide calls for it: a CSV or Excel file, a spreadsheet, a dashboard or a warehouse table
- Keep a deck up to date: refresh it, schedule its updates and email it
- Share decks and folders, make one version of a deck per audience with bursts, and manage templates and versions

It needs a Rollstack account. If you don't have one yet, start at https://www.rollstack.com/book-a-demo.

## Setup

1. In Rollstack, open **Settings → Connected apps → API keys** (https://app.rollstack.com/settings/connected-apps) and create an API key with the scopes your app needs. The tables below give each tool's scope.
2. Copy the key. It starts with `rsk_` and Rollstack shows it only once.
3. In Dify, install the Rollstack plugin and authorize it: paste the key as its **Rollstack API key**. Dify saves the key once Rollstack has accepted it.
4. Add the Rollstack tools your app needs to an Agent app, or as tool nodes in a Workflow or Chatflow.

The key acts as the Rollstack user who created it, in that user's organization, and sees only what that user sees in Rollstack. Give it only the scopes your app uses:

| Scope | What it lets the tools do |
| --- | --- |
| `slide_decks:read` | Find and read decks, templates, folders, runs, schedules, emails and bursts, and export decks |
| `slide_decks:write` | Create, change, delete, share and schedule decks, add data to them and upload files |
| `slide_decks:run` | Message the slides agent, and start and cancel runs |
| `slide_decks:email` | Set up and send emails |
| `connections:read` | List the data sources connected in Rollstack, and search their dashboards, tables and spreadsheets |
| `smtp:read` | List the email servers emails can go out through |
| `users:read` | List the organization's members. Only owners and admins can give a key this scope |

An app that only reads decks needs `slide_decks:read` alone, and a key without `slide_decks:email` can't set up or send an email. You can revoke the key at any time in Rollstack, on the same page.

Add only the tools an app needs. A smaller set keeps an agent focused, and some models accept at most 128 tools in one request.

## Tools

The tools are Rollstack's own, with the names, descriptions and inputs of its [MCP server](https://docs.rollstack.com/api/mcp-server).

<!-- tools:start -->

The plugin has 121 tools, in the groups of Rollstack's API reference.

#### Reports

| Tool | What it does | Scope of the key |
| --- | --- | --- |
| `listReports` | The reports the user can see, of every type, newest first. | `slide_decks:read` |
| `getReport` | A report of any type with its schedules, who it is shared with and who is emailed when a run fails. lastRunStatus and running tell how its latest run went and whether one is going, and appUrl opens it in Rollstack. type tells which other endpoints work on it. | `slide_decks:read` |
| `convertReport` | Turns an older report of type GoogleSlides or MicrosoftPowerPoint, which updates a Google Slides presentation or a PowerPoint file in OneDrive or SharePoint, into a new report of type SlideDeck, as Convert to Rollstack slides in the app does. | `slide_decks:write` |
| `createReport` | Creates a report of type SlideDeck, in a folder the user can see when folderId is set. | `slide_decks:write` |
| `duplicateReport` | Copies a report of type SlideDeck with its slides, datasheets and email setup, as Duplicate in the app does, and answers the copy, which you own. | `slide_decks:write` |
| `updateReport` | Renames a report of any type, moves it, or changes its timezone or failure notifications. | `slide_decks:write` |
| `batchGetReports` | Up to 50 reports of any type at once, each as getReport answers it, with its schedules, who it is shared with, how its latest run went and whether one is going. | `slide_decks:read` |

#### Templates

| Tool | What it does | Scope of the key |
| --- | --- | --- |
| `listTemplates` | The templates the user can build a slide deck in: their company's, with who imported each and whether it is shared with the organization, then Rollstack's own. | `slide_decks:read` |
| `showTemplates` | Shows the user the templates they can build a slide deck in, each with a preview of its look, when the client can show a picker. | `slide_decks:read` |
| `createTemplate` | Imports a company template from a Google Slides presentation, as the app's Templates drawer does: its theme, slide masters, layouts and slide size, not its slides. | `slide_decks:write` |
| `updateTemplate` | Renames a company template, or shares it with the organization or stops sharing it, as the app's Templates drawer does. | `slide_decks:write` |
| `deleteTemplate` | Deletes a company template, as the app's Templates drawer does. | `slide_decks:write` |
| `applyReportTemplate` | Switches a report of type SlideDeck to a template's theme, slide masters, layouts and slide size, as the Templates drawer in the app does. | `slide_decks:write` |

#### Versions

| Tool | What it does | Scope of the key |
| --- | --- | --- |
| `listReportVersions` | The Version history of a report of type SlideDeck, newest first, as the app lists it: the versions Rollstack saved while it was edited, run or changed by the slides agent, and those saved with saveReportVersion, each with what saved it. | `slide_decks:read` |
| `saveReportVersion` | Saves a report of type SlideDeck as it is now in its Version history, with an optional name, so it can be restored later with restoreReportVersion, for example before a change the user may want to take back. | `slide_decks:write` |
| `restoreReportVersion` | Takes a report of type SlideDeck back to one of its versions, as Restore in the app's Version history does: its slides, and the datasheets when the version saved them, become the version's, replacing every change made since, and members with the report open see it at once. | `slide_decks:write` |

#### Chat

| Tool | What it does | Scope of the key |
| --- | --- | --- |
| `getReportMessage` | A message to the slides agent and its replies. | `slide_decks:read` |
| `sendReportMessage` | Asks the slides agent to build or change a report, or to answer a question about it, as the app's chat does. | `slide_decks:run` |
| `approveReportMessageProposal` | Approves the proposal of a settings_proposal or email_send_proposal reply, as its Approve button in the app's chat does: Rollstack makes the change, or sends the email. | `slide_decks:run` |
| `cancelReportMessage` | Stops a message to the slides agent: a queued one leaves the queue, and a running one stops. | `slide_decks:run` |
| `rejectReportMessageProposal` | Rejects the proposal of a settings_proposal or email_send_proposal reply, as its Reject button in the app's chat does: nothing changes. | `slide_decks:run` |

#### Memories

| Tool | What it does | Scope of the key |
| --- | --- | --- |
| `listMemories` | What the slides agent remembers of how the user likes their decks, as the app's Slides settings list it: each memory, the part of a deck it is about, and the report it holds for, if only one. | `slide_decks:read` |
| `createMemory` | Has the slides agent remember something of how the user likes their decks, for all their reports or one of them, as adding a preference in the app's Slides settings does. | `slide_decks:write` |
| `updateMemory` | Rewords a memory of the slides agent, or moves it to one report or all of them. | `slide_decks:write` |
| `deleteMemory` | Has the slides agent forget a memory: its runs stop reading it, as forgetting it in the app's Slides settings does. | `slide_decks:write` |

#### Runs

| Tool | What it does | Scope of the key |
| --- | --- | --- |
| `listReportRuns` | The runs of a report of any type that ended, newest first, with how each ended, what started it and why it failed, for questions such as why last night's update failed. | `slide_decks:read` |
| `getReportRun` | A run's status and the datasheets, or visualizations on a report of another type than SlideDeck, it could not refresh. | `slide_decks:read` |
| `listReportSyncs` | The syncs of a report other than a SlideDeck, such as a Google Slides presentation or an email report: each chart, table or text it pulls from a source, with how it did the last time it updated and why it failed. | `slide_decks:read` |
| `listRuns` | The runs that ended of every report the user can see, of any type, newest first, each with its report, for questions such as what failed overnight: pass status failed and since. | `slide_decks:read` |
| `startReportRun` | Refreshes a report's data, or only some of its datasheets, then repairs failed calculations and the slides with AI. | `slide_decks:run` |
| `batchStartReportRuns` | Starts a run of each of up to 50 reports of any type, as startReportRun does for one: each run updates its whole report, and a run of a report of another type than SlideDeck emails it when its email trigger is `all`. | `slide_decks:run` |
| `cancelReportRun` | Cancels a run of a report, whoever started it. | `slide_decks:run` |

#### Exports

| Tool | What it does | Scope of the key |
| --- | --- | --- |
| `getReportCloudExport` | Where a report is saved after its runs, in Google Drive, OneDrive or SharePoint, and how its last save went, with a link to the saved file. | `slide_decks:read` |
| `updateReportCloudExport` | Saves a report to a Google Drive, OneDrive or SharePoint folder after its runs, as the app's scheduling panel does, replacing the setting it had. | `slide_decks:write` |
| `exportReport` | Exports a report as PDF or PowerPoint and answers a download link valid for 15 minutes. | `slide_decks:read` |

#### Content

| Tool | What it does | Scope of the key |
| --- | --- | --- |
| `getReportContent` | What a viewer sees on a report's visible slides: titles, text, and each chart's and table's values. | `slide_decks:read` |
| `getReportDesign` | Start here to design a slide deck's slides yourself, as HTML. | `slide_decks:read` |
| `getReportSlideHtml` | The HTML drafts slides of a slide deck were made from, to change them and save them again with saveReportSlides under the same ids. | `slide_decks:read` |
| `getReportSlideImages` | Renders slides of a report as images, as viewers see them, so you can check how they look: text that overflows or overlaps, or a chart too small to read. | `slide_decks:read` |
| `showReport` | Shows a report to the user in a viewer with every visible slide, when the client can show one, to browse it or review the slides the slides agent changed: pass the replies' changedSlideIds to open on the first of them and mark them all. | `slide_decks:read` |
| `arrangeReportSlides` | Moves, removes, hides or shows slides of a slide deck, with nothing on them changed. | `slide_decks:write` |
| `updateReportTheme` | Changes a slide deck's theme: its colours, its heading font and its body font. | `slide_decks:write` |
| `renderReportSlides` | Renders slides you wrote as HTML on a slide deck's template, so you can design slides yourself instead of asking the slides agent. | `slide_decks:write` |
| `saveReportSlides` | Writes slides you wrote as HTML into a slide deck, as the slides agent's are: a draft sent under the id of a slide of the report replaces that slide where it is, any other is added right after the slide named in afterSlideId, or at the end without one, and every other slide stays. | `slide_decks:write` |

#### Uploaded files

| Tool | What it does | Scope of the key |
| --- | --- | --- |
| `getDataset` | An uploaded CSV file or Excel workbook. | `slide_decks:read` |
| `createDatasetUpload` | Answers a link to send a CSV file or an Excel workbook (.xlsx) to from a shell, as it is on disk, at most 10 MB: use it when the user gives you a file, in place of writing a CSV into createDataset, and for every workbook. | `slide_decks:write` |
| `createDocument` | Stores a document for the slides agent to read, such as a brief, a report or meeting notes, as when you attach one in the chat in the app: pass its id in documentIds on sendReportMessage. | `slide_decks:write` |
| `createDataset` | Stores a CSV for the slides agent to build slides from: a header row, then at least one data row, at most 10 MB. | `slide_decks:write` |
| `replaceDataset` | Replaces an uploaded CSV file's rows, or a workbook's content with a new .xlsx sent as multipart/form-data in the file field. | `slide_decks:write` |
| `deleteDataset` | Deletes an uploaded CSV file or workbook. | `slide_decks:write` |

#### Datasheets

| Tool | What it does | Scope of the key |
| --- | --- | --- |
| `getReportDataGuide` | Read this once before you add or shape the data of a report: how to send a CSV or an Excel workbook and pick the range of a sheet, how to check a figure with queryReportData, how to shape data with previewReportDatasheetChanges, renderReportSlides and saveReportDatasheetChanges, and the query model those changes write. | `slide_decks:read` |
| `listReportDatasheets` | The datasheets a report's charts and tables are built from, with their source and when each was last read. | `slide_decks:read` |
| `getReportDatasheet` | What a datasheet's data is written as: its query, in the shape set-query takes, its one SQL statement, or its join and the steps after it, and its formats. | `slide_decks:read` |
| `getReportDatasheetData` | The table a report's chart is drawn from: the datasheet's steps run over the copies stored at its sources' last reads; the source is never queried. | `slide_decks:read` |
| `addReportDatasheets` | Adds sources to a report as datasheets, and answers their ids in the order of the sources. | `slide_decks:write` |
| `removeReportDatasheet` | Removes a datasheet the report's slides no longer show, such as a source that was added and not used, or one whose read keeps failing. | `slide_decks:write` |
| `addReportDashboardElements` | Adds charts of a Tableau view or Power BI page the report holds as a picture, each as a datasheet of its own: its data, to read with getReportDatasheetData or queryReportData and draw on a slide, its picture, or both. | `slide_decks:write` |
| `previewReportDatasheetChanges` | Tries changes to a report's datasheets, to shape data before it goes on a slide: a new datasheet, a query, steps after a join, a read type, an unpivot. | `slide_decks:write` |
| `queryReportData` | Runs one read-only SQL query over the tables of a report's datasheets, to check a figure before it goes on a slide or to explore data before shaping it. | `slide_decks:write` |
| `saveReportDatasheetChanges` | Saves changes to a report's datasheets that you tried with previewReportDatasheetChanges: send the same changes with the revisions it answered. | `slide_decks:write` |

#### Parameters

| Tool | What it does | Scope of the key |
| --- | --- | --- |
| `getReportParameters` | A report's parameters, with which ones a burst can vary by, the dashboard filters and the datasheet columns a parameter can link, with the parameter that already links each. | `slide_decks:read` |
| `createReportParameter` | Creates a parameter of a report, linked to the dashboard filters and datasheet columns given, as the app's report parameters editor does. | `slide_decks:write` |
| `updateReportParameter` | Changes a parameter of a report, such as its value to show the report for another region, as the app's report parameters editor does: what you send changes and the rest stays. | `slide_decks:write` |
| `deleteReportParameter` | Deletes a parameter of a report, as the app's report parameters editor does. | `slide_decks:write` |

#### Sharing

| Tool | What it does | Scope of the key |
| --- | --- | --- |
| `getReportViews` | Who opened a report and how they read it, as its editors see under Views in the app: each person's visits, time spent and whether they opened it since its last successful run, who it is shared with but hasn't opened it since, and how far into it people read, slide by slide. | `slide_decks:read` |
| `shareReport` | Shares a report of any type with a member of the organization to view or edit it, or changes their permission. | `slide_decks:write` |
| `unshareReport` | Removes a user's share of a report of any type, and their access to its file when it updates one, as the app does. | `slide_decks:write` |
| `batchShareReports` | Shares up to 50 reports of any type with the same members, with the same permission, as shareReport does for one. | `slide_decks:write` |

#### Comments

| Tool | What it does | Scope of the key |
| --- | --- | --- |
| `listReportComments` | The comments on a report's slides, oldest first: each thread's first comment, whose threadId is null and which says whether the thread is resolved, then its replies. | `slide_decks:read` |
| `createReportComment` | Starts a comment thread on a slide of a report, or replies to a thread, as the user. | `slide_decks:write` |
| `resolveReportComment` | Resolves a comment thread once what it asked for is done, or opens it again, as the user. | `slide_decks:write` |

#### Schedules

| Tool | What it does | Scope of the key |
| --- | --- | --- |
| `getReportSchedules` | The schedules of a report of any type, with the syncs each updates and when each runs next, or null for one that never runs again. | `slide_decks:read` |
| `updateReportSchedules` | Replaces the schedules of a report of any type, at most 10; an empty list removes them all. | `slide_decks:write` |
| `batchUpdateReportSchedules` | Gives up to 50 reports of any type the same schedules, replacing all of each report's current ones, as updateReportSchedules does for one; an empty list removes them all. | `slide_decks:write` |

#### Email

| Tool | What it does | Scope of the key |
| --- | --- | --- |
| `listEmails` | The emails every report the user can see sent, of any type, newest first, each with its report, as the app's Email sends page lists them: pass status failed and since to find the ones that didn't go out, and burstId for one burst's. | `slide_decks:read` |
| `getReportEmailConfig` | Who a report's email goes to and how it is sent, for a report of any type. | `slide_decks:read` |
| `listReportEmails` | The emails a report of any type sent, newest first: when, how, to whom, and whether each was delivered, failed or opened. | `slide_decks:read` |
| `updateReportEmailConfig` | Sets who a report's email goes to and how it is sent, for a report of any type, replacing the settings this endpoint covers; Drive sharing, attachment folders and the email's subject and body stay as set in the app. | `slide_decks:email` |
| `sendReportEmail` | Emails a report to its recipients now, as it is. | `slide_decks:email` |
| `sendReportTestEmail` | Sends a report's email to the user only, and waits until it is sent. | `slide_decks:email` |

#### Bursts

| Tool | What it does | Scope of the key |
| --- | --- | --- |
| `listBursts` | The bursts of reports the user can see, newest first: those of Rollstack reports, whose variants differ by report parameters, and those of older reports such as Google Slides or PowerPoint files, whose variants differ by filters, as kind says. | `slide_decks:read` |
| `listBurstEmailConfigs` | A burst's email configurations, as the app's Burst email settings show them: each one email to its own recipients that includes every variant it selects, sent only when you send it. | `slide_decks:read` |
| `getBurstRun` | Where the runs of a burst's variants stand, such as those startBurstRun started, with how each variant's latest run ended. | `slide_decks:read` |
| `getBurstSettings` | A burst's settings, as its Settings tab in the app shows them: how its variants are named, and for an older report's burst, how each variant's run updates its file, what it does with empty charts, how it archives and how its filters match. | `slide_decks:read` |
| `listBurstVariants` | A burst's variants the user can open, oldest first, each with its values of the burst's parameters or filters, how its latest run went, whether one is going, and who its email goes to. adding lists the variants the user is still adding. | `slide_decks:read` |
| `getBurstVariantBatch` | A batch of variants being added to a burst, with where each variant stands: copied from the template report, then run once to fetch its data. | `slide_decks:read` |
| `listReportSyncFilters` | The filters of the dashboard an older report's sync reads, which a burst of the report can vary by: pass their ids in filters to createBurst. | `slide_decks:read` |
| `addBurstVariants` | Adds variants to a burst by their values of its report parameters, or of its filters for an older report's burst: each is a copy of the template report with its own values, then runs once to fetch its data. | `slide_decks:write` |
| `convertBurst` | Turns a burst of an older report, a Google Slides or PowerPoint file, into a new burst of Rollstack reports of type SlideDeck, as Convert to Rollstack slides does for one report. | `slide_decks:write` |
| `createBurst` | Makes a report the template of a new burst, and answers the burst, named after the report and with no variants yet. | `slide_decks:write` |
| `createBurstEmailConfig` | Adds an email configuration to a burst and answers it: one email to its recipients with the variants it selects, every variant by default. | `slide_decks:email` |
| `startBurstRun` | Starts a run of every variant of a burst, or of the variants passed, as startReportRun does for each: it refreshes the variant's data, and repairs a Rollstack report's slides with AI. | `slide_decks:run` |
| `sendBurstEmailConfig` | Sends a burst's email configuration now: one email to its recipients with each variant it selects. | `slide_decks:email` |
| `sendBurstVariantEmails` | Sends each variant's own email now, to its own recipients, as the app's Send does: every variant, or those passed. | `slide_decks:email` |
| `renameBurst` | Renames a burst and answers it, and with renameVariants its reports too. | `slide_decks:write` |
| `updateBurstVariantEmailSettings` | Changes how the variants' own emails are sent, as the app's Burst settings in its Emailing tab do: only the settings passed, on the template, whose settings new variants copy, and on the variants. | `slide_decks:email` |
| `updateBurstEmailConfig` | Changes the fields passed of a burst's email configuration and answers it. | `slide_decks:email` |
| `updateBurstSettings` | Changes the settings passed and answers them all. | `slide_decks:write` |
| `updateBurstVariantRecipients` | Sets who each variant's email goes to, replacing its to, cc and bcc. | `slide_decks:email` |
| `updateBurstFilters` | Replaces the filters an older report's burst varies by, then writes every variant's values into its syncs again, which can take a minute, and answers the burst. | `slide_decks:write` |
| `deleteBurst` | Deletes a burst with every report in it, the template included, as the app does, and can't be undone. | `slide_decks:write` |
| `deleteBurstEmailConfig` | Deletes a burst's email configuration. | `slide_decks:email` |
| `reapplyBurstFilters` | Writes each variant's filter values into its syncs again, as the app's Reapply does: after syncs were added to the template, or a filter changed on its dashboard. | `slide_decks:write` |
| `removeBurstVariants` | Removes variants of a burst by their ids, and deletes their reports. | `slide_decks:write` |
| `sendBurstEmailConfigTest` | Sends a burst's email configuration to you alone, to check how it looks before sending it. | `slide_decks:email` |

#### Connections

| Tool | What it does | Scope of the key |
| --- | --- | --- |
| `listConnections` | The data source connections the user can see, without their credentials: each one's type, name, settings such as its URL, owner, admins, default user and whether any user's access works. | `connections:read` |
| `searchDashboards` | The dashboards of a Looker, Metabase, Omni, Lightdash, Sigma, Tableau or Power BI connection whose name holds any word of query or its singular, in any case, at most 50: those the most of the organization's reports read first, copies, old and personal ones last, then most words first, read with the user's access to the connection. | `connections:read` |
| `getDashboard` | A dashboard of a Looker, Metabase, Omni, Lightdash, Sigma, Tableau or Power BI connection, read with the user's access to the connection (a Salesforce report has no tabs or charts to read, so add it with addReportDatasheets directly): its tabs, and the charts and filters of the tab tabId names, one of the ids in tabs (else the one the dashboard opens on, a Power BI report's or Sigma workbook's first page). | `connections:read` |
| `searchModels` | The models of a Looker, Power BI or Tableau connection whose name or group holds any word of query or its singular, in any case, at most 50: Looker explores grouped by LookML model, Power BI semantic models by workspace, Tableau published data sources by project, read with the user's access to the connection (on Tableau, their own Tableau user). | `connections:read` |
| `searchTables` | The tables and views of a Snowflake, Databricks or BigQuery connection whose full name, database.schema.table (project.dataset.table on BigQuery), holds any word of query, in any case, at most 50, read with the user's access to the connection, as its default user when one is set. | `connections:read` |

#### Spreadsheets

| Tool | What it does | Scope of the key |
| --- | --- | --- |
| `searchSpreadsheets` | The Google Sheets and Excel files the user added in the app whose name holds any word of query, in any case, most words first, at most 50. | `connections:read` |
| `getSpreadsheet` | A Google Sheets or Excel file the user added in the app, with its sheets, read with the user's own Google or Microsoft account. | `connections:read` |

#### SMTP connections

| Tool | What it does | Scope of the key |
| --- | --- | --- |
| `listSmtpConnections` | The user's SMTP connections and the ones shared with the organization, without their credentials. | `smtp:read` |

#### Folders

| Tool | What it does | Scope of the key |
| --- | --- | --- |
| `listFolders` | The folders the user can see, each with its parent, null at the top level, and the user's permission on it: null, view, edit or manage. | `slide_decks:read` |
| `getFolder` | A folder the user can see, with its parent and everyone who has access to it: its owner, the members it is shared with directly, and those who reach it through the folder it is nested in, each with their permission. | `slide_decks:read` |
| `createFolder` | Creates a folder owned by the user: at the top level, which only owners and admins of the organization may, or inside a folder the user owns or has manage on. | `slide_decks:write` |
| `updateFolder` | Renames a folder, or moves it into another folder or to the top level, with everything in it. | `slide_decks:write` |
| `shareFolder` | Shares a folder and everything in it with a member of the organization, or changes their permission, as Share in the app does. | `slide_decks:write` |
| `unshareFolder` | Removes a member's direct share of a folder, and their access to its reports' files in Drive unless they still reach the folder through a parent folder, as the app does. | `slide_decks:write` |

#### Feedback

| Tool | What it does | Scope of the key |
| --- | --- | --- |
| `submitFeedback` | Tells the Rollstack team about something the user asked for that you couldn't do: a tool or endpoint that is missing, a call that was refused or failed, or a task nothing covers. | Any key |

#### Members

| Tool | What it does | Scope of the key |
| --- | --- | --- |
| `listMembers` | The members of the organization, with their role, authentication role, insights access and whether they are active. | `users:read` (owners and admins) |

<!-- tools:end -->

The slides agent, exports, datasheets and slide content work on reports whose type is `SlideDeck`, the decks built in Rollstack. Older reports, which update a Google Slides, Google Docs, PowerPoint or Word file, can be listed, refreshed, scheduled, shared and emailed.

### What is different in Dify

- **Inputs.** A list, such as `slideIds` or the `to` addresses of an email, is text separated by commas, or a JSON array. A structured input, such as the `sources` of `addReportDatasheets` or the `schedules` of `updateReportSchedules`, is JSON text: its description gives the JSON Schema it follows.
- **Viewers.** In clients that can show them, `showReport` opens a viewer of the deck and `showTemplates` a template picker. Dify can't show them: `showReport` answers the slides' ids and titles, and `showTemplates` the templates. To look at slides, use `getReportSlideImages`, which returns each slide as an image file.
- **Uploads.** `createDatasetUpload` answers a link to send a file to from a shell, which a Dify agent doesn't have. An agent writes a CSV into `createDataset` instead. A workflow can send a file to the link with an HTTP Request node.
- **Left out.** Rollstack's server has four more tools, which only its own viewers call, never a model: `getTemplatePickerCovers`, `getReportMessageProgress`, `getReportViewerSlideImages`, and `confirmAction`, which runs a call you confirmed in its confirmation card.

## Usage

### In an Agent app

Add the tools, then ask in plain words. These requests work in any Rollstack account, one after the other, because they start from a new deck:

- "Create a new deck called Alphabet 2025, and ask the slides agent for five slides on Alphabet's 2025 financial results."
- "What do the slides say?"
- "Ask the slides agent to shorten the slide titles."
- "Add a slide with a bar chart of this table: region,revenue / North,120 / South,95 / West,80."
- "Export the deck as a PDF."
- "Update the deck every Monday at 9:00, Paris time, then show me its schedules."

The same requests work on the decks you already have: name the deck instead of creating one.

A system prompt along these lines helps the agent use the tools well:

```text
You help the user with their Rollstack decks. For a new deck, create it with createReport, in a template from
listTemplates when the user wants one. For an existing one, find it with listReports and check its type before you
act on it. To build or change slides, send the request to the slides agent with sendReportMessage, then call
getReportMessage until its status is completed or failed. If a reply asks questions, ask the user. If a reply
proposes a change, show the user what it changes, and approve or reject it only as they decide. For data the user
pastes, upload it with createDataset and add it to the deck with addReportDatasheets. Before any call that emails
people, shares, deletes or removes something, or replaces schedules, tell the user what it will do and wait for
their go. When a tool answers confirmation-required, give the user the link to confirm the call in Rollstack.
```

### In a Workflow or Chatflow

Each tool returns Rollstack's answer in its `json` output, and the fields of the answer as variables, such as `messageId`, `status`, `runId` or `url`, that later nodes can use directly. A variable the answer has no value for is empty.

Work that takes a while answers at once and is followed with a second tool:

1. `sendReportMessage` returns a `messageId`. Pass it to `getReportMessage`, which waits up to 30 seconds (`waitSeconds`) and returns the `status` and the `replies`. While the status is `queued` or `running`, call it again: put the node in a Loop that ends when the status is `completed`, `failed` or `cancelled`.
2. `startReportRun` returns a `runId`. Pass it to `getReportRun` in the same way, until the status is no longer `running`.

For example, to build a deck from your own data and export it: `createReport` (name) → `createDataset` (name, csv) → `addReportDatasheets` (id, sources) → `sendReportMessage` (id, content, datasheetIds) → `getReportMessage` in a Loop (id, messageId) → `exportReport` (id, format `pdf`), then use the `url` it returns within 15 minutes.

## Calls that email people or delete something

The plugin has every tool of Rollstack's MCP server, including the ones that email people or delete something. Rollstack holds some of them until you confirm them in Rollstack: the tool then answers `confirmation-required`, with the link to confirm at in `message`, and the call runs once you confirm it. The others run as soon as they are called. Dify has no step where you approve a tool call, so choose which of these tools an agent gets, and give the key only the scopes it needs.

<!-- careful:start -->

| Tool | What it does | Held until you confirm it in Rollstack |
| --- | --- | --- |
| `deleteTemplate` | Deletes a company template, as the app's Templates drawer does. | No |
| `approveReportMessageProposal` | Approves the proposal of a settings_proposal or email_send_proposal reply, as its Approve button in the app's chat does: Rollstack makes the change, or sends the email. | When it sends an email |
| `deleteMemory` | Has the slides agent forget a memory: its runs stop reading it, as forgetting it in the app's Slides settings does. | No |
| `startReportRun` | Refreshes a report's data, or only some of its datasheets, then repairs failed calculations and the slides with AI. | When the run would email the report |
| `batchStartReportRuns` | Starts a run of each of up to 50 reports of any type, as startReportRun does for one: each run updates its whole report, and a run of a report of another type than SlideDeck emails it when its email trigger is `all`. | When a run would email a report |
| `arrangeReportSlides` | Moves, removes, hides or shows slides of a slide deck, with nothing on them changed. | No: restoreReportVersion brings removed slides back |
| `deleteDataset` | Deletes an uploaded CSV file or workbook. | No |
| `removeReportDatasheet` | Removes a datasheet the report's slides no longer show, such as a source that was added and not used, or one whose read keeps failing. | No |
| `deleteReportParameter` | Deletes a parameter of a report, as the app's report parameters editor does. | No |
| `shareReport` | Shares a report of any type with a member of the organization to view or edit it, or changes their permission. | No: the member gets an email |
| `unshareReport` | Removes a user's share of a report of any type, and their access to its file when it updates one, as the app does. | No |
| `batchShareReports` | Shares up to 50 reports of any type with the same members, with the same permission, as shareReport does for one. | No: each member gets an email |
| `updateReportSchedules` | Replaces the schedules of a report of any type, at most 10; an empty list removes them all. | No |
| `batchUpdateReportSchedules` | Gives up to 50 reports of any type the same schedules, replacing all of each report's current ones, as updateReportSchedules does for one; an empty list removes them all. | No |
| `sendReportEmail` | Emails a report to its recipients now, as it is. | Yes |
| `sendReportTestEmail` | Sends a report's email to the user only, and waits until it is sent. | No: it goes to you alone |
| `startBurstRun` | Starts a run of every variant of a burst, or of the variants passed, as startReportRun does for each: it refreshes the variant's data, and repairs a Rollstack report's slides with AI. | When a run would email a variant |
| `sendBurstEmailConfig` | Sends a burst's email configuration now: one email to its recipients with each variant it selects. | Yes |
| `sendBurstVariantEmails` | Sends each variant's own email now, to its own recipients, as the app's Send does: every variant, or those passed. | Yes |
| `deleteBurst` | Deletes a burst with every report in it, the template included, as the app does, and can't be undone. | Yes |
| `deleteBurstEmailConfig` | Deletes a burst's email configuration. | No |
| `removeBurstVariants` | Removes variants of a burst by their ids, and deletes their reports. | Yes |
| `sendBurstEmailConfigTest` | Sends a burst's email configuration to you alone, to check how it looks before sending it. | No: it goes to you alone |
| `shareFolder` | Shares a folder and everything in it with a member of the organization, or changes their permission, as Share in the app does. | No: a member new to the folder gets an email |
| `unshareFolder` | Removes a member's direct share of a folder, and their access to its reports' files in Drive unless they still reach the folder through a parent folder, as the app does. | No |

<!-- careful:end -->

- **Proposals.** When you ask the slides agent for a change to a deck's schedules, email settings or parameters, or to send it by email, it replies with a proposal, which changes nothing until it is approved, with `approveReportMessageProposal` or in Rollstack.
- **Schedules.** A scheduled run emails the deck when its email is set up in Rollstack.
- **Undo.** A change the slides agent made can be taken back with `restoreReportVersion`, and the version saved before it.
- **Export links.** A link from `exportReport` works for 15 minutes, for anyone who has it.

## Connection requirements

- Dify must be able to make HTTPS requests to `api.rollstack.com`. The plugin calls no other host and receives no incoming requests.
- It works the same on Dify Cloud and on a self-hosted Dify. A self-hosted Dify behind a firewall needs outgoing access to that host.
- Authentication is the API key, sent as a bearer token on each request. Dify stores it encrypted with the plugin's credentials.
- To sign in with your Rollstack account instead of a key, add `https://api.rollstack.com/public/v1/mcp` under **Tools → MCP** in Dify: its MCP client signs in with OAuth.

Rollstack limits each key to 120 requests a minute, and each user to 6 messages to the slides agent, 10 exports and slide image renders, 10 imports and 5 email sends a minute. Past a limit, a tool fails with Rollstack's message, which says how long to wait.

## When a tool fails

A tool fails with the message Rollstack gave, followed by its code:

| Code | What to do |
| --- | --- |
| `api-key-invalid`, `api-key-expired` | Create a new key in Rollstack and replace it in the plugin's authorization |
| `api-key-missing-scope` | Create a key that has the scope the message names |
| `forbidden` | The message says why, such as needing edit access to the deck. Trying again won't help |
| `require-admin-permission` | Only an owner or admin of the organization can do this |
| `data-validation-error` | The message names the input that is wrong and why |
| `rate-limit-exceeded` | Wait the time the message gives |
| `query-already-running` | Another data query of yours is still running: wait for it, then call again |

## Source and support

- Source: https://github.com/Rollstack/skills/tree/main/integrations/dify (MIT license)
- Rollstack's API and MCP reference: https://docs.rollstack.com/api/mcp-server
- How keys and scopes work: https://rollstack.com/auth.md
- Questions and problems: support@rollstack.com, or https://github.com/Rollstack/skills/issues
- Privacy: [PRIVACY.md](https://github.com/Rollstack/skills/blob/main/integrations/dify/PRIVACY.md) and Rollstack's [privacy policy](https://www.rollstack.com/legal/privacy-policy)
