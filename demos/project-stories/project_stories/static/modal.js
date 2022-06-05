const init_modals = function() {
    const settings = {
        speedOpen: 50,
        speedClose: 250,
        activeClass: 'is-active',
        visibleClass: 'is-visible',
        selectorTarget: '[data-modal-target]',
        selectorReload: '[data-modal-reload]',
        selectorTrigger: '[data-modal-trigger]',
        selectorClose: '[data-modal-close]',
    };

    const toggleccessibility = function(event) {
        if (event.getAttribute('aria-expanded') === 'true') {
            event.setAttribute('aria-expanded', false);
        } else {
            event.setAttribute('aria-expanded', true);
        }
    };

    const openModal = function(trigger) {
        const controls = trigger.getAttribute('aria-controls');
        const target = document.getElementById(controls);
        target.classList.add(settings.activeClass);
        document.documentElement.style.overflow = 'hidden';
        toggleccessibility(trigger);
        setTimeout(
            () => target.classList.add(settings.visibleClass),
            settings.speedOpen
        );
    };

    const closeModal = function(event) {
        const closestParent = event.closest(settings.selectorTarget);
        const controls = '[aria-controls="' + closestParent.id + '"]';
        const childrenTrigger = document.querySelector(controls);
        closestParent.classList.remove(settings.visibleClass);
        document.documentElement.style.overflow = '';
        toggleccessibility(childrenTrigger);
        setTimeout(
            () => closestParent.classList.remove(settings.activeClass),
            settings.speedClose
        );
    };

    const addModalListeners = function() {
        document.querySelectorAll(settings.selectorClose).forEach(
            elem => elem.addEventListener('click', clickHandler, false)
        );
        const pagLinks = document.querySelectorAll(settings.selectorReload);
        pagLinks.forEach(
            elem => elem.addEventListener('click', reloadContent, false)
        );
    };

    const reloadContent = async function(event) {
        const target = event.target;
        await loadContent(target);
    };

    const loadContent = async function(trigger) {
        const controls = trigger.getAttribute('aria-controls');
        const target = document.getElementById(controls);
        const response = await fetch(trigger.dataset.href, {method: 'GET'});
        if (response.status === 200) {
            const data = await response.text();
            const body = target && target.querySelector(".modal__wrapper");
            if (body) {
                body.innerHTML = data;
                addModalListeners();
            }
        }
    };

    const clickHandler = async function(event) {
        const toggle = event.target;
        const open = toggle.closest(settings.selectorTrigger);
        const close = toggle.closest(settings.selectorClose);

        if (open) { // Open modal when the open button is clicked.
            await loadContent(open);
            openModal(open);
        }

        if (close) { // Close modal when the close button is clicked.
            closeModal(close);
        }

        if (open || close) { // Prevent default link behavior.
            event.preventDefault();
        }
    };

    // Keydown Handler, handle Escape button
    const keydownHandler = function(event) {
        if (event.key === 'Escape' || event.keyCode === 27) {
            const mWins = document.querySelectorAll(settings.selectorTarget);
            for (let i = 0; i < mWins.length; ++i) {
                if (mWins[i].classList.contains(settings.activeClass)) {
                    closeModal(mWins[i]);
                }
            }
        }
    };

    document.querySelectorAll(settings.selectorTrigger).forEach(
        elem => elem.addEventListener('click', clickHandler, false)
    );
    document.addEventListener('keydown', keydownHandler, false);
};

window.addEventListener("DOMContentLoaded", (_) => {
    init_modals();
});
