import { get_cookie, get_login_url, get_vote_url } from "./utils";


export default class VotingHandler {
    constructor(configEl) {
        this.cfg_el = configEl;

        this.is_guest = this.cfg_el.dataset.guestUser === "1";
        this.login_url = get_login_url(this.cfg_el, this.is_guest);
        this.vote_url = get_vote_url(this.cfg_el, this.is_guest);

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
            form_data.append("csrfmiddlewaretoken", get_cookie("csrftoken"));

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
