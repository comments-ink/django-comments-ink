import { init_comments } from "./comments.js";
import { init_reactions } from "./reactions.js";
import { init_flagging } from "./flagging.js";

window.djCommentsInk = {
    init_comments: init_comments,
    init_reactions: init_reactions,
    init_flagging: init_flagging
};

window.addEventListener("DOMContentLoaded", (_) => {
    init_comments();
    init_reactions();
    init_flagging();
});
