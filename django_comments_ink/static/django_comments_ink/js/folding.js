export default class FoldingHandler {
    constructor(direction) {
        this.dir = direction; // Direction can be either 'fold' or 'unfold'.
        this.target_comment = undefined;
        this.comment_replies = -1;

        const qs = `[data-dci-action=${this.dir}]`;
        const qs_links = document.querySelectorAll(qs);

        const onLinkClickHandler = this.on_click.bind(this);

        qs_links.forEach(elem => {
            if (direction === "fold") {
                // By default, when loading the page all comments are
                // unfolded, so the 'fold' link has to be visible.
                elem.classList.remove("hide");
            }
            // If the fold link is clicked, it should trigger
            // the folding of the comments underneath.
            elem.addEventListener("click", onLinkClickHandler);
        });
    }

    on_click(event) {
        event.preventDefault();
        // Find the <div id="comment-{id}"> of the clicked element.
        this.target_comment = event.target.closest(".comment").parentNode;
        // Read the number of sibling elements that have to be hidden.
        this.comment_replies = parseInt(event.target.dataset.dciReplies);

        this.fold_or_unfold_siblings();

        // Hide the link clicked, and make visible the inverse link.
        const bits = this.target_comment.getAttribute("id").split("-");
        console.assert(bits.length === 2 && bits[0] === "comment");
        const cm_id = parseInt(bits[1]);
        this.turn_links(cm_id);
    }

    turn_links(cm_id) {
        const dir_lid = `${this.dir}-${cm_id}`;
        const direct_link = document.getElementById(dir_lid);
        if (direct_link !== null) {
            direct_link.classList.add("hide");
        }
        const inv_lid = (this.dir === 'fold' ? 'unfold' : 'fold') + `-${cm_id}`;
        const inverse_link = document.getElementById(inv_lid);
        if (inverse_link !== null) {
            inverse_link.classList.remove("hide");
        }
    }

    fold_or_unfold_siblings() {
        let num_processed = 0; // Number of <div id="comment-{id}"> processed.
        let next_node = this.target_comment.nextElementSibling;

        while(next_node && (num_processed < this.comment_replies)) {
            const cm_attr_id = next_node.getAttribute("id");
            const bits = cm_attr_id.split("-");

            // If the node is a <div id="reply-to-{id}"> element, skip it.
            // They are hidden explicitly when processing the
            // <div id="comment-{id}"> counterpart.

            if (
                (bits.length === 3) &&
                (bits[0] === "reply") && (bits[1] === "to")
            ) {
                next_node = next_node.nextElementSibling;
                continue;
            }
            else if ((bits.length === 2) && (bits[0] === "comment")) {
                const cm_id = parseInt(bits[1]);

                // If the comment has a reply node, toggle it.
                const reply_id = `reply-to-${cm_id}`;
                const reply_node = document.getElementById(reply_id);
                if(reply_node) {
                    this.toggle(reply_node);
                }

                this.turn_links(cm_id); // Turn the fold/unfold links.
                this.toggle(next_node); // Toggle the comment too.

                next_node = next_node.nextElementSibling;
                num_processed++;
            }
        }
    }

    toggle(node) {
        if (this.dir === "fold") {
            node.classList.add("hide");
        } else if (this.dir === "unfold") {
            node.classList.remove("hide");
        }
    }
}
