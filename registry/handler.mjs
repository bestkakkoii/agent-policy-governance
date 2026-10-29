// Read-only public registry. No project text, credential, file-write or execution tools.
/** @typedef {{rule_id:string,strength:string,scope:string[],topics:string[],statement:string,details:string,source:string,check:string}} policy_rule */
/** @typedef {{snapshot_id:string,payload:{schema_version:number,version:string,rules:policy_rule[]}}} policy_catalog */
const protocol_version = "2026-07-28";
const prefix = "io.modelcontextprotocol/";
const body_limit = 262144;

/** @param {unknown} value @returns {Record<string, unknown>} */
function object(value) {
  if (!value || typeof value !== "object" || Array.isArray(value)) { throw new Error("Expected an object"); }
  return /** @type {Record<string, unknown>} */ (value);
}
/** @param {unknown} value @returns {string} */
function text(value) {
  if (typeof value !== "string") { throw new Error("Expected a string"); }
  return value;
}
/** @param {unknown} value @param {number} limit @returns {string[]} */
function strings(value, limit) {
  if (!Array.isArray(value) || value.length > limit || value.some((item) => typeof item !== "string" || item.length > 128)) {
    throw new Error(`Expected at most ${limit} bounded strings`);
  }
  return value;
}
/** @param {unknown} value @returns {string} */
function canonical(value) {
  if (value === null || typeof value !== "object") { return JSON.stringify(value); }
  if (Array.isArray(value)) { return "[" + value.map(canonical).join(",") + "]"; }
  const record = object(value);
  return "{" + Object.keys(record).sort().map((key) => JSON.stringify(key) + ":" + canonical(record[key])).join(",") + "}";
}
/** @param {unknown} value */
async function hash(value) {
  const result = await crypto.subtle.digest("SHA-256", new TextEncoder().encode(canonical(value)));
  return Array.from(new Uint8Array(result), (byte) => byte.toString(16).padStart(2, "0")).join("");
}
/** @param {unknown} value @param {number} status @param {Record<string,string>} extra */
function json_response(value, status = 200, extra = {}) {
  return new Response(JSON.stringify(value), { status, headers: {
    "Content-Type": "application/json; charset=utf-8", "X-Content-Type-Options": "nosniff", ...extra,
  } });
}
/** @param {unknown} id @param {number} code @param {string} message @param {number} status @param {unknown} data */
function rpc_error(id, code, message, status = 400, data = undefined) {
  return json_response({ jsonrpc: "2.0", id: id ?? null, error: { code, message, ...(data === undefined ? {} : { data }) } }, status);
}
/** @param {Request} request */
async function bounded_body(request) {
  const declared = request.headers.get("content-length");
  if (declared !== null && (!/^\d+$/.test(declared) || Number(declared) > body_limit)) { throw new Error("body_limit"); }
  if (!request.body) { return ""; }
  const reader = request.body.getReader();
  let size = 0;
  /** @type {Uint8Array[]} */ const chunks = [];
  try {
    while (true) {
      const result = await reader.read();
      if (result.done) { break; }
      size += result.value.length;
      if (size > body_limit) { await reader.cancel(); throw new Error("body_limit"); }
      chunks.push(result.value);
    }
  } finally { reader.releaseLock(); }
  const bytes = new Uint8Array(size);
  let offset = 0;
  for (const chunk of chunks) { bytes.set(chunk, offset); offset += chunk.length; }
  return new TextDecoder("utf-8", { fatal: true }).decode(bytes);
}
/** @param {string|null} header */
function decode_header(header) {
  if (header === null) { return null; }
  if (header.startsWith("=?base64?") && header.endsWith("?=")) {
    const encoded = header.slice(9, -2);
    const binary = atob(encoded);
    return new TextDecoder("utf-8", { fatal: true }).decode(Uint8Array.from(binary, (character) => character.charCodeAt(0)));
  }
  return header;
}

const annotations = { readOnlyHint: true, destructiveHint: false, idempotentHint: true, openWorldHint: false };
const tag_schema = { type: "array", items: { type: "string", pattern: "^[a-z][a-z0-9_]*$", maxLength: 128 }, maxItems: 64, uniqueItems: true };
const tools = [
  { name: "policy_resolve", description: "Return only policies applicable to factual project tags and task topics. Send no source code, prompts, paths or credentials. Clear known_rule_hashes after context loss.",
    inputSchema: { type: "object", properties: { tags: tag_schema, topics: tag_schema,
      snapshot_id: { type: "string", pattern: "^[a-f0-9]{64}$" },
      known_rule_hashes: { type: "object", maxProperties: 128, additionalProperties: { type: "string", pattern: "^[a-f0-9]{64}$" } } },
    required: ["tags", "topics"], additionalProperties: false }, annotations },
  { name: "policy_explain", description: "Retrieve bounded exact policy clauses by rule IDs and an optional pinned snapshot. Does not inspect or change a project.",
    inputSchema: { type: "object", properties: { rule_ids: { type: "array", items: { type: "string", maxLength: 128 }, minItems: 1, maxItems: 32 },
      snapshot_id: { type: "string", pattern: "^[a-f0-9]{64}$" } }, required: ["rule_ids"], additionalProperties: false }, annotations },
  { name: "policy_capabilities", description: "Report registry coverage and limitations. This service cannot intercept other ChatGPT tools or enforce all model output.",
    inputSchema: { type: "object", properties: {}, additionalProperties: false }, annotations },
];

