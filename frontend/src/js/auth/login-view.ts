namespace AuthModule {
    export function showLoginView(): void {
        document.getElementById("login-view")?.classList.add("active");
        document.getElementById("register-view")?.classList.remove("active");
        const title = document.querySelector<HTMLHeadingElement>(".auth-modal-header h2");
        if (title) title.textContent = "登录";
    }

    export function prefillRememberedUsername(): void {
        const rememberedUsername = TrpgCookies.get("trpg_last_username");
        const loginUsername = document.getElementById("loginUsername") as HTMLInputElement | null;
        if (rememberedUsername && loginUsername) {
            loginUsername.value = rememberedUsername;
        }
    }

    export async function checkAuthStatus(): Promise<boolean> {
        try {
            const response = await TrpgApi.get<ApiResponse<CurrentUser>>("/api/auth/status");
            if (response.success && response.data) {
                setCurrentUser(response.data);
                closeAuthModal();
                return true;
            }
        } catch (error) {
            console.debug("未登录或会话已失效", error);
        }
        setCurrentUser(null);
        showAuthModal();
        return false;
    }

    export async function login(): Promise<void> {
        const identifier = (document.getElementById("loginUsername") as HTMLInputElement | null)?.value.trim() || "";
        const password = (document.getElementById("loginPassword") as HTMLInputElement | null)?.value || "";
        const rememberMe = (document.getElementById("rememberMe") as HTMLInputElement | null)?.checked || false;
        const stayLoggedIn = (document.getElementById("stayLoggedIn") as HTMLInputElement | null)?.checked || false;
        const autoLogin = (document.getElementById("autoLogin") as HTMLInputElement | null)?.checked || false;
        if (!identifier || !password) {
            showMessage("loginMessage", "请输入用户名或邮箱和密码", true);
            return;
        }
        try {
            const response = await TrpgApi.post<ApiResponse<CurrentUser>>("/api/auth/login", {
                identifier,
                password,
                remember_me: rememberMe,
                stay_logged_in: stayLoggedIn,
                auto_login: autoLogin,
            });
            if (!response.success || !response.data) {
                showMessage("loginMessage", localizedAuthMessage(response, "登录失败"), true);
                return;
            }
            setCurrentUser(response.data);
            closeAuthModal();
            TrpgCookies.set("trpg_last_username", response.data.username);
            window.reconnectSocket?.();
            window.clearCurrentRoom?.();
            window.clearChatMessages?.();
            await window.autoLoadLastRoom?.();
        } catch (error) {
            console.error("登录失败:", error);
            showMessage("loginMessage", "登录失败，请稍后重试", true);
        }
    }
}
