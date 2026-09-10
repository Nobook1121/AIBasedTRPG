namespace AuthModule {
    export function showRegisterView(): void {
        document.getElementById("register-view")?.classList.add("active");
        document.getElementById("login-view")?.classList.remove("active");
        const title = document.querySelector<HTMLHeadingElement>(".auth-modal-header h2");
        if (title) title.textContent = authText("auth.register.title", "注册");
    }

    export async function register(): Promise<void> {
        const username = (document.getElementById("registerUsername") as HTMLInputElement | null)?.value.trim() || "";
        const email = (document.getElementById("registerEmail") as HTMLInputElement | null)?.value.trim() || "";
        const password = (document.getElementById("registerPassword") as HTMLInputElement | null)?.value || "";
        const confirmPassword = (document.getElementById("registerConfirmPassword") as HTMLInputElement | null)?.value || "";
        const termsAccepted = (document.getElementById("acceptTerms") as HTMLInputElement | null)?.checked || false;
        if (!username || !email || !password || !confirmPassword) {
            showMessage("registerMessage", authText("auth.error.incomplete_data", "请完整填写注册信息"), true);
            return;
        }
        if (password !== confirmPassword) {
            showMessage("registerMessage", authText("auth.error.password_mismatch", "两次输入的密码不一致"), true);
            return;
        }
        if (!termsAccepted) {
            showMessage("registerMessage", authText("auth.error.terms_required", "请先同意服务条款和隐私协议"), true);
            return;
        }
        try {
            const response = await TrpgApi.post<ApiResponse>("/api/auth/register", {
                username,
                email,
                password,
                confirm_password: confirmPassword,
                terms_accepted: termsAccepted,
            });
            if (!response.success) {
                showMessage("registerMessage", localizedAuthMessage(response, authText("auth.error.registration_failed", "注册失败")), true);
                return;
            }
            showMessage("registerMessage", authText("auth.success.registered", "注册成功，请登录"));
            showLoginView();
        } catch (error) {
            console.error("注册失败:", error);
            showMessage("registerMessage", authText("auth.error.registration_failed_retry", "注册失败，请稍后重试"), true);
        }
    }
}
