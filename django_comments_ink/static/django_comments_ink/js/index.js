import { init_comments } from "./comments.js";
import { init_reactions } from "./reactions.js";

window.dci.init_comments = init_comments;
window.dci.init_reactions = init_reactions;

window.addEventListener("DOMContentLoaded", (_) => {
    if (window.dci === null) {
        return;
    }

    init_comments();
    init_reactions();
});
