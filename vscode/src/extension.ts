// dotslot for VS Code: slot highlighting, width inlay hints, diagnostics, and a "Fill slot" command.
// The scanner is the npm implementation (../npm/src), bundled by esbuild.
import * as vscode from 'vscode';
import { scanText, fillText, SlotError, Slot, Mode } from '../../npm/src/core.js';
import { clusters, unitWidth, displayWidth } from '../../npm/src/width.js';

const cfg = () => vscode.workspace.getConfiguration('dotslot');
const slotDeco = vscode.window.createTextEditorDecorationType({
  backgroundColor: new vscode.ThemeColor('editor.wordHighlightBackground'),
  border: '1px solid', borderColor: new vscode.ThemeColor('editorBracketMatch.border'), borderRadius: '2px',
});
const filledDeco = vscode.window.createTextEditorDecorationType({
  backgroundColor: new vscode.ThemeColor('editor.wordHighlightStrongBackground'), borderRadius: '2px',
});

/** UTF-16 index on a line for a display-cell column (scanner issues report cells). */
function cellToIndex(line: string, col: number): number {
  let w = 0, i = 0;
  for (const u of clusters(line)) { if (w >= col) break; w += unitWidth(u, w, 8); i += u.length; }
  return i;
}
function scan(doc: vscode.TextDocument) {
  const path = doc.uri.scheme === 'untitled' ? '-' : doc.fileName;
  return scanText(doc.getText(), path, cfg().get<Mode>('mode', 'auto'));
}
const allSlots = (slots: Slot[]) => slots.flatMap((s) => [s, ...s.conts]);
const rangeOf = (x: Slot) => new vscode.Range(x.line, x.start, x.line, x.end);

const diagnostics = vscode.languages.createDiagnosticCollection('dotslot');
function refresh(doc: vscode.TextDocument) {
  if (!cfg().get<boolean>('enable', true) || doc.lineCount > 20000) { diagnostics.delete(doc.uri); return; }
  const [slots, issues] = scan(doc);
  const diags: vscode.Diagnostic[] = issues.map(([sev, l, c, msg]) => {
    const text = doc.lineAt(Math.min(l, doc.lineCount - 1)).text, st = cellToIndex(text, c);
    const end = text.indexOf('>', st) >= 0 ? text.indexOf('>', st) + 1 : text.length;
    const d = new vscode.Diagnostic(new vscode.Range(l, st, l, Math.max(end, st + 1)), msg,
      sev === 'E' ? vscode.DiagnosticSeverity.Error : vscode.DiagnosticSeverity.Warning);
    d.source = 'dotslot'; return d;
  });
  const max = cfg().get<number>('maxLineLength', 0);
  if (max > 0) {
    for (const ln of new Set(allSlots(slots).map((x) => x.line))) {
      const text = doc.lineAt(ln).text, w = displayWidth(text);
      if (w > max) {
        const d = new vscode.Diagnostic(new vscode.Range(ln, cellToIndex(text, max), ln, text.length),
          `line with a slot is ${w} cells, over dotslot.maxLineLength ${max}`, vscode.DiagnosticSeverity.Warning);
        d.source = 'dotslot'; d.code = 'line-length'; diags.push(d);
      }
    }
  }
  diagnostics.set(doc.uri, diags);
  for (const ed of vscode.window.visibleTextEditors) if (ed.document === doc) {
    const xs = allSlots(slots);
    ed.setDecorations(slotDeco, xs.filter((x) => !x.rawValue).map(rangeOf));
    ed.setDecorations(filledDeco, xs.filter((x) => x.rawValue).map(rangeOf));
  }
}

class Hints implements vscode.InlayHintsProvider {
  readonly changed = new vscode.EventEmitter<void>();
  onDidChangeInlayHints = this.changed.event;
  provideInlayHints(doc: vscode.TextDocument, range: vscode.Range): vscode.InlayHint[] {
    if (!cfg().get<boolean>('enable', true) || !cfg().get<boolean>('inlayHints', true)) return [];
    const [slots] = scan(doc);
    return slots.filter((s) => range.contains(new vscode.Position(s.line, s.end))).map((s) => {
      const cap = s.capacity + s.conts.reduce((a, c) => a + c.capacity, 0);
      const used = s.rawValue ? displayWidth(s.conts.length ? s.blockValue() : s.value ?? '') : 0;
      const h = new vscode.InlayHint(new vscode.Position(s.line, s.end),
        ` ${used}/${cap}${s.conts.length ? ` ×${1 + s.conts.length}` : ''}`, vscode.InlayHintKind.Parameter);
      h.tooltip = `${s.name ?? '@' + s.index}: width ${s.width}, capacity ${cap}${s.policy ? `, policy ${s.policy}` : ''}`;
      h.paddingLeft = true; return h;
    });
  }
}

async function fillSlot(arg?: { line: number; character: number }) {
  const ed = vscode.window.activeTextEditor; if (!ed) return;
  const doc = ed.document, pos = arg ? new vscode.Position(arg.line, arg.character) : ed.selection.active;
  const [slots] = scan(doc);
  const s = slots.find((x) => [x, ...x.conts].some((y) => rangeOf(y).contains(pos)));
  if (!s) { vscode.window.showInformationMessage('dotslot: put the cursor inside a <./…> slot.'); return; }
  const cap = s.capacity + s.conts.reduce((a, c) => a + c.capacity, 0), key = `@${s.index}`;
  const value = await vscode.window.showInputBox({
    title: `Fill ${s.name ?? key} (${cap} cells${s.policy ? ', ' + s.policy : ''})`,
    value: s.conts.length ? s.blockValue() : s.value ?? '',
    validateInput: (v) => { try { fillText(doc.getText(), { [key]: v }, doc.fileName, cfg().get<Mode>('mode', 'auto'), cfg().get('overflow', 'error')); return null; } catch (e) { return e instanceof SlotError ? e.message : String(e); } },
  });
  if (value === undefined) return;
  try {
    const out = fillText(doc.getText(), { [key]: value }, doc.fileName, cfg().get<Mode>('mode', 'auto'), cfg().get('overflow', 'error'));
    const all = new vscode.Range(doc.positionAt(0), doc.positionAt(doc.getText().length));
    await ed.edit((e) => e.replace(all, out));
  } catch (e) { vscode.window.showErrorMessage(`dotslot: ${e instanceof Error ? e.message : e}`); }
}

export function activate(ctx: vscode.ExtensionContext) {
  const hints = new Hints();
  let timer: NodeJS.Timeout | undefined;
  const later = (doc: vscode.TextDocument) => { clearTimeout(timer); timer = setTimeout(() => { refresh(doc); hints.changed.fire(); }, 150); };
  ctx.subscriptions.push(diagnostics, slotDeco, filledDeco,
    vscode.languages.registerInlayHintsProvider({ scheme: '*' }, hints),
    vscode.commands.registerCommand('dotslot.fillSlot', fillSlot),
    vscode.workspace.onDidOpenTextDocument(refresh),
    vscode.workspace.onDidChangeTextDocument((e) => later(e.document)),
    vscode.workspace.onDidCloseTextDocument((d) => diagnostics.delete(d.uri)),
    vscode.window.onDidChangeVisibleTextEditors((eds) => eds.forEach((e) => refresh(e.document))),
    vscode.workspace.onDidChangeConfiguration((e) => { if (e.affectsConfiguration('dotslot')) { vscode.workspace.textDocuments.forEach(refresh); hints.changed.fire(); } }));
  vscode.workspace.textDocuments.forEach(refresh);
}
export function deactivate() {}
