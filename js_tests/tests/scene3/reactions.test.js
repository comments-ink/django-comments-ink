import path from 'path';

import {
    fireEvent, waitFor,
} from '@testing-library/dom';
import '@testing-library/jest-dom/extend-expect';
import { JSDOM, ResourceLoader } from 'jsdom';


const html_path = path.resolve(__dirname, './index.html');

let dom;
let container;

describe("scene 3 - reactions.test.js module", () => {
    beforeEach(async () => {
        const resourceLoader = new ResourceLoader({
            proxy: "http://localhost:3000",
            strictSSL: false
        });
        const opts = { runScripts: "dangerously", resources: resourceLoader };
        dom = await JSDOM.fromFile(html_path, opts);
        await new Promise(resolve => {
            dom.window.addEventListener("DOMContentLoaded", () => {
                container = dom.window.document.body;
                resolve();
            });
        });
    });

    it("makes window.djCommentsInk.comment_form attribute !== null", () => {
        expect(
            dom.window.djCommentsInk !== null &&
            dom.window.djCommentsInk !== undefined
        ).toBe(true);
        expect(dom.window.djCommentsInk.reactions_handler).not.toBe(null);
    });

    it("has a div with [data-dci=config] with more data attributes", () => {
        const qs_config = "[data-dci=config]";
        const config_el = container.querySelector(qs_config);
        const react_url = config_el.getAttribute("data-react-url");
        const guest_user = config_el.getAttribute("data-guest-user");
        const page_qs_param = config_el.getAttribute("data-page-qs-param");
        const fold_qs_param = config_el.getAttribute("data-fold-qs-param");
        expect(config_el).not.toBe(null);
        expect(react_url).toBe("/comments/react/0/");
        expect(guest_user).toBe("0");
        expect(page_qs_param).toBe("cpage");
        expect(fold_qs_param).toBe("cfold");
    });

    it("opens/closes reactions panel by clicking on 'react' link", async() => {
        const anchor_qs = '[data-dci="reactions-panel"]';

        const comment_el = container.querySelector("#comment-29");
        expect(comment_el).not.toBe(null);

        const react_anchor_el = comment_el.querySelector(anchor_qs);
        expect(react_anchor_el).not.toBe(null);

        fireEvent.click(react_anchor_el);
        await waitFor(() => {
            const hdler = dom.window.djCommentsInk.reactions_handler;
            expect(hdler.active_visible_panel).toBe('29');
            expect(hdler.reactions_panel.comment_id).toBe('29');
            expect(hdler.reactions_panel.panel_el.style.opacity).toBe('1');
        });

        fireEvent.click(react_anchor_el);
        await waitFor(() => {
            const hdler = dom.window.djCommentsInk.reactions_handler;
            expect(hdler.active_visible_panel).toBe('0');
            expect(hdler.reactions_panel.comment_id).toBe('29');
            expect(hdler.reactions_panel.panel_el.style.opacity).toBe('0');
        });
    });

    it("clicks on the 'Like' and displays the 'Like'", async () => {
        const panel_qs = '[data-dci="reactions-panel-template"]';
        const anchor_qs = '[data-dci="reactions-panel"]';

        const comment_el = container.querySelector("#comment-29");
        expect(comment_el).not.toBe(null);

        const react_anchor_el = comment_el.querySelector(anchor_qs);
        expect(react_anchor_el).not.toBe(null);

        const reactions_panel_el = container.querySelector(panel_qs);
        expect(reactions_panel_el).not.toBe(null);

        // Click on the 'react' link to open the reactions panel.
        fireEvent.click(react_anchor_el);
        await waitFor(() => {
            const hdler = dom.window.djCommentsInk.reactions_handler;
            expect(hdler.active_visible_panel).toBe('29');
            expect(hdler.reactions_panel.comment_id).toBe('29');
            expect(hdler.reactions_panel.panel_el.style.opacity).toBe('1');
        });

        dom.window.fetch = jest.fn(() => Promise.resolve({
            status: 201,
            json: () => Promise.resolve({
                html: "<div class=\"active-reactions\"><div class=\"reaction\" data-reaction=\"+\"><span class=\"smaller\">1</span><span class=\"emoji\">&#128077;</span><div class=\"reaction_tooltip\">Daniela Rushmore reacted with Like</div></div></div>",
                reply_to: "0"
            })
        }));
        // Get the like button element, and click on it.
        const like_btn_qs = "button[data-code='+']";
        const like_btn_el = reactions_panel_el.querySelector(like_btn_qs);
        expect(like_btn_el).not.toBe(undefined);
        fireEvent.click(like_btn_el);

        const formData = new dom.window.FormData();
        formData.append("reaction", "+");
        formData.append("csrfmiddlewaretoken", null);

        await waitFor(() => {
            expect(dom.window.fetch.mock.calls.length).toEqual(1);
            expect(dom.window.fetch).toHaveBeenCalledWith(
                "/comments/react/29/",
                {
                    method: "POST",
                    cache: "no-cache",
                    credentials: "same-origin",
                    headers: {
                        "X-Requested-With": "XMLHttpRequest",
                    },
                    body: formData
                }
            );

            const feedback_qs = '#cm-feedback-29';
            const reaction_qs = '[data-reaction="+"]';

            // The feedback element does exist and has two direct children.
            const feedback_el = comment_el.querySelector(feedback_qs);
            expect(feedback_el).not.toBe(null);
            expect(feedback_el.children.length).toBe(2);

            // The like reaction element does exist too.
            const like_reaction_el = comment_el.querySelector(reaction_qs);
            expect(like_reaction_el).not.toBe(null);
            expect(like_reaction_el.children[0].textContent).toBe('1');
            expect(like_reaction_el.children[1].textContent).toBe('👍');
        });

        dom.window.fetch.mockClear();
    });

    it("clicks on the 'Like' to add and remove the 'Like'", async () => {
        const panel_qs = '[data-dci="reactions-panel-template"]';
        const anchor_qs = '[data-dci="reactions-panel"]';

        const comment_el = container.querySelector("#comment-29");
        expect(comment_el).not.toBe(null);

        const react_anchor_el = comment_el.querySelector(anchor_qs);
        expect(react_anchor_el).not.toBe(null);

        const reactions_panel_el = container.querySelector(panel_qs);
        expect(reactions_panel_el).not.toBe(null);

        // Click on the 'react' link to open the reactions panel.
        fireEvent.click(react_anchor_el);
        await waitFor(() => {
            const hdler = dom.window.djCommentsInk.reactions_handler;
            expect(hdler.active_visible_panel).toBe('29');
            expect(hdler.reactions_panel.comment_id).toBe('29');
            expect(hdler.reactions_panel.panel_el.style.opacity).toBe('1');
        });

        dom.window.fetch = jest.fn(() => {
            return Promise.resolve({
                status: 201,
                json: () => Promise.resolve({
                    html: "<div class=\"active-reactions\"><div class=\"reaction\" data-reaction=\"+\"><span class=\"smaller\">1</span><span class=\"emoji\">&#128077;</span><div class=\"reaction_tooltip\">Daniela Rushmore reacted with Like</div></div></div>",
                    reply_to: "0"
                })
            });
        });

        // Get the like button element, and click on it to add the Like.
        const like_btn_qs = "button[data-code='+']";
        const like_btn_el = reactions_panel_el.querySelector(like_btn_qs);
        expect(like_btn_el).not.toBe(undefined);
        expect(dom.window.fetch.mock.calls.length).toEqual(0);
        fireEvent.click(like_btn_el);

        const formData = new dom.window.FormData();
        formData.append("reaction", "+");
        formData.append("csrfmiddlewaretoken", null);

        await waitFor(() => {
            expect(dom.window.fetch.mock.calls.length).toEqual(1);
            expect(dom.window.fetch).toHaveBeenCalledWith(
                "/comments/react/29/",
                {
                    method: "POST",
                    cache: "no-cache",
                    credentials: "same-origin",
                    headers: {
                        "X-Requested-With": "XMLHttpRequest",
                    },
                    body: formData
                }
            );

            const reactions_qs = '#cm-reactions-29';
            const like_qs = '[data-reaction="+"]';

            // The feedback element does exist and has two direct children.
            const reactions_el = comment_el.querySelector(reactions_qs);
            expect(reactions_el).not.toBe(null);
            expect(reactions_el.children.length).toBe(1);

            // The like reaction element does exist too.
            const like_reaction_el = comment_el.querySelector(like_qs);
            expect(like_reaction_el).not.toBe(null);
            expect(like_reaction_el.children[0].textContent).toBe('1');
            expect(like_reaction_el.children[1].textContent).toBe('👍');
        });
        dom.window.fetch.mockClear();

        // --------------------------------------
        // Now test that clicking again on the
        // Like button removes the Like reaction.

        dom.window.fetch = jest.fn(() => {
            return Promise.resolve({
                status: 201,
                json: () => Promise.resolve({
                    html: "<div class=\"active-reactions\"><div class=\"reaction\" data-reaction=\"+\"></div></div>",
                    reply_to: "0"
                })
            });
        });

        // Click on the Like button.
        expect(like_btn_el).not.toBe(undefined);
        expect(dom.window.fetch.mock.calls.length).toEqual(0);
        fireEvent.click(like_btn_el);

        await waitFor(() => {
            expect(dom.window.fetch.mock.calls.length).toEqual(1);
            expect(dom.window.fetch).toHaveBeenCalledWith(
                "/comments/react/29/",
                {
                    method: "POST",
                    cache: "no-cache",
                    credentials: "same-origin",
                    headers: {
                        "X-Requested-With": "XMLHttpRequest",
                    },
                    body: formData
                }
            );

            const reactions_qs = '#cm-reactions-29';
            const like_qs = '[data-reaction="+"]';

            // The feedback element does exist and has only one direct child.
            const reactions_el = comment_el.querySelector(reactions_qs);
            expect(reactions_el).not.toBe(null);
            expect(reactions_el.children.length).toBe(1);

            // Every feedback element's text child node is empty. They would
            // contain &nbsp; to add padding when there are reactions. But
            // when the reactions are removed, the plugin shall remove the
            // explicit paddings too.
            for (const child of reactions_el.childNodes) {
                if (child.nodeType === Node.TEXT_NODE) {
                    expect(child.textContent === "");
                }
            }

            // The reaction data-code="+" does not exist.
            const like_reaction_el = comment_el.querySelector(like_qs);
            expect(like_reaction_el).not.toBe(null);
            expect(like_reaction_el.children.length).toBe(0);
        });
        dom.window.fetch.mockClear();
    });
});
