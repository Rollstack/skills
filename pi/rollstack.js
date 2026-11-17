// Pi extension: registers Rollstack's MCP server, so that installing the package brings the server along with the
// skills. Pi signs the user in with OAuth: `/mcp login rollstack` in a session.

/** @param {import("@earendil-works/pi-coding-agent").ExtensionAPI} pi */
export default function (pi) {
  // Pi before 0.99.0 has no MCP support: the skills still load, and rollstack-getting-started says how to connect
  if (typeof pi.registerMcpServer !== "function") return
  pi.registerMcpServer("rollstack", {
    url: "https://api.rollstack.com/public/v1/mcp",
    description: "Build decks from your company's data, and refresh, schedule and send reports, with Rollstack"
  })
}
