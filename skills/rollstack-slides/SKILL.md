---
name: rollstack-slides
description: Design slides for a Rollstack slide deck yourself, as HTML, check each one with the Rollstack MCP tool renderReportSlides and save them with saveReportSlides. Use when the user asks you to build or redesign slides in Rollstack and wants you to write them, instead of asking Rollstack's own slides agent.
license: MIT
---

# Rollstack slides

Rollstack's MCP server hands out the guide to writing slides, fitted to the report you work on, so the guide always matches the tools. This skill only tells you where to start.

1. Find the report with `listReports`, or create it with `createReport`. It must be a slide deck (type `SlideDeck`). Before creating one, list the templates with `listTemplates` and pass one as `templateId`: when the organization has company templates, ask the user which one to use, even when there is only one; otherwise Rollstack's own.
2. Call `getReportDesign` for the report, without `layoutIds`. Its answer holds the guide: read it and follow it.
3. In short: you write each slide as one `<section>` of HTML, check it with `renderReportSlides` until it has no issues, and save it with `saveReportSlides`.
4. When the slides need the user's data, a CSV or an Excel workbook, call `getReportDataGuide` once before you add it: it covers sending the file, picking a range, checking figures and reshaping data.
