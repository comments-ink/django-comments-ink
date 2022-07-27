import ReactionsPanel from "./reactions_panel";
import { get_login_url, get_react_url } from "./utils";


export default class ReactionsHandler {
    constructor(configEl) {
        this.cfg_el = configEl;
        this.is_guest = this.cfg_el.dataset.guestUser === "1";
        this.is_input_allowed = this.cfg_el.dataset.inputAllowed === "1";
        this.login_url = get_login_url(this.cfg_el, this.is_guest);
        this.react_url = get_react_url(this.cfg_el, this.is_guest);

        // Initialize the buttons panels and their components.
        this.links = document.querySelectorAll("[data-dci=reactions-panel]");
        if (this.links.length === 0 && this.is_input_allowed) {
            throw new Error(
                "Cannot initialize reactions panel => There are " +
                "no elements with [data-dci=reactions-panel].");
        }
        this.active_visible_panel = "0";
        this.panels_visibility = new Map(); // Keys are 'comment_id'.
        this.event_handlers = [];
        this.add_event_listeners();
        this.listen_to_click_on_links();
        const qs_panel = "[data-dci=reactions-panel-template]";
        this.panel_el = document.querySelector(qs_panel);
        if (this.panel_el === undefined) {
            throw new Error("Cannot find element with ${qs_panel}.");
        }

        // Create object of class ReactionsPanel in charge of showing and
        // hiding the reactions panel around the clicked 'react' link.
        const opts = {
            panel_el: this.panel_el,
            is_guest: this.is_guest,
            login_url: this.login_url,
            react_url: this.react_url
        };
        this.reactions_panel = new ReactionsPanel(opts);
    }

    on_document_click(event) {
        const data_attr = event.target.getAttribute("data-dci");
        if (!data_attr || data_attr !== "reactions-panel") {
            this.reactions_panel.hide();
            if (this.active_visible_panel !== "0") {
                this.panels_visibility.set(this.active_visible_panel, false);
                this.active_visible_panel = "0";
            }
        }
    }

    on_document_key_up(event) {
        if (event.key === "Escape") {
            this.reactions_panel.hide();
            if (this.active_visible_panel !== "0") {
                this.panels_visibility.set(this.active_visible_panel, false);
                this.active_visible_panel = "0";
            }
        }
    }

    add_event_listeners() {
        const onDocumentClickHandler = this.on_document_click.bind(this);
        const onDocumentKeyUpHandler = this.on_document_key_up.bind(this);

        window.document.addEventListener('click', onDocumentClickHandler);
        window.document.addEventListener('keyup', onDocumentKeyUpHandler);

        this.event_handlers.push({
            elem: window.document,
            event: 'click',
            handler: this.on_document_click,
        });
        this.event_handlers.push({
            elem: window.document,
            event: 'keyup',
            handler: this.on_document_key_up,
        });
    }

    remove_event_listeners() {
        for (const item of this.event_handlers) {
            item.elem.removeEventListener(item.event, item.handler);
        }
    }

    listen_to_click_on_links() {
        for (const elem of Array.from(this.links)) {
            const comment_id = elem.getAttribute("data-comment");
            if (comment_id === null) {
                continue;
            }
            const click_handler = this.toggle_reactions_panel(comment_id);
            elem.addEventListener("click", click_handler);
            this.event_handlers.push({
                'elem': elem,
                'event': 'click',
                'handler': click_handler
            });
            this.panels_visibility.set(comment_id, false); // Not visible yet.
        }
    }

    toggle_reactions_panel(comment_id) {
        return (event) => {
            event.preventDefault();
            const is_visible = this.panels_visibility.get(comment_id);
            if (!is_visible) {
                this.active_visible_panel = comment_id;
                this.reactions_panel.show(event.target, comment_id);
            } else {
                this.active_visible_panel = "0";
                this.reactions_panel.hide();
            }
            this.panels_visibility.set(comment_id, !is_visible);
        };
    }
}
