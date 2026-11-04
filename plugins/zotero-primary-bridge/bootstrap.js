// Uses Zotero's documented reader event; does not modify the PDF reader itself.
var selectionHandler = null;
var generation = 0;

function install() {}
function uninstall() {}

async function startup({ id }) {
    const current = ++generation;
    await Zotero.initializationPromise;
    await Zotero.uiReadyPromise;
    if (current !== generation || selectionHandler || !Zotero.isLinux) return;

    const { classes: Cc, interfaces: Ci } = Components;
    const helper = Cc['@mozilla.org/widget/clipboardhelper;1']
        .getService(Ci.nsIClipboardHelper);
    selectionHandler = (event) => {
        const text = event?.params?.annotation?.text;
        if (typeof text !== 'string' || !text.trim()) return;
        try {
            // Explicitly use PRIMARY. Leave the normal Ctrl+C clipboard alone.
            helper.copyStringToClipboard(text, Ci.nsIClipboard.kSelectionClipboard);
        } catch (error) {
            // Never let integration errors interrupt Zotero's selection popup.
            // Do not log selected text, document titles or clipboard contents.
            Zotero.logError('Pot Primary Selection Bridge: PRIMARY write failed');
        }
    };
    Zotero.Reader.registerEventListener('renderTextSelectionPopup', selectionHandler, id);
}

function shutdown() {
    ++generation;
    if (selectionHandler) {
        Zotero.Reader.unregisterEventListener('renderTextSelectionPopup', selectionHandler);
        selectionHandler = null;
    }
}
