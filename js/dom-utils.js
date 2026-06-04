(function(global) {
    'use strict';

    function byId(id) {
        return document.getElementById(id);
    }

    function one(selector, root = document) {
        return root.querySelector(selector);
    }

    function all(selector, root = document) {
        return Array.from(root.querySelectorAll(selector));
    }

    function on(target, eventName, handler, options) {
        if (!target) return function noop() {};
        target.addEventListener(eventName, handler, options);
        return function off() {
            target.removeEventListener(eventName, handler, options);
        };
    }

    function setButtonDisclosure(button, options) {
        if (!button) return;

        const label = options.expanded ? options.expandedLabel : options.collapsedLabel;
        button.title = label;
        button.setAttribute('aria-label', label);
        button.setAttribute('aria-expanded', String(options.expanded));

        const icon = button.querySelector('i');
        const iconClass = options.expanded ? options.expandedIconClass : options.collapsedIconClass;
        if (icon && iconClass) {
            icon.className = iconClass;
        }
    }

    function removeModalBackdropsWhenIdle() {
        if (document.querySelectorAll('.modal.show').length > 0) {
            return false;
        }

        document.querySelectorAll('.modal-backdrop').forEach(backdrop => backdrop.remove());
        return true;
    }

    global.TRPG = global.TRPG || {};
    global.TRPG.dom = { byId, one, all, on, setButtonDisclosure, removeModalBackdropsWhenIdle };
    global.TrpgDom = global.TRPG.dom;
})(window);
