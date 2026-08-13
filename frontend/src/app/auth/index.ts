namespace AuthModule {
    export async function initAuth(): Promise<boolean> {
        bindAuthEvents();
        prefillRememberedUsername();
        bindFloatingFields();
        return checkAuthStatus();
    }

    function bindAuthEvents(): void {
        document.getElementById("show-register-view")?.addEventListener("click", showRegisterView);
        document.getElementById("show-login-view")?.addEventListener("click", showLoginView);
        document.getElementById("loginButton")?.addEventListener("click", login);
        document.getElementById("registerButton")?.addEventListener("click", register);
        document.getElementById("close-auth-modal")?.addEventListener("click", closeAuthModal);
        document.getElementById("logoutButton")?.addEventListener("click", logout);
        document.getElementById("switchAccountButton")?.addEventListener("click", switchAccount);
        document.getElementById("open-profile-dialog")?.addEventListener("click", openProfileDialog);
        document.getElementById("close-settings-panel")?.addEventListener("click", closeProfileDialog);
        document.getElementById("saveUserSettings")?.addEventListener("click", saveUserSettings);
        document.getElementById("open-password-dialog")?.addEventListener("click", openPasswordDialog);
        document.getElementById("close-password-dialog")?.addEventListener("click", closePasswordDialog);
        document.getElementById("cancelPasswordDialog")?.addEventListener("click", closePasswordDialog);
        document.getElementById("changePasswordButton")?.addEventListener("click", changePassword);
        document.getElementById("userInfo")?.addEventListener("click", toggleUserCard);
        bindProfileNavigation();
        bindAvatarPreview();
        document.querySelectorAll<HTMLButtonElement>("[data-presence]").forEach((button) => {
            button.addEventListener("click", () => updatePresence(button.dataset.presence as "online" | "dnd" | "invisible"));
        });
    }
}

window.initAuth = AuthModule.initAuth;
window.setCurrentEditingScenarioId = AuthModule.setCurrentEditingScenarioId;