/** @param {policy_catalog} catalog */
export function create_registry(catalog) {
  const catalog_check = hash(catalog.payload).then((actual) => {
    if (actual !== catalog.snapshot_id || catalog.payload.schema_version !== 2) { throw new Error("catalog_integrity_failed"); }
    const ids = catalog.payload.rules.map((rule) => rule.rule_id);
    if (ids.length !== new Set(ids).size) { throw new Error("duplicate_policy_identity"); }
  });
  const capabilities = { enforcement: "advisory_read_only", hosted_project_access: false, persistent_user_data: false,
    protocol_versions: [protocol_version], snapshot_id: catalog.snapshot_id,
    limitations: ["Cannot intercept other tools or all model responses", "Independent review identity is not authenticated by this public registry",
      "Digest checks are integrity checks, not publisher signatures", "CLI adapters and native host trust are separate installations"] };

  /** @param {string} name @param {Record<string, unknown>} args */
  async function tool_call(name, args) {
    const definition = tools.find((tool) => tool.name === name);
    if (!definition) { throw new Error("unknown_tool"); }
    const allowed = new Set(Object.keys(definition.inputSchema.properties));
    if (Object.keys(args).some((key) => !allowed.has(key))) { throw new Error("unexpected_argument_no_project_content_allowed"); }
    if (args.snapshot_id !== undefined && args.snapshot_id !== catalog.snapshot_id) { throw new Error("snapshot_unavailable_no_silent_switch"); }
    if (name === "policy_capabilities") { return capabilities; }
    if (name === "policy_explain") {
      const ids = strings(args.rule_ids, 32);
      if (ids.length === 0) { throw new Error("rule_ids_required"); }
      const rules = ids.map((id) => catalog.payload.rules.find((rule) => rule.rule_id === id));
      if (rules.some((rule) => !rule)) { throw new Error("unknown_rule"); }
      return { snapshot_id: catalog.snapshot_id, rules };
    }
    const tags = strings(args.tags, 64);
    const topics = strings(args.topics, 64);
    if ([...tags, ...topics].some((tag) => !/^[a-z][a-z0-9_]*$/.test(tag)) || new Set(tags).size !== tags.length || new Set(topics).size !== topics.length) {
      throw new Error("invalid_or_duplicate_tags");
    }
    const known = args.known_rule_hashes === undefined ? {} : object(args.known_rule_hashes);
    if (Object.keys(known).length > 128 || Object.entries(known).some(([key, value]) => key.length > 128 || typeof value !== "string" || !/^[a-f0-9]{64}$/.test(value))) {
      throw new Error("invalid_known_rule_hashes");
    }
    const selected = catalog.payload.rules.filter((rule) => rule.scope.every((tag) => tags.includes(tag))
      && (rule.topics.includes("always") || rule.topics.some((topic) => topics.includes(topic))));
    selected.sort((left, right) => Number(!left.rule_id.startsWith("owner.")) - Number(!right.rule_id.startsWith("owner."))
      || (left.rule_id < right.rule_id ? -1 : left.rule_id > right.rule_id ? 1 : 0));
    /** @type {Record<string,string>} */ const hashes = {};
    for (const rule of selected) { hashes[rule.rule_id] = await hash(rule); }
    return { snapshot_id: catalog.snapshot_id, rule_hashes: hashes,
      rules: selected.filter((rule) => known[rule.rule_id] !== hashes[rule.rule_id]),
      removed_rule_ids: Object.keys(known).filter((key) => !(key in hashes)).sort(),
      enforcement: "advisory_read_only", actual_model_tokens: null };
  }

  /** @param {Request} request */
  async function fetch(request) {
    const url = new URL(request.url);
    const origin = request.headers.get("origin");
    if (origin !== null && ![url.origin, "https://chatgpt.com"].includes(origin)) {
      return rpc_error(null, -32600, "Origin is not allowed", 403);
    }
    try { await catalog_check; }
    catch { return json_response({ ok: false, error: "registry_catalog_invalid" }, 503); }
    if (request.method === "GET" && url.pathname === "/health") {
      return json_response({ ok: true, version: catalog.payload.version, snapshot_id: catalog.snapshot_id });
    }
    if (request.method === "GET" && url.pathname === "/manifest.json") {
      return json_response({ snapshot_id: catalog.snapshot_id, version: catalog.payload.version,
        snapshot_path: `/snapshots/${catalog.snapshot_id}.json` }, 200, { "Cache-Control": "public, max-age=60" });
    }
    if (request.method === "GET" && url.pathname === `/snapshots/${catalog.snapshot_id}.json`) {
      return json_response(catalog, 200, { "ETag": `"${catalog.snapshot_id}"`, "Cache-Control": "public, max-age=31536000, immutable" });
    }
    if (url.pathname !== "/mcp") { return json_response({ ok: false, error: "not_found" }, 404); }
    if (request.method === "OPTIONS" && origin !== null) {
      return new Response(null, { status: 204, headers: { "Access-Control-Allow-Origin": origin,
        "Access-Control-Allow-Methods": "POST", "Access-Control-Allow-Headers": "Content-Type, MCP-Protocol-Version, Mcp-Method, Mcp-Name", "Vary": "Origin" } });
    }
    if (request.method !== "POST") { return json_response({ ok: false, error: "post_required" }, 405, { "Allow": "POST" }); }
    if (!(request.headers.get("content-type") ?? "").toLowerCase().startsWith("application/json")) {
      return rpc_error(null, -32600, "Expected application/json", 415);
    }
    const accept = request.headers.get("accept") ?? "";
    if (!accept.includes("application/json") || !accept.includes("text/event-stream")) {
      return rpc_error(null, -32600, "Accept must include application/json and text/event-stream", 406);
    }
    /** @type {Record<string,unknown>} */ let body;
    try { body = object(JSON.parse(await bounded_body(request))); }
    catch (error) { return rpc_error(null, -32700, error instanceof Error && error.message === "body_limit" ? "Body limit exceeded" : "Invalid JSON request", 400); }
    const id = body.id;
    if (body.jsonrpc !== "2.0" || (typeof id !== "string" && typeof id !== "number") || typeof body.method !== "string") {
      return rpc_error(null, -32600, "Expected one JSON-RPC request with an ID; notifications are not implemented", 400);
    }
    if (body.method === "initialize") { return rpc_error(id, -32601, `This server supports modern MCP ${protocol_version}; initialize is not implemented`, 404); }
    let params;
    let metadata;
    try {
      params = object(body.params);
      metadata = object(params._meta);
      const identity = object(metadata[prefix + "clientInfo"]);
      text(identity.name); text(identity.version);
      object(metadata[prefix + "clientCapabilities"]);
    } catch { return rpc_error(id, -32602, "Required per-request MCP client metadata is missing or malformed"); }
    const requested = metadata[prefix + "protocolVersion"];
    try {
      if (request.headers.get("mcp-protocol-version") !== requested || request.headers.get("mcp-method") !== body.method
          || (body.method === "tools/call" && decode_header(request.headers.get("mcp-name")) !== params.name)) {
        return rpc_error(id, -32020, "Required MCP headers are missing or differ from the request body");
      }
    } catch { return rpc_error(id, -32020, "Malformed encoded MCP header"); }
    if (requested !== protocol_version) { return rpc_error(id, -32022, "Unsupported protocol version", 400, { supported: [protocol_version], requested }); }
    /** @type {Record<string,unknown>} */ let result;
    if (body.method === "server/discover") {
      result = { resultType: "complete", supportedVersions: [protocol_version], capabilities: { tools: {} },
        _meta: { [prefix + "serverInfo"]: { name: "agent_policy_governance", version: catalog.payload.version } },
        instructions: "Retrieve applicable engineering policies using tags and topics. Never submit project source or credentials. This server provides guidance, not global interception.",
        ttlMs: 60000, cacheScope: "public" };
    } else if (body.method === "tools/list") {
      result = { resultType: "complete", tools };
    } else if (body.method === "tools/call") {
      try {
        const data = await tool_call(text(params.name), object(params.arguments));
        result = { resultType: "complete", structuredContent: data, content: [{ type: "text", text: JSON.stringify(data) }], isError: false };
      } catch (error) {
        return rpc_error(id, -32602, error instanceof Error ? error.message : "Invalid tool arguments");
      }
    } else { return rpc_error(id, -32601, "Method not found", 404); }
    return json_response({ jsonrpc: "2.0", id, result }, 200, origin ? { "Access-Control-Allow-Origin": origin, "Vary": "Origin" } : {});
  }
  return { fetch };
}
