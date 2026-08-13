namespace AuthModule {
    export function openProfileDialog(): void {
        const dialog = document.getElementById("edit-profile-dialog");
        dialog?.classList.add("open");
        dialog?.setAttribute("aria-hidden", "false");
        scrollProfileSection("profile-account-info", false);
        TrpgApi.get<ApiResponse<CurrentUser>>("/api/user/profile")
            .then((response) => {
                if (!response.success || !response.data) return;
                const user = response.data;
                (document.getElementById("editUsername") as HTMLInputElement | null)!.value = user.username || "";
                (document.getElementById("editEmail") as HTMLInputElement | null)!.value = user.email || "";
                (document.getElementById("editNickname") as HTMLInputElement | null)!.value = user.nickname || "";
                const avatar = document.getElementById("avatarPreview") as HTMLImageElement | null;
                if (avatar) avatar.src = user.avatar || "/assets/avatars/default.jpg";
            })
            .catch((error) => console.error("获取用户资料失败:", error));
    }

    export function closeProfileDialog(): void {
        const dialog = document.getElementById("edit-profile-dialog");
        dialog?.classList.remove("open");
        dialog?.setAttribute("aria-hidden", "true");
    }

    export function bindProfileNavigation(): void {
        document.querySelectorAll<HTMLButtonElement>(".profile-section-tab[data-profile-target]").forEach((tab) => {
            tab.addEventListener("click", () => scrollProfileSection(tab.dataset.profileTarget || "profile-account-info"));
        });
    }

    export function bindAvatarPreview(): void {
        const avatarInput = document.getElementById("avatarUpload") as HTMLInputElement | null;
        const avatarPreview = document.getElementById("avatarPreview") as HTMLImageElement | null;
        if (!avatarInput || !avatarPreview) return;
        avatarInput.addEventListener("change", () => {
            const file = avatarInput.files?.[0];
            if (!file) return;
            avatarPreview.src = URL.createObjectURL(file);
        });
    }

    export async function saveUserSettings(): Promise<void> {
        const username = (document.getElementById("editUsername") as HTMLInputElement | null)?.value.trim() || "";
        const email = (document.getElementById("editEmail") as HTMLInputElement | null)?.value.trim() || "";
        const nickname = (document.getElementById("editNickname") as HTMLInputElement | null)?.value.trim() || "";
        const avatarFile = (document.getElementById("avatarUpload") as HTMLInputElement | null)?.files?.[0];
        if (!username || !email) {
            showMessage("settingsMessage", "请输入用户名和电子邮件", true);
            return;
        }
        try {
            const formData = new FormData();
            formData.append("username", username);
            formData.append("email", email);
            formData.append("nickname", nickname);
            if (avatarFile) formData.append("avatar", avatarFile);

            const response = await TrpgApi.post<ApiResponse<CurrentUser>>("/api/auth/update", formData);
            if (!response.success || !response.data) {
                showMessage("settingsMessage", apiMessage(response, "保存失败"), true);
                return;
            }
            setCurrentUser({ ...(window.currentUser as CurrentUser), ...response.data });
            showMessage("settingsMessage", "设置已保存");
        } catch (error) {
            console.error("更新用户资料失败:", error);
            showMessage("settingsMessage", "保存失败，请稍后重试", true);
        }
    }

    export function openPasswordDialog(): void {
        const dialog = document.getElementById("password-dialog");
        dialog?.classList.add("open");
        dialog?.setAttribute("aria-hidden", "false");
        showMessage("passwordMessage", "");
    }

    export function closePasswordDialog(): void {
        const dialog = document.getElementById("password-dialog");
        dialog?.classList.remove("open");
        dialog?.setAttribute("aria-hidden", "true");
    }

    export async function changePassword(): Promise<void> {
        const currentPassword = (document.getElementById("passwordCurrentPassword") as HTMLInputElement | null)?.value || "";
        const newPassword = (document.getElementById("passwordNewPassword") as HTMLInputElement | null)?.value || "";
        const confirmPassword = (document.getElementById("passwordConfirmPassword") as HTMLInputElement | null)?.value || "";
        if (!currentPassword || !newPassword || !confirmPassword) {
            showMessage("passwordMessage", "请完整填写密码信息", true);
            return;
        }
        if (newPassword !== confirmPassword) {
            showMessage("passwordMessage", "两次输入的新密码不一致", true);
            return;
        }
        try {
            const response = await TrpgApi.post<ApiResponse>("/api/auth/password/change", {
                current_password: currentPassword,
                new_password: newPassword,
                confirm_password: confirmPassword,
            });
            if (!response.success) {
                showMessage("passwordMessage", apiMessage(response, "密码修改失败"), true);
                return;
            }
            clearPasswordDialogFields();
            showMessage("passwordMessage", "密码已修改");
            setTimeout(closePasswordDialog, 500);
        } catch (error) {
            console.error("密码修改失败:", error);
            showMessage("passwordMessage", "密码修改失败，请稍后重试", true);
        }
    }

    function scrollProfileSection(targetId: string, smooth = true): void {
        const target = document.getElementById(targetId);
        if (!target) return;
        document.querySelectorAll<HTMLElement>(".profile-section-tab[data-profile-target]").forEach((tab) => {
            tab.classList.toggle("active", tab.dataset.profileTarget === targetId);
        });
        target.scrollIntoView({ behavior: smooth ? "smooth" : "auto", block: "start" });
    }

    function clearPasswordDialogFields(): void {
        ["passwordCurrentPassword", "passwordNewPassword", "passwordConfirmPassword"].forEach((id) => {
            const input = document.getElementById(id) as HTMLInputElement | null;
            if (input) input.value = "";
        });
    }

    export async function updatePresence(presence: "online" | "dnd" | "invisible"): Promise<void> {
        try {
            const response = await TrpgApi.put<ApiResponse<CurrentUser>>("/api/user/presence", { presence });
            if (response.success && response.data) {
                setCurrentUser({ ...(window.currentUser as CurrentUser), ...response.data });
                closeUserCard();
                return;
            }
            showMessage("settingsMessage", apiMessage(response, "在线状态更新失败"), true);
        } catch (error) {
            console.error("在线状态更新失败:", error);
            showMessage("settingsMessage", "在线状态更新失败，请稍后重试", true);
        }
    }
}
