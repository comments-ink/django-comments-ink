import ReactionsHandler from "./reactions_handler";

function init_reactions() {
    if (window.dci === null) {
        return;
    }

    const rroot = document.querySelector("[data-dci=config]");
    if (rroot === null || window.dci === null) {
        return;
    }

    window.dci.reactions_handler = null;

    /* ----------------------------------------------
     * Initialize reactions_handler, in charge
     * of all reactions popover components.
     */
    if (window.dci.reactions_handler === null) {
        window.dci.reactions_handler = new ReactionsHandler(rroot);
        window.addEventListener("beforeunload", (_) => {
            window.dci.reactions_handler.remove_event_listeners();
        });

    }
}

export { init_reactions };
