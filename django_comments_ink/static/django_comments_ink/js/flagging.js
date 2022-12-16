import { get_cookie, get_login_url, get_flag_url } from "./utils";


export default class FlaggingHandler {
    constructor(configEl) {
        this.cfg_el = configEl;

        this.is_guest = this.cfg_el.dataset.guestUser === "1";
        this.login_url = get_login_url(this.cfg_el, this.is_guest);
        this.flag_url = get_flag_url(this.cfg_el, this.is_guest);

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
            form_data.append("csrfmiddlewaretoken", get_cookie("csrftoken"));

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


export { init_flagging };
