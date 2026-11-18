// Builds dist/rollstack-chatgpt.zip, the package to upload to OpenAI's plugin portal: plugin.json, the skills, the
// icon, and mcp.json with ChatGPT's sign-in settings added to its server entries.
// Those settings can't be in the repo's own mcp.json. OpenAI reads them from an `extensions` object inside a server
// entry, but Agent Plugins v1 allows only `type`, `url` and `headers` there, and clients that follow it, such as
// Hermes, skip a server that has anything else. So they live in chatgpt-mcp-extensions.json, keyed by server name.
import { execFileSync } from "node:child_process"
import { cpSync, mkdirSync, readFileSync, rmSync, writeFileSync } from "node:fs"

const STAGING = "dist/chatgpt"
const ZIP = "dist/rollstack-chatgpt.zip"
const SERVER_FIELDS = ["type", "url", "headers"]

const readJson = (file) => JSON.parse(readFileSync(file, "utf8"))

const mcp = readJson("mcp.json")
for (const [name, server] of Object.entries(mcp.mcpServers)) {
  const extra = Object.keys(server).filter((field) => !SERVER_FIELDS.includes(field))
  if (extra.length)
    throw new Error(`mcp.json: server "${name}" has ${extra.join(", ")}: client-specific settings go in scripts/chatgpt-mcp-extensions.json`)
}

for (const [name, extensions] of Object.entries(readJson("scripts/chatgpt-mcp-extensions.json"))) {
  if (!mcp.mcpServers[name]) throw new Error(`scripts/chatgpt-mcp-extensions.json: no server "${name}" in mcp.json`)
  mcp.mcpServers[name].extensions = extensions
}

// Only this script's own output: dist also holds the other clients' packages
rmSync(STAGING, { recursive: true, force: true })
rmSync(ZIP, { force: true })
mkdirSync(STAGING, { recursive: true })
for (const path of ["plugin.json", "skills", "assets", "LICENSE"]) cpSync(path, `${STAGING}/${path}`, { recursive: true })
writeFileSync(`${STAGING}/mcp.json`, `${JSON.stringify(mcp, null, 2)}\n`)

// Zipped from inside the folder, so that plugin.json and mcp.json are at the root of the ZIP
execFileSync("zip", ["-X", "-q", "-r", "../rollstack-chatgpt.zip", "."], { cwd: STAGING })
console.log(`Wrote ${ZIP}`)
