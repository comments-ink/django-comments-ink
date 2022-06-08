import CommentForm from "./comment_form.js";
import ReplyFormsHandler from "./reply_forms.js";
import FoldingHandler from "./folding.js";

function init_comments() {
    if (window.dci === null) {
        return;
    }

    if (window.dci.page_param === undefined) {
        const rroot = document.querySelector("[data-dci=config]");
        if (rroot) {
            window.dci.page_param = rroot.getAttribute("data-page-qs-param");
        }
    }

    window.dci.comment_form = null;
    window.dci.reply_forms_handler = null;
    window.dci_folding_handler = null;
    window.dci_unfolding_handler = null;

    /* ----------------------------------------------
     * Initialize main comment form.
     */
    const qs_cform = "[data-dci=comment-form]";
    if (window.dci.comment_form === null &&
        document.querySelector(qs_cform)
    ) {
        window.dci.comment_form = new CommentForm(qs_cform);
    }

    /* ----------------------------------------------
     * Initialize reply forms.
     */
    const qs_rform_base = "[data-dci=reply-form-template]";
    const qs_rforms = "[data-dci=reply-form]";
    if (window.dci.reply_forms_handler === null &&
        document.querySelector(qs_rform_base) &&
        document.querySelectorAll(qs_rforms)
    ) {
        window.dci.reply_forms_handler = new ReplyFormsHandler(qs_rform_base, qs_rforms);
    }

    /* ----------------------------------------------
     * Initialize fold/unfold of comments with level > 0.
     */
    window.dci.folding_handler = new FoldingHandler("fold");
    window.dci.unfolding_handler = new FoldingHandler("unfold");
}

export { init_comments };
