(function initializeApiClient(global: Window) {
    "use strict";

    async function parseJson<T = unknown>(response: Response): Promise<T | null> {
        const text = await response.text();
        if (!text.trim()) return null;
        try {
            return JSON.parse(text) as T;
        } catch {
            const contentType = response.headers.get("content-type") || "";
            const hint = contentType.includes("text/html")
                ? "服务器返回了网页而不是 JSON（可能是登录失效或接口地址错误）"
                : `服务器返回了无效 JSON（HTTP ${response.status}）`;
            return { success: false, message: hint, error: `HTTP ${response.status}` } as T;
        }
    }

    function buildOptions(options: TrpgRequestOptions): RequestInit {
        const requestOptions: TrpgRequestOptions = { ...options };
        const method = String(requestOptions.method || "GET").toUpperCase();
        const hasBody = Object.prototype.hasOwnProperty.call(requestOptions, "body");
        const isFormData = typeof FormData !== "undefined" && requestOptions.body instanceof FormData;
        const csrfToken = window.currentUser?.csrf_token;

        if (hasBody && requestOptions.body !== null && typeof requestOptions.body === "object" && !isFormData) {
            requestOptions.body = JSON.stringify(requestOptions.body);
            requestOptions.headers = {
                "Content-Type": "application/json",
                ...(requestOptions.headers || {}),
            };
        }

        // Every API request explicitly asks for JSON.  This keeps proxy/router
        // fallbacks from returning the SPA HTML shell, while leaving FormData's
        // Content-Type boundary to the browser.
        requestOptions.headers = {
            Accept: "application/json",
            ...(requestOptions.headers || {}),
        };

        if (csrfToken && ["POST", "PUT", "PATCH", "DELETE"].includes(method)) {
            requestOptions.headers = {
                ...(requestOptions.headers || {}),
                "X-CSRF-Token": csrfToken,
            };
        }

        if (method === "GET") {
            requestOptions.cache = "no-store";
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
