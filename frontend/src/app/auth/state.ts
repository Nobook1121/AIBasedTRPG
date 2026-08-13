interface Window {
    currentUser: AuthModule.CurrentUser | null;
    initAuth: () => Promise<boolean>;
    reconnectSocket?: () => void;
    disconnectSocket?: () => void;
    clearCurrentRoom?: () => void;
    clearChatMessages?: () => void;
    autoLoadLastRoom?: () => Promise<void>;
    setCurrentEditingScenarioId?: (id: string | number | null) => void;
}

namespace AuthModule {
    export interface CurrentUser {
        user_id: number;
        username: string;
        role: string;
        email?: string;
        avatar?: string;
        nickname?: string;
        presence?: "online" | "dnd" | "invisible";
        two_factor_enabled?: boolean;
    }

    export let currentEditingScenarioId: string | number | null = null;

    export function setCurrentEditingScenarioId(id: string | number | null): void {
        currentEditingScenarioId = id;
    }

    export function setCurrentUser(user: CurrentUser | null): void {
        window.currentUser = user;
        const name = document.getElementById("userName");
        const avatar = document.querySelector<HTMLImageElement>(".user-avatar img");
        const cardName = document.getElementById("userCardName");
        const cardRole = document.getElementById("userCardRole");
        const cardAvatar = document.getElementById("userCardAvatar") as HTMLImageElement | null;
        const presenceButtonLabel = document.querySelector<HTMLElement>("#presence-menu-button .presence-current-label");
        if (user) {
            if (name) name.textContent = user.username;
            if (avatar) avatar.src = user.avatar || "/assets/avatars/default.jpg";
            if (cardName) cardName.textContent = user.username;
            if (cardRole) cardRole.textContent = user.role || "USER";
            if (cardAvatar) cardAvatar.src = user.avatar || "/assets/avatars/default.jpg";
            if (presenceButtonLabel) presenceButtonLabel.textContent = presenceLabel(user.presence || "online");
        } else {
            if (name) name.textContent = "未登录";
            if (avatar) avatar.src = "/assets/avatars/default.jpg";
            if (cardName) cardName.textContent = "未登录";
            if (cardRole) cardRole.textContent = "USER";
            if (cardAvatar) cardAvatar.src = "/assets/avatars/default.jpg";
            if (presenceButtonLabel) presenceButtonLabel.textContent = "在线状态";
        }
    }

    function presenceLabel(presence: CurrentUser["presence"]): string {
        switch (presence) {
            case "dnd":
                return "请勿打扰";
            case "invisible":
                return "隐身";
            default:
                return "在线";
        }
    }

    export function showAuthModal(): void {
        const modal = document.getElementById("auth-modal");
        if (modal) modal.style.display = "flex";
    }

    export function closeAuthModal(): void {
        const modal = document.getElementById("auth-modal");
        if (modal) modal.style.display = "none";
    }

    export function showMessage(elementId: string, message: string, isError = false): void {
        const element = document.getElementById(elementId);
        if (!element) return;
        element.textContent = message;
        element.style.color = isError ? "red" : "green";
    }
}
