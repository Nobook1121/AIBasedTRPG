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
        const translations: Record<string, string> = {
            "Invalid username/email or password": "用户名或邮箱或密码错误",
            "Invalid password": "用户名或邮箱或密码错误",
            "Please provide username and password": "请输入用户名或邮箱和密码",
            "Incomplete data": "请完整填写信息",
            "Terms must be accepted": "请先同意服务条款和隐私协议",
            "Passwords do not match": "两次输入的密码不一致",
            "Username already exists": "用户名已存在",
            "Email already exists": "电子邮件已存在",
            "Invalid username": "用户名格式不正确",
            "Invalid email": "电子邮件格式不正确",
            "Login failed": "登录失败",
            "Registration failed": "注册失败",
        };
        return translations[message] || fallback;
    }
}
