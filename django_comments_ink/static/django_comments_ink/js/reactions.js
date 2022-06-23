import ReactionsHandler from "./reactions_handler";

function init_reactions() {
    const rroot = document.querySelector("[data-dci=config]");
    if (rroot === null || window.djCommentsInk === null) {
        return;
    }

    window.djCommentsInk.reactions_handler = null;

    /* ----------------------------------------------
     * Initialize reactions_handler, in charge
     * of all reactions popover components.
     */
    if (window.djCommentsInk.reactions_handler === null) {
        window.djCommentsInk.reactions_handler = new ReactionsHandler(rroot);
        window.addEventListener("beforeunload", (_) => {
            window.djCommentsInk.reactions_handler.remove_event_listeners();
        });

    }
}

export { init_reactions };
