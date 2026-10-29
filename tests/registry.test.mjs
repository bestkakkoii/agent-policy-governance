import assert from "node:assert/strict";
import { readFile } from "node:fs/promises";
import test from "node:test";
import { create_registry } from "../registry/handler.mjs";

const catalog = JSON.parse(await readFile(new URL("../policies/catalog.json", import.meta.url), "utf8"));
const registry = create_registry(catalog);
const version = "2026-07-28";
const metadata = { "io.modelcontextprotocol/protocolVersion": version,
  "io.modelcontextprotocol/clientInfo": { name: "contract_test", version: "1.0.0" },
  "io.modelcontextprotocol/clientCapabilities": {} };
function request(method, args = {}, modifications = {}) {
  const name = method === "tools/call" ? args.name : undefined;
  return new Request("https://registry.test/mcp", { method: "POST", headers: {
    "Content-Type": "application/json", "Accept": "application/json, text/event-stream",
    "MCP-Protocol-Version": version, "Mcp-Method": method, ...(name ? { "Mcp-Name": name } : {}),
    ...modifications,
  }, body: JSON.stringify({ jsonrpc: "2.0", id: 1, method, params: { ...args, _meta: metadata } }) });
}
async function call(name, args) {
  return registry.fetch(request("tools/call", { name, arguments: args }));
}

test("modern discovery and version identity", async () => {
  const response = await registry.fetch(request("server/discover"));
  assert.equal(response.status, 200);
  const body = await response.json();
  assert.deepEqual(body.result.supportedVersions, [version]);
  assert.equal(body.result.resultType, "complete");
});
test("tools expose bounded read-only schemas", async () => {
  const response = await registry.fetch(request("tools/list"));
  const body = await response.json();
  assert.equal(body.result.tools.length, 3);
  for (const tool of body.result.tools) {
    assert.equal(tool.annotations.readOnlyHint, true);
    assert.equal(tool.inputSchema.additionalProperties, false);
  }
});
test("resolve excludes unrelated game rules and supports unchanged delta", async () => {
  const response = await call("policy_resolve", { tags: ["software"], topics: ["quality"] });
  const packet = (await response.json()).result.structuredContent;
  assert.ok(packet.rules.length > 0);
  assert.ok(packet.rules.every((rule) => !rule.rule_id.startsWith("R")));
  const again = await call("policy_resolve", { tags: ["software"], topics: ["quality"], known_rule_hashes: packet.rule_hashes });
  assert.deepEqual((await again.json()).result.structuredContent.rules, []);
});
test("exact explanation and unknown rule failure", async () => {
  const valid = await call("policy_explain", { rule_ids: ["R10"], snapshot_id: catalog.snapshot_id });
  assert.equal((await valid.json()).result.structuredContent.rules[0].rule_id, "R10");
  const invalid = await call("policy_explain", { rule_ids: ["imaginary_rule"] });
  assert.equal(invalid.status, 400);
});
test("cannot silently change pinned version", async () => {
  const response = await call("policy_resolve", { tags: ["software"], topics: [], snapshot_id: "0".repeat(64) });
  assert.match((await response.json()).error.message, /no_silent_switch/);
});
test("header/body mismatch fails deterministically", async () => {
  const response = await registry.fetch(request("tools/list", {}, { "Mcp-Method": "tools/call" }));
  assert.equal(response.status, 400);
  assert.equal((await response.json()).error.code, -32020);
});
test("origin restrictions, no legacy GET stream", async () => {
  const blocked = await registry.fetch(request("server/discover", {}, { Origin: "https://attacker.invalid" }));
  assert.equal(blocked.status, 403);
  const get = await registry.fetch(new Request("https://registry.test/mcp"));
  assert.equal(get.status, 405);
});
test("project source, credentials and unexpected input are rejected", async () => {
  const response = await call("policy_resolve", { tags: ["software"], topics: [], source_code: "private content" });
  assert.equal(response.status, 400);
});
test("no mutation tools or global enforcement claim", async () => {
  const result = await call("policy_capabilities", {});
  const packet = (await result.json()).result.structuredContent;
  assert.equal(packet.enforcement, "advisory_read_only");
  assert.equal(packet.hosted_project_access, false);
  assert.equal((await call("policy_publish", {})).status, 400);
});
test("immutable snapshot and current manifest", async () => {
  const response = await registry.fetch(new Request(`https://registry.test/snapshots/${catalog.snapshot_id}.json`));
  assert.equal(response.status, 200);
  assert.deepEqual(await response.json(), catalog);
  assert.match(response.headers.get("cache-control"), /immutable/);
});
test("tampered catalog never serves valid-looking policy", async () => {
  const tampered = structuredClone(catalog);
  tampered.payload.rules[0].statement = "tamper";
  const instance = create_registry(tampered);
  const response = await instance.fetch(request("server/discover"));
  assert.equal(response.status, 503);
});
test("oversized and malformed requests are rejected", async () => {
  const response = await registry.fetch(new Request("https://registry.test/mcp", { method: "POST",
    headers: { "Content-Type": "application/json", Accept: "application/json, text/event-stream" }, body: "x".repeat(262145) }));
  assert.equal(response.status, 400);
});
test("remote selector matches the Python conformance vector", async () => {
  const fixture = JSON.parse(await readFile(new URL("./selector_vectors.json", import.meta.url), "utf8"));
  for (const vector of fixture) {
    const response = await call("policy_resolve", { tags: vector.tags, topics: vector.topics });
    const packet = (await response.json()).result.structuredContent;
    assert.deepEqual(packet.rules.map((rule) => rule.rule_id), vector.rule_ids);
  }
});

// Verify public policy transport, not native C++ build or research truth.
test("owner amendment reaches remote common and C++ profile slices", async () => {
  const generic = (await (await call("policy_resolve", { tags: ["software"], topics: [] })).json()).result.structuredContent;
  assert.ok(generic.rules.find((rule) => rule.rule_id === "owner.latest").statement.includes("theoretical advantage"));
  assert.ok(!generic.rules.some((rule) => rule.rule_id === "owner.cpp_modules"));
  const cpp = (await (await call("policy_resolve", { tags: ["software", "cpp"], topics: [] })).json()).result.structuredContent;
  const rule = cpp.rules.find((entry) => entry.rule_id === "owner.cpp_modules");
  assert.ok(rule.details.includes("export module module_name;"));
  assert.ok(rule.details.includes("module module_name;"));
});
