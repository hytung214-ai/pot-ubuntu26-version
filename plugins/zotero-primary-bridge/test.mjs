import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import vm from 'node:vm';

const source = readFileSync(new URL('./bootstrap.js', import.meta.url), 'utf8');
function fixture({ linux = true, fail = false, initialization = Promise.resolve() } = {}) {
    const writes = [], listeners = [], errors = [];
    const context = vm.createContext({
        Zotero: {
            isLinux: linux, initializationPromise: initialization, uiReadyPromise: Promise.resolve(),
            Reader: {
                registerEventListener(type, handler, id) { listeners.push({ type, handler, id }); },
                unregisterEventListener(type, handler) {
                    const i = listeners.findIndex(x => x.type === type && x.handler === handler);
                    if (i >= 0) listeners.splice(i, 1);
                },
            },
            logError(error) { errors.push(error); },
        },
        Components: {
            classes: { '@mozilla.org/widget/clipboardhelper;1': { getService() {
                return { copyStringToClipboard(text, clipboard) {
                    if (fail) throw new Error('platform failure');
                    writes.push({ text, clipboard });
                } };
            } } },
            interfaces: { nsIClipboardHelper: {}, nsIClipboard: { kSelectionClipboard: 1 } },
        },
    });
    vm.runInContext(source, context);
    return { context, writes, listeners, errors };
}

const f = fixture();
await f.context.startup({ id: 'test' });
assert.equal(f.listeners[0].type, 'renderTextSelectionPopup');
const event = { params: { annotation: { text: 'Title 标题\nsecond line' } } };
const before = JSON.stringify(event);
f.listeners[0].handler(event);
assert.deepEqual(f.writes, [{ text: event.params.annotation.text, clipboard: 1 }]);
assert.equal(JSON.stringify(event), before); // popup/annotation is not mutated
for (const text of ['', '  ', null, 123]) f.listeners[0].handler({ params: { annotation: { text } } });
f.listeners[0].handler({});
assert.equal(f.writes.length, 1);
f.context.shutdown();
assert.equal(f.listeners.length, 0);

const bad = fixture({ fail: true });
await bad.context.startup({ id: 'test' });
assert.doesNotThrow(() => bad.listeners[0].handler(event));
assert.equal(bad.errors.length, 1);
assert.ok(!bad.errors[0].includes('Title'));

const other = fixture({ linux: false });
await other.context.startup({ id: 'test' });
assert.equal(other.listeners.length, 0);

let resolve;
const race = fixture({ initialization: new Promise(r => { resolve = r; }) });
const pending = race.context.startup({ id: 'test' });
race.context.shutdown();
resolve(); await pending;
assert.equal(race.listeners.length, 0);
console.log('PASS: PRIMARY only, Unicode, popup unchanged, empty selection, shutdown, platform error, Linux guard, startup cancellation');
