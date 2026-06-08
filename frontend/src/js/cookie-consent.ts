// @ts-nocheck
// Optional preference-cookie consent and small cookie helpers.

(function initCookieConsent(global) {
    const CONSENT_COOKIE = 'trpg_cookie_consent';
    const MAX_AGE_DAYS = 180;

    function get(name) {
        const prefix = `${encodeURIComponent(name)}=`;
        const item = document.cookie
            .split(';')
            .map(part => part.trim())
            .find(part => part.startsWith(prefix));
        if (!item) return '';
        return decodeURIComponent(item.slice(prefix.length));
    }

    function set(name, value, days = MAX_AGE_DAYS) {
        if (!hasConsent() && name !== CONSENT_COOKIE) return;
        const maxAge = Math.max(1, days) * 24 * 60 * 60;
        document.cookie = `${encodeURIComponent(name)}=${encodeURIComponent(value || '')}; Max-Age=${maxAge}; Path=/; SameSite=Lax`;
    }

    function remove(name) {
        document.cookie = `${encodeURIComponent(name)}=; Max-Age=0; Path=/; SameSite=Lax`;
    }

    function hasConsent() {
        return get(CONSENT_COOKIE) === 'accepted';
    }

    function hasAnswered() {
        return ['accepted', 'declined'].includes(get(CONSENT_COOKIE));
    }

    function showCookieConsentBanner() {
        if (hasAnswered() || document.getElementById('cookieConsentBanner')) return;

        const banner = document.createElement('div');
        banner.id = 'cookieConsentBanner';
        banner.className = 'cookie-consent-banner';
        banner.innerHTML = `
            <div class="cookie-consent-text">
                本应用使用必要登录 Cookie 保持会话；可选 Cookie 用于记住上次用户名和房间偏好。
            </div>
            <div class="cookie-consent-actions">
                <button type="button" class="btn btn-sm btn-outline-secondary" id="declineCookieConsent">仅必要 Cookie</button>
                <button type="button" class="btn btn-sm btn-primary" id="acceptCookieConsent">同意</button>
            </div>
        `;
        document.body.appendChild(banner);

        document.getElementById('acceptCookieConsent').addEventListener('click', function() {
            set(CONSENT_COOKIE, 'accepted');
            banner.remove();
        });
        document.getElementById('declineCookieConsent').addEventListener('click', function() {
            document.cookie = `${CONSENT_COOKIE}=declined; Max-Age=${MAX_AGE_DAYS * 24 * 60 * 60}; Path=/; SameSite=Lax`;
            banner.remove();
        });
    }

    global.TrpgCookies = {
        get,
        set,
        remove,
        hasConsent,
        showCookieConsentBanner,
    };
    window.TrpgCookies = global.TrpgCookies;

    document.addEventListener('DOMContentLoaded', showCookieConsentBanner);
})(window);
