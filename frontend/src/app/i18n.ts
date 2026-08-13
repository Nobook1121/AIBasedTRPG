interface Window {
    TrpgI18n?: {
        t: (key: string, fallback?: string) => string;
        apply: (root?: ParentNode) => void;
    };
}

(function initializeI18n(global: Window): void {
    const zhCN: Record<string, string> = {
        "app.title": "AI TRPG",
        "auth.login.title": "登录",
        "auth.status.guest": "未登录",
        "chat.action.send": "发送",
        "chat.placeholder.room_required": "加入房间后可发送消息，使用 @KP 呼叫 AI",
        "room.status.current_room": "当前房间",
        "room.status.scenario": "剧本",
    };

    function t(key: string, fallback = ""): string {
        return zhCN[key] || fallback || key;
    }

    function apply(root: ParentNode = document): void {
        root.querySelectorAll<HTMLElement>("[data-i18n]").forEach((element) => {
            element.textContent = t(element.dataset.i18n || "", element.textContent || "");
        });
        root.querySelectorAll<HTMLInputElement | HTMLTextAreaElement>("[data-i18n-placeholder]").forEach((element) => {
            element.placeholder = t(element.dataset.i18nPlaceholder || "", element.placeholder || "");
        });
    }

    global.TrpgI18n = { t, apply };
})(window);
