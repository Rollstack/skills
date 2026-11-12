---
name: rollstack-edit-deck
description: Change the slides of an existing Rollstack slide deck yourself, with the Rollstack MCP tools getReportSlideHtml, renderReportSlides, saveReportSlides and arrangeReportSlides, keeping what people changed in Rollstack's editor. Use when the user asks to reword, fix, add, move, remove, hide or show slides of a deck, or to undo a change to one.
license: MIT
---

# Rollstack edit deck

Rollstack's MCP server hands out the guide to changing a deck, so the guide always matches the tools. This skill only tells you where to start.

1. Find the report with `listReports`. It must be a slide deck (type `SlideDeck`).
2. Read its slides and their ids with `getReportContent`, and look at them with `getReportSlideImages`. "Slide 4" in the user's words is the fourth slide there.
3. Call `getReportDesign` for the report, without `layoutIds`, and follow "Changing a deck later" in its guide.
4. In short: to change what a slide says or shows, read its draft again with `getReportSlideHtml` every time, make each change in its `changedInRollstack` first, then your own, render it with `renderReportSlides` and save it under the same id with `saveReportSlides`. To move, remove, hide or show slides, call `arrangeReportSlides`.
5. A slide with no draft (`html` is `null`) was made by hand. Rewriting it drops that work: tell the user what would be lost, and rewrite it only when they agree.
6. Each change answers a `versionBeforeId`. To undo one, restore it with `restoreReportVersion`.

When `getReportDesign` is not among Rollstack's tools, they are not on for the user yet: ask Rollstack's slides agent with `sendReportMessage`, passing the slides' ids.
