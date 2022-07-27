import ReactionsHandler from "./reactions_handler";
import VotingHandler from "./voting.js";


function init_reactions() {
    const cfg = document.querySelector("[data-dci=config]");
    if (cfg === null || window.djCommentsInk === null) {
        return;
    }

    window.djCommentsInk.reactions_handler = null;

    // Handler for clicking events on vote up/down elements.
    window.djCommentsInk.voting_handler = null;

    /* ----------------------------------------------
     * Initialize reactions_handler, in charge
     * of all reactions popover components.
     */
    if (window.djCommentsInk.reactions_handler === null) {
        window.djCommentsInk.reactions_handler = new ReactionsHandler(cfg);
        window.addEventListener("beforeunload", (_) => {
            window.djCommentsInk.reactions_handler.remove_event_listeners();
        });
    }

    /* ----------------------------------------------
     * Initialize voting up/down of comments with level == 0.
     */
    if (window.djCommentsInk.voting_handler === null) {
        window.djCommentsInk.voting_handler = new VotingHandler(cfg);
    }
}

export { init_reactions };
