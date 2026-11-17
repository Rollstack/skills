// Fails when the manifests that describe the plugin to each client disagree on its version. Every marketplace reads
// its own manifest: xAI's catalog, for one, ships an update to Grok Build users only when the version it reads changes.
import { readFileSync } from "node:fs"

const MANIFESTS = [
  ".claude-plugin/plugin.json",
  "plugin.json",
  ".cursor-plugin/plugin.json",
  ".grok-plugin/plugin.json",
  "package.json"
]

const versions = MANIFESTS.map((file) => [file, JSON.parse(readFileSync(file, "utf8")).version])

if (versions.some(([, version]) => !version || version !== versions[0][1])) {
  console.error("The manifests disagree on the plugin's version: set the same one in each")
  for (const [file, version] of versions) console.error(`  ${file}: ${version ?? "none"}`)
  process.exit(1)
}
console.log(`The ${MANIFESTS.length} manifests are all at version ${versions[0][1]}`)
