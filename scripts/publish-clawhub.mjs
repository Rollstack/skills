// Publishes the plugin to ClawHub, OpenClaw's registry, as one bundle: the skills and the MCP server together.
// ClawHub takes a bundle with exactly one client's manifest and rejects a folder that has several, and this repo has
// one per client. So this stages a copy with only Claude's manifest in dist/clawhub, packs it and publishes the pack.
// It only previews unless you pass --publish. Run `clawhub login` first, or set CLAWHUB_TOKEN as the workflow does.
import { execFileSync } from "node:child_process"
import { cpSync, mkdirSync, readFileSync, rmSync, writeFileSync } from "node:fs"

const STAGING = "dist/clawhub"
// Pinned, like the Claude CLI in CI, so that a new CLI release can't change what a publish does
const CLAWHUB = "clawhub@0.26.0"
// The ClawHub owner handle the listing is published under: the token has to be allowed to publish for it, and the
// package's scope has to be that handle
const OWNER = "rollstack"
const NAME = `@${OWNER}/rollstack`
const REPO = "Rollstack/skills"
// OpenClaw reads a Claude bundle's MCP servers from .mcp.json, and ClawHub takes the listing's artwork from
// assets/icon.png
const FILES = [".claude-plugin/plugin.json", ".claude-plugin/icon.png", ".mcp.json", "skills", "assets/icon.png", "README.md", "LICENSE"]

const publish = process.argv.includes("--publish")
const { version, displayName, description } = JSON.parse(readFileSync(".claude-plugin/plugin.json", "utf8"))
const git = (...args) => execFileSync("git", args, { encoding: "utf8" }).trim()
const clawhub = (...args) => execFileSync("npx", ["--yes", CLAWHUB, ...args], { stdio: "inherit" })

rmSync(STAGING, { recursive: true, force: true })
mkdirSync(`${STAGING}/.claude-plugin`, { recursive: true })
mkdirSync(`${STAGING}/assets`, { recursive: true })
for (const path of FILES) cpSync(path, `${STAGING}/${path}`, { recursive: true })
// The copy's own package.json. ClawHub warns about a plugin without one, and takes the listing's one-line summary
// from its description: without it, from the first line of the README, which is only the repo's title. The name in
// it has to be the published one
writeFileSync(`${STAGING}/package.json`, `${JSON.stringify({ name: NAME, version, description }, null, 2)}\n`)

// An npm tarball is ClawHub's current package format, a ClawPack. A folder would be uploaded as a "legacy ZIP",
// which the listing flags as a compatibility risk
const [{ filename }] = JSON.parse(execFileSync("npm", ["pack", "--json", "--pack-destination", ".."], { cwd: STAGING, encoding: "utf8" }))

if (process.env.CLAWHUB_TOKEN) clawhub("login", "--token", process.env.CLAWHUB_TOKEN)
clawhub(
  // The ./ matters: ClawHub reads a bare dist/x.tgz as a GitHub owner/repo
  ...["package", "publish", `./dist/${filename}`, "--family", "bundle-plugin", "--bundle-format", "claude"],
  // Left to itself, ClawHub shows the manifest's id as the display name and reads no version from a bundle
  ...["--owner", OWNER, "--name", NAME, "--display-name", displayName, "--version", version],
  // It finds a folder's source in git by itself, but not a tarball's
  ...["--source-repo", REPO, "--source-commit", git("rev-parse", "HEAD")],
  ...["--source-ref", process.env.GITHUB_REF_NAME ?? git("rev-parse", "--abbrev-ref", "HEAD")],
  // --wait holds a real publish until ClawHub's security checks have passed or failed, so the run reports the outcome
  ...(publish ? ["--wait"] : ["--dry-run"])
)
