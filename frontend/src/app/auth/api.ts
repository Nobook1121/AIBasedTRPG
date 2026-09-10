namespace AuthModule {
    export interface ApiResponse<T = unknown> {
        success: boolean;
        message?: string;
        error?: string;
        data?: T;
    }

    export function apiMessage(response: ApiResponse, fallback: string): string {
        return response.message || fallback;
    }

    export function localizedAuthMessage(response: ApiResponse, fallback: string): string {
        const message = response.message || response.error || fallback;
        const legacyChineseMessages: Record<string, string> = {
            "Password must be at least 8 characters": "密码至少需要 8 个字符",
            "Password must include a letter": "密码必须包含字母",
            "Password must include a number": "密码必须包含数字",
        };
        const keys: Record<string, string> = {
            "Invalid username/email or password": "auth.error.invalid_credentials",
            "Invalid password": "auth.error.invalid_credentials",
            "Please provide username and password": "auth.error.missing_credentials",
            "Please provide username or email and password": "auth.error.missing_credentials",
            "Incomplete data": "auth.error.incomplete_data",
            "Terms must be accepted": "auth.error.terms_required",
            "Passwords do not match": "auth.error.password_mismatch",
            "Username already exists": "auth.error.username_exists",
            "Email already exists": "auth.error.email_exists",
            "Invalid username": "auth.error.invalid_username",
            "Invalid email": "auth.error.invalid_email",
            "Password must be at least 8 characters": "auth.error.password_length",
            "Password must include a letter": "auth.error.password_letter",
            "Password must include a number": "auth.error.password_number",
            "Login failed": "auth.error.login_failed",
            "Registration failed": "auth.error.registration_failed",
        };
        const key = keys[message];
        return key
            ? (window.TrpgI18n?.t(key, legacyChineseMessages[message] || fallback) || fallback)
            : legacyChineseMessages[message] || message || fallback;
    }
}
