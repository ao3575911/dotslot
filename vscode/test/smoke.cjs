// Loads the bundle with a stub `vscode` module and checks activate() registers the command and providers.
const Module = require('module'); const path = require('path'); const assert = require('assert');
const reg = { commands: [], hints: 0 }; const noop = () => ({ dispose() {} });
const Emitter = class { constructor() { this.event = noop; } fire() {} };
const stub = {
  window: { createTextEditorDecorationType: () => ({ dispose() {} }), visibleTextEditors: [], onDidChangeVisibleTextEditors: noop, activeTextEditor: undefined },
  languages: { createDiagnosticCollection: () => ({ set() {}, delete() {}, dispose() {} }), registerInlayHintsProvider: () => { reg.hints++; return noop(); } },
  commands: { registerCommand: (n) => { reg.commands.push(n); return noop(); } },
  workspace: { getConfiguration: () => ({ get: (_k, d) => d }), onDidOpenTextDocument: noop, onDidChangeTextDocument: noop, onDidCloseTextDocument: noop, onDidChangeConfiguration: noop, textDocuments: [] },
  ThemeColor: class {}, EventEmitter: Emitter,
};
const load = Module._load; Module._load = function (r, ...a) { return r === 'vscode' ? stub : load.call(this, r, ...a); };
const ext = require(path.join(__dirname, '..', 'dist', 'extension.js'));
ext.activate({ subscriptions: [] });
assert.deepStrictEqual(reg.commands, ['dotslot.fillSlot']); assert.strictEqual(reg.hints, 1);
console.log('extension smoke test passed');
