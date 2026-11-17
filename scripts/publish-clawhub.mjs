// Publishes the plugin to ClawHub, OpenClaw's registry, as one bundle: the skills and the MCP server together.
// ClawHub takes a bundle with exactly one client's manifest and rejects a folder that has several, and this repo has
// one per client. So this stages a copy with only Claude's manifest in dist/clawhub and publishes that copy.
// It only previews unless you pass --publish. Run `clawhub login` first, or set CLAWHUB_TOKEN as the workflow does.
import { execFileSync } from "node:child_process"
import { cpSync, mkdirSync, readFileSync, rmSync } from "node:fs"

const STAGING = "dist/clawhub"
// Pinned, like the Claude CLI in CI, so that a new CLI release can't change what a publish does
const CLAWHUB = "clawhub@0.26.0"
// The ClawHub owner handle the listing is published under: the token has to be allowed to publish for it, and the
// package's scope has to be that handle
const OWNER = "rollstack"
const NAME = `@${OWNER}/rollstack`
// OpenClaw reads a Claude bundle's MCP servers from .mcp.json, and ClawHub takes the listing's artwork from
// assets/icon.png
const FILES = [".claude-plugin/plugin.json", ".claude-plugin/icon.png", ".mcp.json", "skills", "assets/icon.png", "README.md", "LICENSE"]

const publish = process.argv.includes("--publish")
const { version, displayName } = JSON.parse(readFileSync(".claude-plugin/plugin.json", "utf8"))
const clawhub = (...args) => execFileSync("npx", ["--yes", CLAWHUB, ...args], { stdio: "inherit" })

rmSync(STAGING, { recursive: true, force: true })
mkdirSync(`${STAGING}/.claude-plugin`, { recursive: true })
mkdirSync(`${STAGING}/assets`, { recursive: true })
for (const path of FILES) cpSync(path, `${STAGING}/${path}`, { recursive: true })

if (process.env.CLAWHUB_TOKEN) clawhub("login", "--token", process.env.CLAWHUB_TOKEN)
clawhub(
  ...["package", "publish", STAGING, "--family", "bundle-plugin", "--bundle-format", "claude"],
  // Left to itself, ClawHub names the package after the staging folder, shows the manifest's id as its display name,
  // reads no version from a bundle, and records dist/clawhub, which isn't in the repo, as the source path
  ...["--owner", OWNER, "--name", NAME, "--display-name", displayName, "--version", version, "--source-path", "."],
  // --wait holds a real publish until ClawHub's security checks have passed or failed, so the run reports the outcome
  ...(publish ? ["--wait"] : ["--dry-run"])
)
