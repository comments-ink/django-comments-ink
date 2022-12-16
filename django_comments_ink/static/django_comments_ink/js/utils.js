export function get_cookie(name) {
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

export function get_login_url(configEl, isGuest) {
    const url = configEl.getAttribute("data-login-url");
    if (url === null || url.length === 0) {
        if (isGuest) {
            throw new Error("Cannot find the [data-login-url] attribute.");
        }
    }
    return url;
}

export function get_react_url(configEl, isGuest) {
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

export function get_obj_react_url(configEl, isGuest) {
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

export function get_vote_url(configEl, isGuest) {
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

export function get_flag_url(configEl, isGuest) {
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
