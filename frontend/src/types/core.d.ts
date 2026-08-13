type JsonPrimitive = string | number | boolean | null;
type JsonObject = { [key: string]: JsonValue };
type JsonArray = JsonValue[];
type JsonValue = JsonPrimitive | JsonObject | JsonArray;
type RequestBody = BodyInit | JsonValue | object | null;

interface TrpgRequestOptions extends Omit<RequestInit, "body"> {
    body?: RequestBody;
    method?: string;
    timeout?: number;
}

interface TrpgResponse<T = unknown> {
    response: Response;
    data: T;
}

interface ApiResponse<T = unknown> {
    success: boolean;
    message?: string;
    error?: string;
    data?: T;
}

interface TrpgApiClient {
    request<T = unknown>(url: string, options?: TrpgRequestOptions): Promise<T>;
    requestWithResponse<T = unknown>(url: string, options?: TrpgRequestOptions): Promise<TrpgResponse<T>>;
    get<T = unknown>(url: string, options?: TrpgRequestOptions): Promise<T>;
    post<T = unknown>(url: string, body?: RequestBody, options?: TrpgRequestOptions): Promise<T>;
    put<T = unknown>(url: string, body?: RequestBody, options?: TrpgRequestOptions): Promise<T>;
    del<T = unknown>(url: string, options?: TrpgRequestOptions): Promise<T>;
}

interface TrpgDomClient {
    byId<T extends HTMLElement = HTMLElement>(id: string): T | null;
    one<T extends Element = Element>(selector: string, root?: ParentNode): T | null;
    all<T extends Element = Element>(selector: string, root?: ParentNode): T[];
    on(
        target: EventTarget | null,
        eventName: string,
        handler: EventListenerOrEventListenerObject,
        options?: boolean | AddEventListenerOptions,
    ): () => void;
    setButtonDisclosure(button: HTMLElement | null, options: ButtonDisclosureOptions): void;
    removeModalBackdropsWhenIdle(): boolean;
}

interface ButtonDisclosureOptions {
    expanded: boolean;
    expandedLabel: string;
    collapsedLabel: string;
    expandedIconClass?: string;
    collapsedIconClass?: string;
}

interface TrpgNamespace {
    api?: TrpgApiClient;
    dom?: TrpgDomClient;
}

interface TrpgCookieClient {
    get(name: string): string;
    set(name: string, value: string, days?: number): void;
    remove(name: string): void;
    hasConsent(): boolean;
    showCookieConsentBanner(): void;
}
