(function initializeDomUtils(global: Window): void {
    "use strict";

    function byId<T extends HTMLElement = HTMLElement>(id: string): T | null {
        return document.getElementById(id) as T | null;
    }

    function one<T extends Element = Element>(selector: string, root: ParentNode = document): T | null {
        return root.querySelector(selector) as T | null;
    }

    function all<T extends Element = Element>(selector: string, root: ParentNode = document): T[] {
        return Array.from(root.querySelectorAll(selector)) as T[];
    }

    function on(
        target: Document | HTMLElement | null,
        eventName: string,
        handler: EventListener,
        options?: boolean | AddEventListenerOptions,
    ): () => void {
        if (!target) return function noop(): void {};
        target.addEventListener(eventName, handler, options);
        return function off(): void {
            target.removeEventListener(eventName, handler, options);
        };
    }

    function setButtonDisclosure(button: HTMLElement | null, options: ButtonDisclosureOptions): void {
        if (!button) return;

        const label = options.expanded ? options.expandedLabel : options.collapsedLabel;
        button.title = label;
        button.setAttribute("aria-label", label);
        button.setAttribute("aria-expanded", String(options.expanded));

        const icon = button.querySelector("i");
        const iconClass = options.expanded ? options.expandedIconClass : options.collapsedIconClass;
        if (icon && iconClass) {
            icon.className = iconClass;
        }
    }

    function removeModalBackdropsWhenIdle(): boolean {
        if (document.querySelectorAll(".modal.show").length > 0) {
            return false;
        }

        document.querySelectorAll(".modal-backdrop").forEach((backdrop) => backdrop.remove());
        return true;
    }

    global.TRPG = global.TRPG || {};
    global.TRPG.dom = { byId, one, all, on, setButtonDisclosure, removeModalBackdropsWhenIdle };
    global.TrpgDom = global.TRPG.dom;
})(window);
