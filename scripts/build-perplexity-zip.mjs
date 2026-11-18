// Builds dist/rollstack-perplexity.zip, the package to upload to Perplexity Computer: plugin.json, mcp.json, the
// skills and the icon. Perplexity also imports the repo itself from GitHub, and reads the same files either way.
// So this first checks them against what its importer takes. What breaks a rule is often dropped without an error:
// a server entry with `headers`, for one, is skipped, and the plugin arrives with its skills and no connector.
// The rules: https://www.perplexity.ai/help-center/en/articles/2026100802-create-or-upload-a-custom-plugin
import { execFileSync } from "node:child_process"
import { cpSync, mkdirSync, readdirSync, readFileSync, rmSync, statSync } from "node:fs"

const STAGING = "dist/perplexity"
const ZIP = "dist/rollstack-perplexity.zip"
const SERVER_TYPES = ["streamable-http", "http", "sse"]
const MAX_DESCRIPTION = 1024
const MAX_SERVERS = 15
const MAX_SKILLS = 32
const MAX_FILES = 1000
const MAX_BYTES = 20 * 1024 * 1024

const readJson = (file) => JSON.parse(readFileSync(file, "utf8"))

const { name, description } = readJson("plugin.json")
if (typeof name !== "string" || !name) throw new Error("plugin.json: Perplexity rejects a plugin with no name")
// The manifest's limit is in UTF-8 bytes, a skill's in characters
if (description !== undefined && (typeof description !== "string" || Buffer.byteLength(description) > MAX_DESCRIPTION))
  throw new Error(`plugin.json: the description must be a string of at most ${MAX_DESCRIPTION} bytes`)

const servers = Object.entries(readJson("mcp.json").mcpServers)
if (servers.length > MAX_SERVERS) throw new Error(`mcp.json: Perplexity imports only the first ${MAX_SERVERS} servers`)
for (const [server, { type, url, headers }] of servers) {
  const skipped = (why) => new Error(`mcp.json: Perplexity would skip server "${server}": ${why}`)
  if (!SERVER_TYPES.includes(type)) throw skipped(`its type must be one of ${SERVER_TYPES.join(", ")}`)
  if (typeof url !== "string" || !url.startsWith("https://")) throw skipped("its url must start with https://")
  if (url.includes("${")) throw skipped("its url has a placeholder")
  // Each user signs in to a connector themselves, so Perplexity takes no server that needs a fixed header
  if (headers) throw skipped("it has headers")
}

const skills = readdirSync("skills", { withFileTypes: true }).filter((entry) => entry.isDirectory())
if (skills.length > MAX_SKILLS) throw new Error(`skills: ${skills.length} skills, and Perplexity takes ${MAX_SKILLS} per plugin`)
for (const { name: dir } of skills) {
  const file = `skills/${dir}/SKILL.md`
  const skillDescription = readFileSync(file, "utf8").match(/^description:\s*(.+)$/m)?.[1].trim() ?? ""
  if ([...skillDescription].length > MAX_DESCRIPTION)
    throw new Error(`${file}: the description is over ${MAX_DESCRIPTION} characters, which Perplexity rejects`)
}

// A GitHub import copies the whole repo, so its size limits are checked on every tracked file, not only the ZIP's
const tracked = execFileSync("git", ["ls-files", "-z"], { encoding: "utf8" }).split("\0").filter(Boolean)
const bytes = tracked.reduce((sum, file) => sum + (statSync(file, { throwIfNoEntry: false })?.size ?? 0), 0)
if (tracked.length > MAX_FILES || bytes > MAX_BYTES)
  throw new Error(`The repo has ${tracked.length} files and ${bytes} bytes: Perplexity takes ${MAX_FILES} files and ${MAX_BYTES} bytes`)

rmSync(STAGING, { recursive: true, force: true })
rmSync(ZIP, { force: true })
mkdirSync(STAGING, { recursive: true })
for (const path of ["plugin.json", "mcp.json", "skills", "assets", "LICENSE"]) cpSync(path, `${STAGING}/${path}`, { recursive: true })

// Zipped from inside the folder, so that plugin.json and mcp.json are at the root of the ZIP
execFileSync("zip", ["-X", "-q", "-r", "../rollstack-perplexity.zip", "."], { cwd: STAGING })
console.log(`Wrote ${ZIP} (${skills.length} skills, ${servers.length} MCP server)`)
