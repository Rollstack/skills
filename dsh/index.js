// DeepSeek Harness plugin: offers the skills in ../skills to dsh's agents. The other row of cordis.patch.yml connects
// Rollstack's MCP server. It follows dsh's own packaged skill providers, dsh-skill-office and dsh-skill-badge.
import { readdir, readFile } from "node:fs/promises"
import { join, sep } from "node:path"
import { fileURLToPath } from "node:url"

const PROVIDER = "rollstack"
const SKILLS_DIR = fileURLToPath(new URL("../skills/", import.meta.url))
// BUNDLED_SKILL_RANK of @deepseek-ai/dsh-skill: a project's or user's own skill of the same name wins over a packaged
// one. Copied, not imported, so that the package has no dsh dependency to resolve.
const BUNDLED_SKILL_RANK = 600
const FRONT_MATTER = /^---\r?\n([\s\S]*?)\r?\n---(?:\r?\n|$)/

// A skill's description from its front matter, and its instructions without the front matter, as dsh expects them
const readSkill = async (name) => {
  const file = join(SKILLS_DIR, name, "SKILL.md")
  const text = await readFile(file, "utf8")
  const frontMatter = FRONT_MATTER.exec(text)
  const description = frontMatter?.[1].match(/^description:\s*(.+)$/m)?.[1].trim()
  if (!description) throw new Error(`${file}: no description in its front matter`)
  return { description, content: text.slice(frontMatter[0].length).trim() }
}

export const name = "rollstack"
export const inject = ["skills"]

export function apply(ctx) {
  ctx.skills.registerProvider(() => ({
    name: PROVIDER,
    async list() {
      const entries = await readdir(SKILLS_DIR, { withFileTypes: true })
      return Promise.all(
        entries
          .filter((entry) => entry.isDirectory())
          .map(async ({ name }) => {
            const directory = join(SKILLS_DIR, name)
            return {
              name,
              description: (await readSkill(name)).description,
              invocation: { modelInvocable: true, userInvocable: true },
              provider: PROVIDER,
              source: "bundled",
              rank: BUNDLED_SKILL_RANK,
              resourceBase: { kind: "directory", path: directory.split(sep).join("/") },
              locator: join(directory, "SKILL.md")
            }
          })
      )
    },
    // rank and locator belong to the catalog entry only: the loaded skill is the rest, with its instructions
    async get({ rank, locator, ...summary }) {
      return { ...summary, content: (await readSkill(summary.name)).content }
    }
  }))
}
