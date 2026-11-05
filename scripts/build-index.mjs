// Writes .well-known/agent-skills/index.json (Agent Skills discovery v0.2.0) from skills/*/SKILL.md: each skill's
// name and description from its front matter, its raw GitHub URL and the SHA-256 of its bytes.
// `--check` writes nothing and fails when the committed index differs, so CI catches a skill edited without it.
import { createHash } from "node:crypto"
import { readdirSync, readFileSync, writeFileSync } from "node:fs"

const RAW_BASE = "https://raw.githubusercontent.com/Rollstack/skills/main"
const INDEX_PATH = ".well-known/agent-skills/index.json"
const NAME = /^[a-z0-9]+(-[a-z0-9]+)*$/

const frontMatter = (text, file) => {
  const block = text.match(/^---\n([\s\S]*?)\n---\n/)?.[1]
  if (!block) throw new Error(`${file}: no front matter`)
  const field = (key) => block.match(new RegExp(`^${key}:\\s*(.+)$`, "m"))?.[1].trim()
  return { name: field("name"), description: field("description") }
}

const skills = readdirSync("skills", { withFileTypes: true })
  .filter((entry) => entry.isDirectory())
  .map(({ name: dir }) => {
    const file = `skills/${dir}/SKILL.md`
    const bytes = readFileSync(file)
    const { name, description } = frontMatter(bytes.toString("utf8"), file)
    if (name !== dir || !NAME.test(name) || name.length > 64) throw new Error(`${file}: name must equal "${dir}"`)
    if (!description) throw new Error(`${file}: no description`)
    return {
      name,
      type: "skill-md",
      description,
      url: `${RAW_BASE}/${file}`,
      digest: `sha256:${createHash("sha256").update(bytes).digest("hex")}`
    }
  })
  .sort((a, b) => a.name.localeCompare(b.name))

const index = `${JSON.stringify({ $schema: "https://schemas.agentskills.io/discovery/0.2.0/schema.json", skills }, null, 2)}\n`

if (process.argv.includes("--check")) {
  let committed = ""
  try {
    committed = readFileSync(INDEX_PATH, "utf8")
  } catch {}
  if (committed !== index) {
    console.error(`${INDEX_PATH} is out of date: run node scripts/build-index.mjs and commit it`)
    process.exit(1)
  }
  console.log(`${INDEX_PATH} is up to date (${skills.length} skills)`)
} else {
  writeFileSync(INDEX_PATH, index)
  console.log(`Wrote ${INDEX_PATH} (${skills.length} skills)`)
}
