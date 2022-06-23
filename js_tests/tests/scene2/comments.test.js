import path from 'path';

import { getByText } from '@testing-library/dom';
import '@testing-library/jest-dom/extend-expect';
import { JSDOM, ResourceLoader } from 'jsdom';


const html_path = path.resolve(__dirname, './index.html');

let dom;
let container;
let qs_cform;

describe("scene 2 - comments.test.js module", () => {
    beforeEach(async () => {
        const resourceLoader = new ResourceLoader({
            proxy: "http://localhost:3000",
            strictSSL: false
        });
        const opts = { runScripts: "dangerously", resources: resourceLoader };
        dom = await JSDOM.fromFile(html_path, opts);
        await new Promise(resolve => {
            dom.window.addEventListener("DOMContentLoaded", () => {
                dom.window.djCommentsInk.init_comments();
                container = dom.window.document.body;
                qs_cform = "[data-dci=comment-form]";
                resolve();
            });
        });
    });

    it("makes window.djCommentsInk.comment_form attribute !== null", () => {
        expect(
            dom.window.djCommentsInk !== null &&
            dom.window.djCommentsInk !== undefined
        );
        expect(dom.window.djCommentsInk.comment_form !== null);
    });

    it("has a div with [data-dci=comment-form]", () => {
        expect(container.querySelector(qs_cform));
        expect(getByText(container, 'Post your comment')).toBeInTheDocument();
    });

    it("has a div with [data-dci=reply-form-template]", () => {
        const qs_rform_template = "[data-dci=reply-form-template]";
        expect(container.querySelector(qs_rform_template));
    });

    it("has a div with [data-dci=reply-form]", () => {
        const qs_rform = "[data-dci=reply-form]";
        expect(container.querySelector(qs_rform));
    });

    it("creates djCommentsInk.reply_forms_handler attribute !== null", () => {
        expect(
            dom.window.djCommentsInk !== null &&
            dom.window.djCommentsInk !== undefined
        );
        expect(dom.window.djCommentsInk.comment_form !== null);
    });
});
