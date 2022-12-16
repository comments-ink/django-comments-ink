/******/ (() => { // webpackBootstrap
/******/ 	"use strict";
/******/ 	var __webpack_modules__ = ({

/***/ "./django_comments_ink/static/django_comments_ink/js/comment_form.js":
/*!***************************************************************************!*\
  !*** ./django_comments_ink/static/django_comments_ink/js/comment_form.js ***!
  \***************************************************************************/
/***/ ((__unused_webpack_module, __webpack_exports__, __webpack_require__) => {

__webpack_require__.r(__webpack_exports__);
/* harmony export */ __webpack_require__.d(__webpack_exports__, {
/* harmony export */   "default": () => (/* binding */ CommentForm)
/* harmony export */ });
class CommentForm {
    constructor(formWrapper) {
        this.formWrapper = formWrapper;
        this.init();
    }

    click_on_post(_) { return this.post("post"); }

    click_on_preview(_) { return this.post("preview"); }

    init() {
        this.formWrapperEl = document.querySelector(this.formWrapper);
        this.formEl = this.formWrapperEl.querySelector("form");
        const post_btn = this.formEl.elements.post;
        const preview_btn = this.formEl.elements.preview;
        post_btn.addEventListener("click", (_) => this.post("post"));
        preview_btn.addEventListener("click", (_) => this.post("preview"));
        // Change the type of the buttons, otherwise the form is submitted.
        post_btn.type = "button";
        preview_btn.type = "button";
    }

    disable_btns(value) {
        this.formEl.elements.post.disabled = value;
        this.formEl.elements.preview.disabled = value;
    }

    is_valid() {
        for (const el of this.formEl.querySelectorAll("[required]")) {
            if (!el.reportValidity()) {
                el.focus();
                return false;
            }
        }
        return true;
    }

    post(submit_button_name) {
        if (!this.is_valid()) {
            return;
        }
        this.disable_btns(true);

        // If the <section data-dci="preview">...</section> does exist,
        // delete it. If the user clicks again in the "preview" button
        // it will be displayed again.
        const preview = this.formWrapperEl.querySelector("[data-dci=preview]");
        if (preview) {
            preview.remove();
        }

        const formData = new FormData(this.formEl);
        if (submit_button_name !== undefined) {
            formData.append(submit_button_name, 1);
        }

        fetch(this.formEl.action, {
            method: 'POST',
            headers: {
                "X-Requested-With": "XMLHttpRequest",
            },
            body: formData
        }).then(response => {
            if (submit_button_name === "preview") {
                this.handle_preview_comment_response(response);
            } else if (submit_button_name === "post") {
                this.handle_post_comment_response(response);
            }
        });

        this.disable_btns(false);
        return false; // To prevent calling the action attribute.
    }

    async handle_preview_comment_response(response) {
        const data = await response.json();
        if (response.status === 200) {
            this.formWrapperEl.innerHTML = data.html;
            this.init();
            if (data.field_focus) {
                this.formEl.querySelector(`[name=${data.field_focus}]`).focus();
            }
        } else if (response.status === 400) {
            this.formEl.innerHTML = data.html;
        }
    }

    async handle_post_comment_response(response) {
        const data = await response.json();

        if (response.status === 200) {
            this.formWrapperEl.innerHTML = data.html;
            this.init();
            if (data.field_focus) {
                this.formEl.querySelector(`[name=${data.field_focus}]`).focus();
            }
        }
        else if (
            response.status === 201 ||
            response.status === 202 ||
            response.status === 400
        ) {
            this.formEl.innerHTML = data.html;
        }
        else if (response.status > 400) {
            alert(
                "Something went wrong and your comment could not be " +
                "processed. Please, reload the page and try again."
            );
        }
    }
}


/***/ }),

/***/ "./django_comments_ink/static/django_comments_ink/js/comments.js":
/*!***********************************************************************!*\
  !*** ./django_comments_ink/static/django_comments_ink/js/comments.js ***!
  \***********************************************************************/
/***/ ((__unused_webpack_module, __webpack_exports__, __webpack_require__) => {

__webpack_require__.r(__webpack_exports__);
/* harmony export */ __webpack_require__.d(__webpack_exports__, {
/* harmony export */   "init_comments": () => (/* binding */ init_comments)
/* harmony export */ });
/* harmony import */ var _comment_form_js__WEBPACK_IMPORTED_MODULE_0__ = __webpack_require__(/*! ./comment_form.js */ "./django_comments_ink/static/django_comments_ink/js/comment_form.js");
/* harmony import */ var _reply_forms_js__WEBPACK_IMPORTED_MODULE_1__ = __webpack_require__(/*! ./reply_forms.js */ "./django_comments_ink/static/django_comments_ink/js/reply_forms.js");
/* harmony import */ var _folding_js__WEBPACK_IMPORTED_MODULE_2__ = __webpack_require__(/*! ./folding.js */ "./django_comments_ink/static/django_comments_ink/js/folding.js");





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
        window.djCommentsInk.comment_form = new _comment_form_js__WEBPACK_IMPORTED_MODULE_0__["default"](qs_cform);
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
        window.djCommentsInk.reply_forms_handler = new _reply_forms_js__WEBPACK_IMPORTED_MODULE_1__["default"](
            qs_rform_base, qs_rforms
        );
    }

    /* ----------------------------------------------
     * Initialize fold/unfold of comments with level > 0.
     */
    if (window.djCommentsInk.folding_handler === null &&
        window.djCommentsInk.unfolding_handler === null
    ) {
        window.djCommentsInk.folding_handler = new _folding_js__WEBPACK_IMPORTED_MODULE_2__["default"]("fold");
        window.djCommentsInk.unfolding_handler = new _folding_js__WEBPACK_IMPORTED_MODULE_2__["default"]("unfold");
    }
}




/***/ }),

/***/ "./django_comments_ink/static/django_comments_ink/js/flagging.js":
/*!***********************************************************************!*\
  !*** ./django_comments_ink/static/django_comments_ink/js/flagging.js ***!
  \***********************************************************************/
/***/ ((__unused_webpack_module, __webpack_exports__, __webpack_require__) => {

__webpack_require__.r(__webpack_exports__);
/* harmony export */ __webpack_require__.d(__webpack_exports__, {
/* harmony export */   "default": () => (/* binding */ FlaggingHandler),
/* harmony export */   "init_flagging": () => (/* binding */ init_flagging)
/* harmony export */ });
/* harmony import */ var _utils__WEBPACK_IMPORTED_MODULE_0__ = __webpack_require__(/*! ./utils */ "./django_comments_ink/static/django_comments_ink/js/utils.js");



class FlaggingHandler {
    constructor(configEl) {
        this.cfg_el = configEl;

        this.is_guest = this.cfg_el.dataset.guestUser === "1";
        this.login_url = (0,_utils__WEBPACK_IMPORTED_MODULE_0__.get_login_url)(this.cfg_el, this.is_guest);
        this.flag_url = (0,_utils__WEBPACK_IMPORTED_MODULE_0__.get_flag_url)(this.cfg_el, this.is_guest);

        this.qs_flag = '[data-dci-action="flag"]';
        const qs_flag = document.querySelectorAll(this.qs_flag);

        this.on_click = this.on_click.bind(this);
        qs_flag.forEach(el => el.addEventListener("click", this.on_click));
    }

    on_click(event) {
        event.preventDefault();
        const target = event.target;
        if (!this.is_guest) {
            this.comment_id = target.dataset.comment;
            const flag_url = this.flag_url.replace("0", this.comment_id);
            const code = target.dataset.code;
            const form_data = new FormData();
            form_data.append("flag", code);
            form_data.append("csrfmiddlewaretoken", (0,_utils__WEBPACK_IMPORTED_MODULE_0__.get_cookie)("csrftoken"));

            fetch(flag_url, {
                method: "POST",
                cache: "no-cache",
                credentials: "same-origin",
                headers: {
                    "X-Requested-With": "XMLHttpRequest",
                },
                body: form_data
            }).then(response => this.handle_flag_response(response));
        }
        else {
            const next_url = target.dataset.loginNext;
            window.location.href = `${this.login_url}?next=${next_url}`;
        }
    }

    async handle_flag_response(response) {
        const data = await response.json();
        if (response.status === 200 || response.status === 201) {
            const cm_flags_qs = `#cm-flags-${this.comment_id}`;
            const cm_flags_el = document.querySelector(cm_flags_qs);
            if (cm_flags_el) {
                cm_flags_el.innerHTML = data.html;
                const qs_flags = cm_flags_el.querySelector(this.qs_flag);
                if (qs_flags) {
                    qs_flags.addEventListener("click", this.on_click);
                }
            }
        } else if (response.status > 400) {
            alert(
                "Something went wrong and the flagging of the comment could not " +
                "be processed. Please, reload the page and try again."
            );
        }
    }
}

function init_flagging() {
    const cfg = document.querySelector("[data-dci=config]");
    if (cfg === null || window.djCommentsInk === null) {
        return;
    }

    window.djCommentsInk.flagging_handler = null;

    /* ----------------------------------------------
     * Initialize flagging as inappropriate for comments with level == 0.
     */
    if (window.djCommentsInk.flagging_handler === null) {
        window.djCommentsInk.flagging_handler = new FlaggingHandler(cfg);
    }
}





/***/ }),

/***/ "./django_comments_ink/static/django_comments_ink/js/folding.js":
/*!**********************************************************************!*\
  !*** ./django_comments_ink/static/django_comments_ink/js/folding.js ***!
  \**********************************************************************/
/***/ ((__unused_webpack_module, __webpack_exports__, __webpack_require__) => {

__webpack_require__.r(__webpack_exports__);
/* harmony export */ __webpack_require__.d(__webpack_exports__, {
/* harmony export */   "default": () => (/* binding */ FoldingHandler)
/* harmony export */ });
class FoldingHandler {
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


/***/ }),

/***/ "./django_comments_ink/static/django_comments_ink/js/reactions.js":
/*!************************************************************************!*\
  !*** ./django_comments_ink/static/django_comments_ink/js/reactions.js ***!
  \************************************************************************/
/***/ ((__unused_webpack_module, __webpack_exports__, __webpack_require__) => {

__webpack_require__.r(__webpack_exports__);
/* harmony export */ __webpack_require__.d(__webpack_exports__, {
/* harmony export */   "init_reactions": () => (/* binding */ init_reactions)
/* harmony export */ });
/* harmony import */ var _reactions_handler__WEBPACK_IMPORTED_MODULE_0__ = __webpack_require__(/*! ./reactions_handler */ "./django_comments_ink/static/django_comments_ink/js/reactions_handler.js");
/* harmony import */ var _voting_js__WEBPACK_IMPORTED_MODULE_1__ = __webpack_require__(/*! ./voting.js */ "./django_comments_ink/static/django_comments_ink/js/voting.js");




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
        window.djCommentsInk.reactions_handler = new _reactions_handler__WEBPACK_IMPORTED_MODULE_0__["default"](cfg);
        window.addEventListener("beforeunload", (_) => {
            window.djCommentsInk.reactions_handler.remove_event_listeners();
        });
    }

    /* ----------------------------------------------
     * Initialize voting up/down of comments with level == 0.
     */
    if (window.djCommentsInk.voting_handler === null) {
        window.djCommentsInk.voting_handler = new _voting_js__WEBPACK_IMPORTED_MODULE_1__["default"](cfg);
    }
}




/***/ }),

/***/ "./django_comments_ink/static/django_comments_ink/js/reactions_handler.js":
/*!********************************************************************************!*\
  !*** ./django_comments_ink/static/django_comments_ink/js/reactions_handler.js ***!
  \********************************************************************************/
/***/ ((__unused_webpack_module, __webpack_exports__, __webpack_require__) => {

__webpack_require__.r(__webpack_exports__);
/* harmony export */ __webpack_require__.d(__webpack_exports__, {
/* harmony export */   "default": () => (/* binding */ ReactionsHandler)
/* harmony export */ });
/* harmony import */ var _reactions_panel__WEBPACK_IMPORTED_MODULE_0__ = __webpack_require__(/*! ./reactions_panel */ "./django_comments_ink/static/django_comments_ink/js/reactions_panel.js");
/* harmony import */ var _utils__WEBPACK_IMPORTED_MODULE_1__ = __webpack_require__(/*! ./utils */ "./django_comments_ink/static/django_comments_ink/js/utils.js");




class ReactionsHandler {
    constructor(configEl) {
        this.cfg_el = configEl;
        this.is_guest = this.cfg_el.dataset.guestUser === "1";
        this.is_input_allowed = this.cfg_el.dataset.inputAllowed === "1";
        this.login_url = (0,_utils__WEBPACK_IMPORTED_MODULE_1__.get_login_url)(this.cfg_el, this.is_guest);
        this.react_url = (0,_utils__WEBPACK_IMPORTED_MODULE_1__.get_react_url)(this.cfg_el, this.is_guest);

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
        this.reactions_panel = new _reactions_panel__WEBPACK_IMPORTED_MODULE_0__["default"](opts);
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


/***/ }),

/***/ "./django_comments_ink/static/django_comments_ink/js/reactions_panel.js":
/*!******************************************************************************!*\
  !*** ./django_comments_ink/static/django_comments_ink/js/reactions_panel.js ***!
  \******************************************************************************/
/***/ ((__unused_webpack_module, __webpack_exports__, __webpack_require__) => {

__webpack_require__.r(__webpack_exports__);
/* harmony export */ __webpack_require__.d(__webpack_exports__, {
/* harmony export */   "default": () => (/* binding */ ReactionsPanel)
/* harmony export */ });
/* harmony import */ var _utils__WEBPACK_IMPORTED_MODULE_0__ = __webpack_require__(/*! ./utils */ "./django_comments_ink/static/django_comments_ink/js/utils.js");


const enter_delay = 0;
const exit_delay = 0;

class ReactionsPanel {
    constructor({panel_el, is_guest, login_url, react_url } = opts) {
        this.panel_el = panel_el;
        // this.panel_el.style.zIndex = 1;
        // this.panel_el.style.display = "block";
        this.arrow_el = panel_el.querySelector(".arrow");
        this.is_guest = is_guest;
        this.login_url = login_url;
        this.react_url = react_url;

        // -----------------------------------------------------
        // The panel_title_elem and its content panel_title will
        // change when the user hover the buttons of the panel.

        this.panel_title = "";
        this.panel_title_elem = this.panel_el.querySelector(".title");
        if (this.panel_title_elem) {
            this.panel_title = this.panel_title_elem.textContent;
        }

        // -----------------------------------------
        // The comment_id is necessary to know which
        // comment will receive the reaction code.

        this.comment_id = 0; // Valid comment_id must be > 0.
        this.next_url = ""; // Comment URL to come back after log in.

        this.on_react_btn_click = this.on_react_btn_click.bind(this);
        this.on_react_btn_mouseover = this.on_react_btn_mouseover.bind(this);
        this.on_react_btn_mouseout = this.on_react_btn_mouseout.bind(this);
        this.add_event_listeners();
    }

    add_event_listeners() {
        const buttons = this.panel_el.querySelectorAll("button");
        for (const btn of Array.from(buttons)) {
            btn.addEventListener("click", this.on_react_btn_click);
            btn.addEventListener("mouseover", this.on_react_btn_mouseover);
            btn.addEventListener("mouseout", this.on_react_btn_mouseout);
        }
    }

    on_react_btn_click(event) {
        if (!this.is_guest) {
            const code = event.target.dataset.code;
            const react_url = this.react_url.replace("0", this.comment_id);
            const formData = new FormData();
            formData.append("reaction", code);
            formData.append("csrfmiddlewaretoken", (0,_utils__WEBPACK_IMPORTED_MODULE_0__.get_cookie)("csrftoken"));

            fetch(react_url, {
                method: "POST",
                cache: "no-cache",
                credentials: "same-origin",
                headers: {
                    "X-Requested-With": "XMLHttpRequest",
                },
                body: formData
            }).then(response => this.handle_reactions_response(response));
        } else {
            window.location.href = `${this.login_url}?next=${this.next_url}`;
        }
    }

    async handle_reactions_response(response) {
        const data = await response.json();
        if (response.status === 200 || response.status === 201) {
            const cm_reactions_qs = `#cm-reactions-${this.comment_id}`;
            const cm_reactions_el = document.querySelector(cm_reactions_qs);
            if (cm_reactions_el) {
                cm_reactions_el.innerHTML = data.html;
            }
        } else if (response.status > 400) {
            alert(
                "Something went wrong and your comment reaction could not " +
                "be processed. Please, reload the page and try again."
            );
        }
    }

    on_react_btn_mouseover(event) {
        if (this.panel_title_elem) {
            this.panel_title_elem.textContent = event.target.dataset.title;
        }
    }

    on_react_btn_mouseout(_) {
        this.panel_title_elem.textContent = this.panel_title;
    }

    set_position(trigger_elem) {
        this.panel_el.style.display = "block";

        const panel_elem_coords = this.get_absolute_coords(this.panel_el);
        const trigger_elem_coords = this.get_absolute_coords(trigger_elem);

        const panel_elem_width = panel_elem_coords.width;
        const panel_elem_height = panel_elem_coords.height;
        const panel_elem_top = panel_elem_coords.top;
        const panel_elem_left = panel_elem_coords.left;

        const trigger_elem_width = trigger_elem_coords.width;
        const trigger_elem_top = trigger_elem_coords.top;
        const trigger_elem_left = trigger_elem_coords.left;

        const top_diff = trigger_elem_top - panel_elem_top;
        const left_diff = trigger_elem_left - panel_elem_left;

        // This group of const values can be hardcoded somewhere else.
        // const position = "auto";
        const margin = 8;

        const width_center = trigger_elem_width / 2 - panel_elem_width / 2;

        const left = left_diff + width_center;
        const top = top_diff - panel_elem_height - margin;
        const from_top = top + 10;

        this.panel_el.dataset.fromLeft = left;
        this.panel_el.dataset.fromTop = from_top;
        this.panel_el.dataset.left = left;
        this.panel_el.dataset.top = top;

        // Arrow.
        if (this.arrow_el) {
            let arrow_left = 0;
            const full_left = left + panel_elem_left;
            const t_width_center = trigger_elem_width / 2 + trigger_elem_left;
            arrow_left = t_width_center - full_left;
            const transform_text = `translate3d(${arrow_left}px, 0px, 0)`;
            this.arrow_el.style.transform = transform_text;
        }
    }

    hide() {
        clearTimeout(this.enter_delay_timeout);

        this.exit_delat_timeout = setTimeout(() => {
            if (this.panel_el) {
                const left = this.panel_el.dataset.fromLeft;
                const top = this.panel_el.dataset.fromTop;
                const transform_text = `translate3d(${left}px, ${top}px, 0)`;

                this.panel_el.style.transform = transform_text;
                this.panel_el.style.opacity = 0;
                this.panel_el.style.display = "none";
                this.panel_el.style.zIndex = 0;
            }
        }, exit_delay);
    }

    show(trigger_elem, comment_id) {
        this.comment_id = comment_id;
        this.next_url = trigger_elem.dataset.loginNext || "";
        this.panel_el.style.transform = "none";
        this.set_position(trigger_elem);

        this.enter_delay_timeout = setTimeout(() => {
            const left = this.panel_el.dataset.left;
            const top = this.panel_el.dataset.top;
            const transform_text = `translate3d(${left}px, ${top}px, 0)`;

            this.panel_el.style.zIndex = 1;
            this.panel_el.style.display = "block";
            this.panel_el.style.transform = transform_text;
            this.panel_el.style.opacity = 1;
        }, enter_delay);
    }

    get_absolute_coords(elem) {
        if (!elem) {
            return;
        }

        const box = elem.getBoundingClientRect();
        const page_x = window.pageXOffset;
        const page_y = window.pageYOffset;

        return {
            width: box.width,
            height: box.height,
            top: box.top + page_y,
            right: box.right + page_x,
            bottom: box.bottom + page_y,
            left: box.left + page_x,
        };
    }
}


/***/ }),

/***/ "./django_comments_ink/static/django_comments_ink/js/reply_forms.js":
/*!**************************************************************************!*\
  !*** ./django_comments_ink/static/django_comments_ink/js/reply_forms.js ***!
  \**************************************************************************/
/***/ ((__unused_webpack_module, __webpack_exports__, __webpack_require__) => {

__webpack_require__.r(__webpack_exports__);
/* harmony export */ __webpack_require__.d(__webpack_exports__, {
/* harmony export */   "default": () => (/* binding */ ReplyFormsHandler)
/* harmony export */ });
class ReplyFormsHandler {
    constructor(qsReplyFormBase, qsReplyForms) {
        this.replyFormBase = document.querySelector(qsReplyFormBase);
        this.replyMap = new Map();

        const cpage_field = window.djCommentsInk.page_param || "cpage";

        for (const elem of document.querySelectorAll(qsReplyForms)) {
            // Extract the reply_to value from the current reply_form.
            // Also, if it does exist, extract the comment's page number too.
            // Then replace the content of elem with a copy of
            // this.replyFormBase and update the fields reply_to
            // and comment's page number.
            const rFormEl = elem.querySelector("form");
            if (rFormEl === null) {
                console.error(
                    `Could not find a reply form within one of ` +
                    `the elements retrieved with ${qsReplyForms}.`
                );
                return;
            }

            const reply_to = rFormEl.elements.reply_to.value;
            const cpage = rFormEl.elements[cpage_field]
                ? rFormEl.elements[cpage_field].value
                : null;

            const section = this.replyFormBase.cloneNode(true);
            section.dataset.dci = `reply-form-${reply_to}`;

            // Update fields reply_to and cpage..
            const newForm = section.querySelector("form");
            newForm.elements.reply_to.value = reply_to;
            if (cpage) {
                newForm.elements[cpage_field].value = cpage;
            }

            const elemParent = elem.parentNode;
            elem.replaceWith(section);
            this.init(reply_to);
            this.replyMap.set(reply_to, elemParent);
        }
    }

    init(reply_to, is_active) {
        const qs_section = `[data-dci=reply-form-${reply_to}]`;
        const section = document.querySelector(qs_section);

        // Modify the form (update fields, add event listeners).
        const newForm = section.querySelector("form");
        const post_btn = newForm.elements.post;
        post_btn.addEventListener("click", this.send_clicked(reply_to));
        const preview_btn = newForm.elements.preview;
        preview_btn.addEventListener("click", this.preview_clicked(reply_to));
        const cancel_btn = newForm.elements.cancel;
        cancel_btn.addEventListener("click", this.cancel_clicked(reply_to));
        newForm.style.display = "none";

        // Attach event listener to textarea.
        const divta = section.querySelector("[data-dci=reply-textarea]");
        const ta = divta.querySelector("textarea");
        ta.addEventListener("focus", this.textarea_focus(reply_to));

        // If is_active is true, hide the textarea and display the form.
        if (is_active === true) {
            section.classList.add("active");
            divta.style.display = "none";
            newForm.style = "";
            newForm.elements.comment.focus();
        }
    }

    get_map_item(reply_to) {
        const item = this.replyMap.get(reply_to);
        if (item === undefined) {
            const msg = `replyMap doesn't have a key ${reply_to}`;
            console.error(msg);
            throw msg;
        }
        return item;
    }

    disable_buttons(formEl, value) {
        formEl.elements.post.disabled = value;
        formEl.elements.preview.disabled = value;
    }

    is_valid(formEl) {
        for (const el of formEl.querySelectorAll("[required]")) {
            if (!el.reportValidity()) {
                el.focus();
                return false;
            }
        }
        return true;
    }

    textarea_focus(reply_to) {
        // Display the comment form and hide the text area.
        return (_) => {
            const item = this.get_map_item(reply_to);
            const qs_section = `[data-dci=reply-form-${reply_to}`;
            const section = item.querySelector(qs_section);
            const form = section.querySelector("form");
            const divta = section.querySelector("[data-dci=reply-textarea]");
            section.classList.toggle("active");
            divta.style.display = "none";
            form.style = "";
            form.elements.comment.focus();
        };
    }

    cancel_clicked(reply_to) {
    // Display the text area and hide the comment form.
        return (_) => {
            const item = this.get_map_item(reply_to);
            const qs_section = `[data-dci=reply-form-${reply_to}`;
            const section = item.querySelector(qs_section);
            const form = section.querySelector("form");
            const divta = section.querySelector("[data-dci=reply-textarea]");
            const comment_value = form.elements.comment.value;
            divta.querySelector("textarea").value = comment_value;
            section.classList.toggle("active");
            form.style.display = "none";
            divta.style = "";

            const previewEl = item.querySelector("[data-dci=preview]");
            if (previewEl) {
                previewEl.remove();
            }
        };
    }

    preview_clicked(reply_to) {
        return (_) => {
            this.post("preview", reply_to);
        };
    }

    send_clicked(reply_to) {
        return (_) => {
            this.post("post", reply_to);
        };
    }

    post(submit_button_name, reply_to) {
        const item = this.get_map_item(reply_to);
        const formEl = item.querySelector("form");

        if (!this.is_valid(formEl)) {
            return;
        }

        this.disable_buttons(formEl, true);

        const previewEl = item.querySelector("[data-dci=preview]");
        if (previewEl) {
            previewEl.remove();
        }

        const formData = new FormData(formEl);
        if (submit_button_name !== undefined) {
            formData.append(submit_button_name, 1);
        }

        fetch(formEl.action, {
            method: "POST",
            headers: {
                "X-Requested-With": "XMLHttpRequest",
            },
            body: formData
        }).then(response => {
            if (submit_button_name === "preview") {
                this.handle_preview_comment_response(response, reply_to);
            } else if (submit_button_name === "post") {
                this.handle_post_comment_response(response, reply_to);
            }
        });
        this.disable_buttons(formEl, false);
        return false; // To prevent calling the action attribute.
    }

    handle_http_200(item, data, reply_to) {
        item.innerHTML = data.html;
        this.init(reply_to, true); // 2nd param: is_active = true.
        if (data.field_focus) {
            item.querySelector(`[name=${data.field_focus}]`).focus();
        }
    }

    handle_http_201_202_400(item, data) {
        const form = item.querySelector("form");
        form.innerHTML = data.html;
    }

    async handle_preview_comment_response(response, reply_to) {
        const item = this.get_map_item(reply_to);
        const data = await response.json();

        if (response.status === 200) {
            this.handle_http_200(item, data, reply_to);
        } else if (response.status === 400) {
            this.handle_http_201_202_400(item, data);
        }
    }

    async handle_post_comment_response(response, reply_to) {
        const item = this.get_map_item(reply_to);
        const data = await response.json();

        if (response.status === 200) {
            this.handle_http_200(item, data, reply_to);
        }
        else if (
            response.status === 201 ||
            response.status === 202 ||
            response.status === 400
        ) {
            this.handle_http_201_202_400(item, data);
        }
        else if (response.status > 400) {
            alert(
                "Something went wrong and your comment could not be " +
                "processed. Please, reload the page and try again."
            );
        }
    }
}


/***/ }),

/***/ "./django_comments_ink/static/django_comments_ink/js/utils.js":
/*!********************************************************************!*\
  !*** ./django_comments_ink/static/django_comments_ink/js/utils.js ***!
  \********************************************************************/
/***/ ((__unused_webpack_module, __webpack_exports__, __webpack_require__) => {

__webpack_require__.r(__webpack_exports__);
/* harmony export */ __webpack_require__.d(__webpack_exports__, {
/* harmony export */   "get_cookie": () => (/* binding */ get_cookie),
/* harmony export */   "get_flag_url": () => (/* binding */ get_flag_url),
/* harmony export */   "get_login_url": () => (/* binding */ get_login_url),
/* harmony export */   "get_obj_react_url": () => (/* binding */ get_obj_react_url),
/* harmony export */   "get_react_url": () => (/* binding */ get_react_url),
/* harmony export */   "get_vote_url": () => (/* binding */ get_vote_url)
/* harmony export */ });
function get_cookie(name) {
    let cookieValue = null;
    if (document.cookie && document.cookie !== '') {
        const cookies = document.cookie.split(';');
        for (let i = 0; i < cookies.length; i++) {
            const cookie = cookies[i].trim();
            // Does this cookie string begin with the name we want?
            if (cookie.substring(0, name.length + 1) === (name + '=')) {
                cookieValue = decodeURIComponent(cookie.substring(name.length + 1));
                break;
            }
        }
    }
    return cookieValue;
}

function get_login_url(configEl, isGuest) {
    const url = configEl.getAttribute("data-login-url");
    if (url === null || url.length === 0) {
        if (isGuest) {
            throw new Error("Cannot find the [data-login-url] attribute.");
        }
    }
    return url;
}

function get_react_url(configEl, isGuest) {
    const url = configEl.getAttribute("data-react-url");
    if (url === null || url.length === 0) {
        if (!isGuest) {
            throw new Error("Cannot initialize reactions panel => The " +
                "[data-react-url] attribute does not exist or is empty.");
        } else {
            console.info("Couldn't find the data-react-url attribute, " +
                "but the user is anonymous. She has to login first in " +
                "order to post comment reactions.");
        }
    }
    return url;
}

function get_obj_react_url(configEl, isGuest) {
    const url = configEl.getAttribute("data-obj-react-url");
    if (url === null || url.length === 0) {
        if (!isGuest) {
            throw new Error("Cannot initialize reactions panel => The " +
                "[data-obj-react-url] attribute does not exist or is empty.");
        } else {
            console.info("Couldn't find the data-obj-react-url attribute, " +
                "but the user is anonymous. She has to login first in " +
                "order to post object reactions.");
        }
    }
    return url;
}

function get_vote_url(configEl, isGuest) {
    const url = configEl.getAttribute("data-vote-url");
    if (url === null || url.length === 0) {
        if (!isGuest) {
            throw new Error("Cannot initialize comment voting => The " +
                "[data-vote-url] attribute does not exist or is empty.");
        } else {
            console.info("Couldn't find the data-vote-url attribute, " +
                "but the user is anonymous. She has to login first in " +
                "order to vote for comments.");
        }
    }
    return url;
}

function get_flag_url(configEl, isGuest) {
    const url = configEl.getAttribute("data-flag-url");
    if (url === null || url.length === 0) {
        if (!isGuest) {
            throw new Error("Cannot initialize comment flagging => The " +
                "[data-flag-url] attribute does not exist or is empty.");
        } else {
            console.info("Couldn't find the data-flag-url attribute, " +
                "but the user is anonymous. She has to login first in " +
                "order to flag comments.");
        }
    }
    return url;
}


/***/ }),

/***/ "./django_comments_ink/static/django_comments_ink/js/voting.js":
/*!*********************************************************************!*\
  !*** ./django_comments_ink/static/django_comments_ink/js/voting.js ***!
  \*********************************************************************/
/***/ ((__unused_webpack_module, __webpack_exports__, __webpack_require__) => {

__webpack_require__.r(__webpack_exports__);
/* harmony export */ __webpack_require__.d(__webpack_exports__, {
/* harmony export */   "default": () => (/* binding */ VotingHandler)
/* harmony export */ });
/* harmony import */ var _utils__WEBPACK_IMPORTED_MODULE_0__ = __webpack_require__(/*! ./utils */ "./django_comments_ink/static/django_comments_ink/js/utils.js");



class VotingHandler {
    constructor(configEl) {
        this.cfg_el = configEl;

        this.is_guest = this.cfg_el.dataset.guestUser === "1";
        this.login_url = (0,_utils__WEBPACK_IMPORTED_MODULE_0__.get_login_url)(this.cfg_el, this.is_guest);
        this.vote_url = (0,_utils__WEBPACK_IMPORTED_MODULE_0__.get_vote_url)(this.cfg_el, this.is_guest);

        this.qs_up = '[data-dci-action="vote-up"]';
        this.qs_down = '[data-dci-action="vote-down"]';
        const qs_vote_up = document.querySelectorAll(this.qs_up);
        const qs_vote_down = document.querySelectorAll(this.qs_down);

        this.on_click = this.on_click.bind(this);
        qs_vote_up.forEach(el => el.addEventListener("click", this.on_click));
        qs_vote_down.forEach(el => el.addEventListener("click", this.on_click));
    }

    on_click(event) {
        event.preventDefault();
        const target = event.target;
        if (!this.is_guest) {
            this.comment_id = target.dataset.comment;
            const vote_url = this.vote_url.replace("0", this.comment_id);
            const code = target.dataset.code;
            const form_data = new FormData();
            form_data.append("vote", code);
            form_data.append("csrfmiddlewaretoken", (0,_utils__WEBPACK_IMPORTED_MODULE_0__.get_cookie)("csrftoken"));

            fetch(vote_url, {
                method: "POST",
                cache: "no-cache",
                credentials: "same-origin",
                headers: {
                    "X-Requested-With": "XMLHttpRequest",
                },
                body: form_data
            }).then(response => this.handle_vote_response(response));
        }
        else {
            const next_url = target.dataset.loginNext;
            window.location.href = `${this.login_url}?next=${next_url}`;
        }
    }

    async handle_vote_response(response) {
        const data = await response.json();
        if (response.status === 200 || response.status === 201) {
            const cm_votes_qs = `#cm-votes-${this.comment_id}`;
            const cm_votes_el = document.querySelector(cm_votes_qs);
            if (cm_votes_el) {
                cm_votes_el.innerHTML = data.html;
                const qs_vote_up = cm_votes_el.querySelector(this.qs_up);
                if (qs_vote_up) {
                    qs_vote_up.addEventListener("click", this.on_click);
                }
                const qs_vote_down = cm_votes_el.querySelector(this.qs_down);
                if (qs_vote_down) {
                    qs_vote_down.addEventListener("click", this.on_click);
                }
            }
        } else if (response.status > 400) {
            alert(
                "Something went wrong and your comment vote could not " +
                "be processed. Please, reload the page and try again."
            );
        }
    }
}


/***/ })

/******/ 	});
/************************************************************************/
/******/ 	// The module cache
/******/ 	var __webpack_module_cache__ = {};
/******/ 	
/******/ 	// The require function
/******/ 	function __webpack_require__(moduleId) {
/******/ 		// Check if module is in cache
/******/ 		var cachedModule = __webpack_module_cache__[moduleId];
/******/ 		if (cachedModule !== undefined) {
/******/ 			return cachedModule.exports;
/******/ 		}
/******/ 		// Create a new module (and put it into the cache)
/******/ 		var module = __webpack_module_cache__[moduleId] = {
/******/ 			// no module.id needed
/******/ 			// no module.loaded needed
/******/ 			exports: {}
/******/ 		};
/******/ 	
/******/ 		// Execute the module function
/******/ 		__webpack_modules__[moduleId](module, module.exports, __webpack_require__);
/******/ 	
/******/ 		// Return the exports of the module
/******/ 		return module.exports;
/******/ 	}
/******/ 	
/************************************************************************/
/******/ 	/* webpack/runtime/define property getters */
/******/ 	(() => {
/******/ 		// define getter functions for harmony exports
/******/ 		__webpack_require__.d = (exports, definition) => {
/******/ 			for(var key in definition) {
/******/ 				if(__webpack_require__.o(definition, key) && !__webpack_require__.o(exports, key)) {
/******/ 					Object.defineProperty(exports, key, { enumerable: true, get: definition[key] });
/******/ 				}
/******/ 			}
/******/ 		};
/******/ 	})();
/******/ 	
/******/ 	/* webpack/runtime/hasOwnProperty shorthand */
/******/ 	(() => {
/******/ 		__webpack_require__.o = (obj, prop) => (Object.prototype.hasOwnProperty.call(obj, prop))
/******/ 	})();
/******/ 	
/******/ 	/* webpack/runtime/make namespace object */
/******/ 	(() => {
/******/ 		// define __esModule on exports
/******/ 		__webpack_require__.r = (exports) => {
/******/ 			if(typeof Symbol !== 'undefined' && Symbol.toStringTag) {
/******/ 				Object.defineProperty(exports, Symbol.toStringTag, { value: 'Module' });
/******/ 			}
/******/ 			Object.defineProperty(exports, '__esModule', { value: true });
/******/ 		};
/******/ 	})();
/******/ 	
/************************************************************************/
var __webpack_exports__ = {};
// This entry need to be wrapped in an IIFE because it need to be isolated against other modules in the chunk.
(() => {
/*!********************************************************************!*\
  !*** ./django_comments_ink/static/django_comments_ink/js/index.js ***!
  \********************************************************************/
__webpack_require__.r(__webpack_exports__);
/* harmony import */ var _comments_js__WEBPACK_IMPORTED_MODULE_0__ = __webpack_require__(/*! ./comments.js */ "./django_comments_ink/static/django_comments_ink/js/comments.js");
/* harmony import */ var _reactions_js__WEBPACK_IMPORTED_MODULE_1__ = __webpack_require__(/*! ./reactions.js */ "./django_comments_ink/static/django_comments_ink/js/reactions.js");
/* harmony import */ var _flagging_js__WEBPACK_IMPORTED_MODULE_2__ = __webpack_require__(/*! ./flagging.js */ "./django_comments_ink/static/django_comments_ink/js/flagging.js");




window.djCommentsInk = {
    init_comments: _comments_js__WEBPACK_IMPORTED_MODULE_0__.init_comments,
    init_reactions: _reactions_js__WEBPACK_IMPORTED_MODULE_1__.init_reactions,
    init_flagging: _flagging_js__WEBPACK_IMPORTED_MODULE_2__.init_flagging
};

window.addEventListener("DOMContentLoaded", (_) => {
    (0,_comments_js__WEBPACK_IMPORTED_MODULE_0__.init_comments)();
    (0,_reactions_js__WEBPACK_IMPORTED_MODULE_1__.init_reactions)();
    (0,_flagging_js__WEBPACK_IMPORTED_MODULE_2__.init_flagging)();
});

})();

/******/ })()
;
//# sourceMappingURL=dci-0.3.0.js.map