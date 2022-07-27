import CommentForm from "./comment_form.js";
import ReplyFormsHandler from "./reply_forms.js";
import FoldingHandler from "./folding.js";


function init_comments() {
    if (window.djCommentsInk === null) {
        return;
    }

    if (window.djCommentsInk.page_param === undefined) {
        const rroot = document.querySelector("[data-dci=config]");
        if (rroot) {
            window.djCommentsInk.page_param = rroot.getAttribute(
                "data-page-qs-param"
            );
        }
    }

    window.djCommentsInk.comment_form = null;
    window.djCommentsInk.reply_forms_handler = null;

    // Handler of clicking events on a[data-dci-action=fold] elements.
    window.djCommentsInk.folding_handler = null;
    // Handler of clicking events on a[data-dci-action=unfold] elements.
    window.djCommentsInk.unfolding_handler = null;

    /* ----------------------------------------------
     * Initialize main comment form.
     */
    const qs_cform = "[data-dci=comment-form]";
    if (window.djCommentsInk.comment_form === null &&
        document.querySelector(qs_cform)
    ) {
        window.djCommentsInk.comment_form = new CommentForm(qs_cform);
    }

    /* ----------------------------------------------
     * Initialize reply forms.
     */
    const qs_rform_base = "[data-dci=reply-form-template]";
    const qs_rforms = "[data-dci=reply-form]";
    if (window.djCommentsInk.reply_forms_handler === null &&
        document.querySelector(qs_rform_base) &&
        document.querySelectorAll(qs_rforms)
    ) {
        window.djCommentsInk.reply_forms_handler = new ReplyFormsHandler(
            qs_rform_base, qs_rforms
        );
    }

    /* ----------------------------------------------
     * Initialize fold/unfold of comments with level > 0.
     */
    if (window.djCommentsInk.folding_handler === null &&
        window.djCommentsInk.unfolding_handler === null
    ) {
        window.djCommentsInk.folding_handler = new FoldingHandler("fold");
        window.djCommentsInk.unfolding_handler = new FoldingHandler("unfold");
    }
}

export { init_comments };
