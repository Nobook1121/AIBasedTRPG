type JsonValue =
    | string
    | number
    | boolean
    | null
    | JsonValue[]
    | { [key: string]: JsonValue };

type RequestBody = BodyInit | JsonValue | Record<string, unknown> | null;

interface TrpgRequestOptions extends Omit<RequestInit, "body"> {
    body?: RequestBody;
    method?: string;
}

interface TrpgResponse<T = unknown> {
    response: Response;
    data: T;
}

interface TrpgApiClient {
    request<T = unknown>(url: string, options?: TrpgRequestOptions): Promise<T>;
    requestWithResponse<T = unknown>(url: string, options?: TrpgRequestOptions): Promise<TrpgResponse<T>>;
    get<T = unknown>(url: string, options?: TrpgRequestOptions): Promise<T>;
    post<T = unknown>(url: string, body?: RequestBody, options?: TrpgRequestOptions): Promise<T>;
    put<T = unknown>(url: string, body?: RequestBody, options?: TrpgRequestOptions): Promise<T>;
    del<T = unknown>(url: string, options?: TrpgRequestOptions): Promise<T>;
}

interface Window {
    TRPG?: {
        api?: TrpgApiClient;
    };
    TrpgApi?: TrpgApiClient;
}

(function initializeApiClient(global: Window) {
    "use strict";

    async function parseJson<T = unknown>(response: Response): Promise<T | null> {
        const text = await response.text();
        return text ? JSON.parse(text) as T : null;
    }

    function buildOptions(options: TrpgRequestOptions): RequestInit {
        const requestOptions: TrpgRequestOptions = { ...options };
        const hasBody = Object.prototype.hasOwnProperty.call(requestOptions, "body");
        const isFormData = typeof FormData !== "undefined" && requestOptions.body instanceof FormData;

        if (hasBody && requestOptions.body !== null && typeof requestOptions.body === "object" && !isFormData) {
            requestOptions.body = JSON.stringify(requestOptions.body);
            requestOptions.headers = {
                "Content-Type": "application/json",
                ...(requestOptions.headers || {}),
            };
        }

        return requestOptions as RequestInit;
    }

    async function request<T = unknown>(url: string, options: TrpgRequestOptions = {}): Promise<T> {
        const response = await fetch(url, buildOptions(options));
        return parseJson<T>(response) as Promise<T>;
    }

    async function requestWithResponse<T = unknown>(
        url: string,
        options: TrpgRequestOptions = {},
    ): Promise<TrpgResponse<T>> {
        const response = await fetch(url, buildOptions(options));
        const data = await parseJson<T>(response);
        return { response, data: data as T };
    }

    function get<T = unknown>(url: string, options: TrpgRequestOptions = {}): Promise<T> {
        return request<T>(url, { ...options, method: options.method || "GET" });
    }

    function post<T = unknown>(
        url: string,
        body: RequestBody = null,
        options: TrpgRequestOptions = {},
    ): Promise<T> {
        return request<T>(url, { ...options, method: "POST", body });
    }

    function put<T = unknown>(
        url: string,
        body: RequestBody = null,
        options: TrpgRequestOptions = {},
    ): Promise<T> {
        return request<T>(url, { ...options, method: "PUT", body });
    }

    function del<T = unknown>(url: string, options: TrpgRequestOptions = {}): Promise<T> {
        return request<T>(url, { ...options, method: options.method || "DELETE" });
    }

    global.TRPG = global.TRPG || {};
    global.TRPG.api = { request, requestWithResponse, get, post, put, del };
    global.TrpgApi = global.TRPG.api;
})(window);
