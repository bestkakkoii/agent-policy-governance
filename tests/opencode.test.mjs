import test from "node:test";
import assert from "node:assert/strict";
import { mkdtemp, mkdir, rm } from "node:fs/promises";
import { tmpdir } from "node:os";
import { join, resolve } from "node:path";
import * as adapter from "../adapters/opencode/plugin.mjs";

async function fixture(t) {
  const base = await mkdtemp(join(tmpdir(), "apg_opencode_"));
  t.after(() => rm(base, {recursive:true,force:true}));
  const project = join(base, "project");
  await mkdir(project);
  const hooks = await adapter.default({directory:project}, {config:{
    python:process.env.APG_TEST_PYTHON || "python", launcher:resolve("apg.py"), home:join(base,"state")
  }});
  return hooks;
}

test("only the host plugin entry is exported", () => assert.deepEqual(Object.keys(adapter), ["default"]));
test("real subprocess restores policies into fresh model context and compaction", async (t) => {
  const hooks = await fixture(t);
  await hooks["chat.message"]({sessionID:"real_adapter"},{parts:[{type:"text",text:"review code quality"}]});
  for (let iteration=0; iteration<2; iteration++) {
    const output = {system:[]};
    await hooks["experimental.chat.system.transform"]({sessionID:"real_adapter"}, output);
    assert.match(output.system.join("\n"), /owner.evidence/);
  }
  const output={context:[]};
  await hooks["experimental.session.compacting"]({sessionID:"real_adapter"},output);
  assert.match(output.context.join("\n"), /owner.evidence/);
  await hooks.event({event:{type:"session.idle",properties:{sessionID:"real_adapter"}}});
});
test("supported invalid direct write throws before host execution", async(t) => {
  const hooks=await fixture(t);
  await assert.rejects(hooks["tool.execute.before"]({sessionID:"write",tool:"write"},{args:{filePath:"BadName.py",content:"x=1"}}),/APG_POLICY_DENIED/);
});
test("agent definition synthesis without session does not invent a task", async(t) => {
  const hooks=await fixture(t); const output={system:[]};
  await hooks["experimental.chat.system.transform"]({},output);
  assert.deepEqual(output.system,[]);
});
