// Host-contract adapter. The installer replaces only the configuration marker.
import { spawn } from "node:child_process";

const installed_config = /*APG_CONFIG*/ null;

/** @param {{python: string, launcher: string, home: string}} config
 * @param {Record<string, unknown>} payload
 * @returns {Promise<Record<string, any>>} */
function invoke(config, payload) {
  return new Promise((resolve, reject) => {
    const child = spawn(config.python, [config.launcher, "--home", config.home, "rpc"], {
      stdio: ["pipe", "pipe", "pipe"], windowsHide: true, shell: false,
    });
    let stdout = "";
    let stderr = "";
    let settled = false;
    const timer = setTimeout(() => {
      child.kill();
      if (!settled) {
        settled = true;
        reject(new Error("APG_TIMEOUT: local policy request exceeded 10 seconds"));
      }
    }, 10000);
    child.on("error", (error) => {
      clearTimeout(timer);
      if (!settled) { settled = true; reject(error); }
    });
    child.stdout.on("data", (data) => {
      stdout += data.toString("utf8");
      if (stdout.length > 2 * 1024 * 1024) { child.kill(); }
    });
    child.stderr.on("data", (data) => {
      if (stderr.length < 65536) { stderr += data.toString("utf8"); }
    });
    child.on("close", (code) => {
      clearTimeout(timer);
      if (settled) { return; }
      settled = true;
      if (code !== 0) { reject(new Error(`APG_RUNTIME_ERROR (${code}): ${stderr || stdout}`)); return; }
      try { resolve(JSON.parse(stdout)); }
      catch (error) { reject(new Error(`APG_PROTOCOL_ERROR: ${String(error)}`)); }
    });
    child.stdin.on("error", (error) => {
      if (!settled) { settled = true; clearTimeout(timer); child.kill(); reject(error); }
    });
    child.stdin.end(JSON.stringify(payload));
  });
}

/** @param {{directory: string}} host
 * @param {{python: string, launcher: string, home: string} | null} config */
function create_hooks(host, config) {
  if (!config) { throw new Error("APG_NOT_INSTALLED: run the repository installer"); }
  const call = (/** @type {Record<string, unknown>} */ payload) => invoke(config, { project: host.directory, ...payload });
  return {
    // Store only inferred topics in local state; never send the prompt remotely.
    "chat.message": async (/** @type {{sessionID: string}} */ input, /** @type {{parts: Array<{type: string, text?: string}>}} */ output) => {
      const task = output.parts.filter((part) => part.type === "text").map((part) => part.text ?? "").join("\n");
      await call({ op: "context", session: input.sessionID, task, begin: true });
    },
    "experimental.chat.system.transform": async (/** @type {{sessionID?: string}} */ input, /** @type {{system: string[]}} */ output) => {
      if (!input.sessionID) { return; } // Agent-definition generation is not a project task session.
      // The host rebuilds this array per model request. Full *applicable* context must be restored;
      // sending just a delta here would silently drop earlier policy text.
      const packet = await call({ op: "context", session: input.sessionID, fresh: true });
      if (packet.context) { output.system.push(packet.context); }
    },
    "tool.execute.before": async (/** @type {{sessionID: string, tool: string}} */ input, /** @type {{args: Record<string, unknown>}} */ output) => {
      const result = await call({ op: "hook", adapter: "opencode", event: {
        cwd: host.directory, session_id: input.sessionID, hook_event_name: "PreToolUse",
        tool_name: input.tool, tool_input: output.args,
      } });
      const decision = result.hookSpecificOutput;
      if (decision?.permissionDecision === "deny") {
        throw new Error(`APG_POLICY_DENIED: ${decision.permissionDecisionReason}`);
      }
    },
    "experimental.session.compacting": async (/** @type {{sessionID: string}} */ input, /** @type {{context: string[]}} */ output) => {
      const packet = await call({ op: "context", session: input.sessionID, fresh: true });
      if (packet.context) { output.context.push(packet.context); }
    },
    event: async (/** @type {{event: {type: string, properties?: {sessionID?: string, info?: {id?: string}}}}} */ input) => {
      const event = input.event;
      if (event.type !== "session.idle" && event.type !== "session.deleted") { return; }
      const session = event.properties?.sessionID ?? event.properties?.info?.id;
      if (session) { await call({ op: "finish", session }); }
    },
  };
}

/** @param {{directory: string}} host
 * @param {{config?: {python: string, launcher: string, home: string}}} options */
export default async function policy_governance(host, options = {}) {
  return create_hooks(host, installed_config ?? options.config ?? null);
}
