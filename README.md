# Rollstack skills

Agent skills for [Rollstack](https://www.rollstack.com), the AI presentation platform for business reporting. They teach an AI agent to do Rollstack jobs through its MCP server: build decks from a company's data, keep recurring reports refreshed, and send them.

| Skill | Use it to |
| --- | --- |
| [`rollstack-getting-started`](skills/rollstack-getting-started/SKILL.md) | Connect to Rollstack and find your way around a workspace |
| [`rollstack-build-deck`](skills/rollstack-build-deck/SKILL.md) | Build or change a deck from a dashboard, spreadsheet or CSV with the slides agent |
| [`rollstack-refresh-and-schedule`](skills/rollstack-refresh-and-schedule/SKILL.md) | Refresh a report and schedule its updates |
| [`rollstack-send-report-email`](skills/rollstack-send-report-email/SKILL.md) | Set a report's recipients, send a test, then email it once the user confirms |
| [`rollstack-slides`](skills/rollstack-slides/SKILL.md) | Write a deck's slides yourself as HTML, check them and save them |
| [`rollstack-data`](skills/rollstack-data/SKILL.md) | Bring a CSV or Excel file into a report and shape its data for charts |
| [`rollstack-update-deck`](skills/rollstack-update-deck/SKILL.md) | Refresh a deck with new data and fix the slides it made wrong |
| [`rollstack-edit-deck`](skills/rollstack-edit-deck/SKILL.md) | Change, add, move, remove, hide or show slides, keeping edits made in Rollstack |
| [`rollstack-brand-deck`](skills/rollstack-brand-deck/SKILL.md) | Give a deck a brand's colours and fonts |
| [`rollstack-check-figures`](skills/rollstack-check-figures/SKILL.md) | Check a deck's numbers against its data before it goes out |
| [`rollstack-burst-reports`](skills/rollstack-burst-reports/SKILL.md) | Make one version of a report per client, region or team, set each one's recipients, and run or send them |

## Install

**Claude Code plugin** (the MCP server and the skills together):

```
/plugin install rollstack --marketplace Rollstack/skills
```

Or in two steps, on Claude Code before 2.1.275:

```
/plugin marketplace add Rollstack/skills
/plugin install rollstack@rollstack
```

The plugin adds one remote MCP server, `https://api.rollstack.com/public/v1/mcp`, which you sign in to with your Rollstack account. It runs nothing on your machine.

**Pi package** (the MCP server and the skills together):

```bash
pi install git:github.com/Rollstack/skills
```

Then sign in from a Pi session with `/mcp login rollstack`.

**DeepSeek Harness bundle** (the MCP server and the skills together), added to the profile you run, such as `web`:

```bash
dsh plugin --profile web add github:Rollstack/skills
```

dsh can't sign in to an MCP server with OAuth yet, so it connects with an API key: create one in Rollstack under Settings → Connected apps, then start dsh with it in `ROLLSTACK_API_KEY`. Without the key, the skills still load and the MCP server stays off.

**Skills only**, with the [skills CLI](https://skills.sh):

```bash
npx skills add Rollstack/skills
```

Or copy a skill's folder into your agent's skills directory, such as `~/.claude/skills/` for Claude Code.

The repo is also an [Agent Plugin](https://agent-plugins.org): `plugin.json` and `mcp.json` at the root describe the same plugin for other clients. `.cursor-plugin/plugin.json` and `.grok-plugin/plugin.json` describe it for Cursor and Grok Build.

**Dify**: [`integrations/dify`](integrations/dify) is a tool plugin for [Dify](https://dify.ai) agents and workflows, with Rollstack's main tools and an API key for authentication. Its [README](integrations/dify/README.md) says how to set it up.

## Connect Rollstack

The skills call Rollstack's MCP server, `https://api.rollstack.com/public/v1/mcp`. Add it to your agent as a remote MCP server and sign in with your Rollstack account. For scripts, use an API key from Settings → Connected apps.

- How agents get credentials: https://rollstack.com/auth.md
- MCP server and API reference: https://docs.rollstack.com/api/mcp-server
- Everything for agents in one place: https://www.rollstack.com/llms.txt

## Discovery

`.well-known/agent-skills/index.json` lists the skills with their SHA-256 digests ([Agent Skills discovery](https://github.com/cloudflare/agent-skills-discovery-rfc), v0.2.0). Rollstack serves it at https://rollstack.com/.well-known/agent-skills/index.json.

## Contributing

Edit a skill, then run `node scripts/build-index.mjs` to update the index. CI fails when the index doesn't match the skills. See [AGENTS.md](AGENTS.md).

## License

[MIT](LICENSE)
