import { init_comments } from "./comments.js";
import { init_reactions } from "./reactions.js";

window.djCommentsInk = {
    init_comments: init_comments,
    init_reactions: init_reactions
};

window.addEventListener("DOMContentLoaded", (_) => {
    init_comments();
    init_reactions();
});
