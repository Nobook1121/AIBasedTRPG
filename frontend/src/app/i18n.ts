interface TranslationCatalog {
    locale?: string;
    translations?: Record<string, string>;
    legacy?: Record<string, string>;
    patterns?: Array<{ pattern: string; replace: string }>;
}

interface I18nRuntime {
    t: (key: string, fallback?: string, values?: Record<string, string | number>) => string;
    apply: (root?: ParentNode) => void;
    setLocale: (locale: string) => Promise<void>;
    getLocale: () => string;
    ready: Promise<void>;
}

interface Window {
    TrpgI18n?: I18nRuntime;
}

(function initializeI18n(global: Window): void {
    const FALLBACK_LOCALE = "zh_cn";
    const LOCALE_STORAGE_KEY = "trpg_locale";
    const catalogs = new Map<string, TranslationCatalog>();
    const sourceText = new WeakMap<Text, string>();
    const sourceAttributes = new WeakMap<Element, Record<string, string>>();
    function readStoredLocale(): string {
        try {
            return localStorage.getItem(LOCALE_STORAGE_KEY) || "zh_cn";
        } catch {
            return "zh_cn";
        }
    }

    let activeLocale = normalizeLocale(readStoredLocale());

    function normalizeLocale(locale: string): string {
        const normalized = locale.replace("-", "_").toLowerCase();
        return normalized === "zh" || normalized === "zh_cn" ? "zh_cn" : "en_us";
    }

    async function loadCatalog(locale: string): Promise<TranslationCatalog> {
        const cached = catalogs.get(locale);
        if (cached) return cached;
        const response = await fetch(`/locales/${locale}.json`, { cache: "no-store" });
        if (!response.ok) throw new Error(`Unable to load locale catalog: ${locale}`);
        const catalog = await response.json() as TranslationCatalog;
        catalogs.set(locale, catalog);
        return catalog;
    }

    function replaceValues(value: string, values: Record<string, string | number> = {}): string {
        return value.replace(/\{([\w.-]+)\}/g, (_, name: string) => String(values[name] ?? `{${name}}`));
    }

    function lookup(key: string, fallback: string): string {
        const active = catalogs.get(activeLocale);
        const base = catalogs.get(FALLBACK_LOCALE);
        return active?.translations?.[key]
            || base?.translations?.[key]
            || active?.legacy?.[fallback]
            || base?.legacy?.[fallback]
            || fallback
            || key;
    }

    function translateLegacy(value: string): string {
        const active = catalogs.get(activeLocale);
        const direct = active?.legacy?.[value];
        if (direct) return direct;
        for (const item of active?.patterns || []) {
            const match = value.match(new RegExp(item.pattern));
            if (match) return item.replace.replace(/\{(\d+)\}/g, (_, index: string) => match[Number(index)] || "");
        }
        return value;
    }

    function t(key: string, fallback = "", values: Record<string, string | number> = {}): string {
        return replaceValues(lookup(key, fallback), values);
    }

    function translateElement(element: Element): void {
        const htmlElement = element as HTMLElement;
        const attributes = sourceAttributes.get(element) || {};
        if (htmlElement.dataset.i18n) {
            if (!attributes.i18n) attributes.i18n = htmlElement.textContent || "";
            sourceAttributes.set(element, attributes);
            htmlElement.textContent = t(htmlElement.dataset.i18n, attributes.i18n);
        }
        const input = element as HTMLInputElement | HTMLTextAreaElement;
        if (input.dataset.i18nPlaceholder) {
            if (!attributes.placeholder) attributes.placeholder = input.placeholder || "";
            sourceAttributes.set(element, attributes);
            input.placeholder = t(input.dataset.i18nPlaceholder, attributes.placeholder);
        } else if (input.placeholder) {
            if (!attributes.placeholder) attributes.placeholder = input.placeholder;
            sourceAttributes.set(element, attributes);
            input.placeholder = translateLegacy(attributes.placeholder);
        }
        if (htmlElement.dataset.i18nTitle) {
            if (!attributes.title) attributes.title = htmlElement.title || "";
            sourceAttributes.set(element, attributes);
            htmlElement.title = t(htmlElement.dataset.i18nTitle, attributes.title);
        } else if (htmlElement.title) {
            if (!attributes.title) attributes.title = htmlElement.title;
            sourceAttributes.set(element, attributes);
            htmlElement.title = translateLegacy(attributes.title);
        }
        if (htmlElement.dataset.i18nAriaLabel) {
            if (!attributes.ariaLabel) attributes.ariaLabel = htmlElement.getAttribute("aria-label") || "";
            sourceAttributes.set(element, attributes);
            htmlElement.setAttribute("aria-label", t(htmlElement.dataset.i18nAriaLabel, attributes.ariaLabel));
        } else if (htmlElement.getAttribute("aria-label")) {
            if (!attributes.ariaLabel) attributes.ariaLabel = htmlElement.getAttribute("aria-label") || "";
            sourceAttributes.set(element, attributes);
            htmlElement.setAttribute("aria-label", translateLegacy(attributes.ariaLabel));
        }
        const image = element as HTMLImageElement;
        if (image.dataset.i18nAlt) {
            if (!attributes.alt) attributes.alt = image.alt || "";
            sourceAttributes.set(element, attributes);
            image.alt = t(image.dataset.i18nAlt, attributes.alt);
        } else if (image.alt) {
            if (!attributes.alt) attributes.alt = image.alt;
            sourceAttributes.set(element, attributes);
            image.alt = translateLegacy(attributes.alt);
        }
    }

    function applyLegacyText(root: ParentNode): void {
        const walker = document.createTreeWalker(root, NodeFilter.SHOW_TEXT);
        const textNodes: Text[] = [];
        let current: Node | null;
        while ((current = walker.nextNode())) textNodes.push(current as Text);
        textNodes.forEach((node) => {
            const parent = node.parentElement;
            if (!parent || ["SCRIPT", "STYLE", "TEXTAREA", "INPUT"].includes(parent.tagName)) return;
            if (parent.closest("[data-user-content], [data-i18n-dynamic]")) return;
            const source = sourceText.get(node) || node.nodeValue || "";
            sourceText.set(node, source);
            const trimmed = source.trim();
            if (!trimmed) return;
            const translated = translateLegacy(trimmed);
            if (translated !== trimmed) {
                const current = node.nodeValue || "";
                const start = current.indexOf(current.trim());
                node.nodeValue = `${current.slice(0, Math.max(0, start))}${translated}${current.slice(Math.max(0, start) + current.trim().length)}`;
            } else if (node.nodeValue !== source) {
                const current = node.nodeValue || "";
                const start = current.indexOf(current.trim());
                node.nodeValue = `${current.slice(0, Math.max(0, start))}${source}${current.slice(Math.max(0, start) + current.trim().length)}`;
            }
        });
    }

    function apply(root: ParentNode = document): void {
        if (root instanceof Element) translateElement(root);
        root.querySelectorAll<HTMLElement>("[data-i18n], [data-i18n-placeholder], [data-i18n-title], [data-i18n-aria-label], [data-i18n-alt], input, textarea, select, option, button, img").forEach(translateElement);
        applyLegacyText(root);
    }

    async function setLocale(locale: string): Promise<void> {
        const nextLocale = normalizeLocale(locale);
        await loadCatalog(nextLocale);
        activeLocale = nextLocale;
        try {
            localStorage.setItem(LOCALE_STORAGE_KEY, nextLocale);
        } catch {
            // Locale switching still works when storage is unavailable.
        }
        document.documentElement.lang = nextLocale === "en_us" ? "en-US" : "zh-CN";
        const select = document.getElementById("languageSelect") as HTMLSelectElement | null;
        if (select) select.value = nextLocale === "en_us" ? "en-US" : "zh-CN";
        apply();
        global.dispatchEvent(new CustomEvent("trpg:locale-changed", { detail: nextLocale }));
    }

    function bindLanguageSelector(): void {
        const select = document.getElementById("languageSelect") as HTMLSelectElement | null;
        if (!select || select.dataset.i18nBound === "true") return;
        select.dataset.i18nBound = "true";
        select.value = activeLocale === "en_us" ? "en-US" : "zh-CN";
        select.addEventListener("change", () => void setLocale(select.value));
    }

    const ready = (async () => {
        try {
            await loadCatalog(FALLBACK_LOCALE);
            await loadCatalog(activeLocale);
        } catch (error) {
            console.error("Failed to load localization catalogs", error);
        }
        document.documentElement.lang = activeLocale === "en_us" ? "en-US" : "zh-CN";
        bindLanguageSelector();
        apply();
        const observer = new MutationObserver((records) => {
            records.forEach((record) => {
                record.addedNodes.forEach((node) => {
                    if (node.nodeType === Node.ELEMENT_NODE) apply(node as Element);
                });
            });
        });
        if (document.body) observer.observe(document.body, { childList: true, subtree: true });
    })();

    global.TrpgI18n = { t, apply, setLocale, getLocale: () => activeLocale, ready };
})(window);
