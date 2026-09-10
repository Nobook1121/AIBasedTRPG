namespace AuthModule {
    export function toggleUserCard(): void {
        if (!window.currentUser) {
            showLoginView();
            showAuthModal();
            return;
        }
        const popover = document.getElementById("user-card-popover");
        if (!popover) return;
        popover.classList.toggle("open");
        popover.setAttribute("aria-hidden", popover.classList.contains("open") ? "false" : "true");
    }

    export function closeUserCard(): void {
        const popover = document.getElementById("user-card-popover");
        popover?.classList.remove("open");
        popover?.setAttribute("aria-hidden", "true");
    }

    export function closeUserCardOnOutsideClick(): void {
        document.addEventListener("click", (event) => {
            const target = event.target as Node | null;
            const popover = document.getElementById("user-card-popover");
            const trigger = document.getElementById("userInfo");
            if (!target || !popover?.classList.contains("open")) return;
            if (popover.contains(target) || trigger?.contains(target)) return;
            closeUserCard();
        });
    }

    export async function logout(): Promise<void> {
        try {
            await TrpgApi.post<ApiResponse>("/api/auth/logout");
        } catch (error) {
            console.error("登出失败:", error);
        }
        window.disconnectSocket?.();
        window.clearCurrentRoom?.();
        window.clearChatMessages?.();
        window.clearCharacterManagement?.();
        setCurrentUser(null);
        closeUserCard();
        closeProfileDialog();
        closePasswordDialog();
        showLoginView();
        showAuthModal();
    }

    export async function switchAccount(): Promise<void> {
        await logout();
    }

    export async function stopImpersonation(): Promise<void> {
        try {
            await TrpgApi.post<ApiResponse>("/api/auth/impersonation/stop");
            window.location.reload();
        } catch (error) {
            console.error("退出模拟失败:", error);
            showNotification("退出模拟失败", "error");
        }
    }
}
