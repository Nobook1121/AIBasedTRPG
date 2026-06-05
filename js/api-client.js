(function(global) {
    'use strict';

    async function parseJson(response) {
        const text = await response.text();
        return text ? JSON.parse(text) : null;
    }

    function buildOptions(options) {
        const requestOptions = { ...options };
        const hasBody = Object.prototype.hasOwnProperty.call(requestOptions, 'body');
        const isFormData = typeof FormData !== 'undefined' && requestOptions.body instanceof FormData;

        if (hasBody && requestOptions.body !== null && typeof requestOptions.body === 'object' && !isFormData) {
            requestOptions.body = JSON.stringify(requestOptions.body);
            requestOptions.headers = {
                'Content-Type': 'application/json',
                ...(requestOptions.headers || {})
            };
        }

        return requestOptions;
    }

    async function request(url, options = {}) {
        const response = await fetch(url, buildOptions(options));
        return parseJson(response);
    }

    async function requestWithResponse(url, options = {}) {
        const response = await fetch(url, buildOptions(options));
        const data = await parseJson(response);
        return { response, data };
    }

    function get(url, options = {}) {
        return request(url, { ...options, method: options.method || 'GET' });
    }

    function post(url, body, options = {}) {
        return request(url, { ...options, method: 'POST', body });
    }

    function put(url, body, options = {}) {
        return request(url, { ...options, method: 'PUT', body });
    }

    function del(url, options = {}) {
        return request(url, { ...options, method: options.method || 'DELETE' });
    }

    global.TRPG = global.TRPG || {};
    global.TRPG.api = { request, requestWithResponse, get, post, put, del };
    global.TrpgApi = global.TRPG.api;
})(window);
