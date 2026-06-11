interface NetworkConfig {
    port?: number;
    discovery_enabled?: boolean;
}

interface PenetrationConfig {
    enabled?: boolean;
}

interface NetworkStatus {
    server_status?: string;
    lan_ip?: string;
    external_access?: string;
}

interface NetworkTestResult {
    local_ip?: string;
    port?: number;
    connection_success?: boolean;
    error_message?: string;
    discovery_success?: boolean;
    discovery_error?: string;
}

async function initNetworkConfig(): Promise<void> {
    await loadNetworkConfig();

    const saveNetworkConfigBtn = document.getElementById("saveNetworkConfig");
    if (saveNetworkConfigBtn) {
        saveNetworkConfigBtn.addEventListener("click", () => {
            void saveNetworkConfig();
        });
    }

    const testNetworkConnectionBtn = document.getElementById("testNetworkConnection");
    if (testNetworkConnectionBtn) {
        testNetworkConnectionBtn.addEventListener("click", () => {
            void testNetworkConnection();
        });
    }

    setInterval(() => {
        void updateNetworkStatus();
    }, 5000);
    console.log("网络配置初始化成功");
}

async function loadNetworkConfig(): Promise<void> {
    try {
        const data = await TrpgApi.get<ApiResponse<NetworkConfig>>("/api/network/config");

        if (data.success && data.data) {
            const config = data.data;
            const networkPort = document.getElementById("networkPort") as HTMLInputElement | null;
            if (networkPort) {
                networkPort.value = String(config.port || 8086);
            }

            const enableDiscovery = document.getElementById("enableDiscovery") as HTMLInputElement | null;
            if (enableDiscovery) {
                enableDiscovery.checked = config.discovery_enabled !== false;
            }

            await loadPenetrationConfig();
        }
    } catch (error) {
        console.error("加载网络配置失败:", error);
    }
}

async function loadPenetrationConfig(): Promise<void> {
    try {
        const data = await TrpgApi.get<ApiResponse<PenetrationConfig>>("/api/network/penetration");

        if (data.success && data.data) {
            const enablePenetration = document.getElementById("enablePenetration") as HTMLInputElement | null;
            if (enablePenetration) {
                enablePenetration.checked = data.data.enabled === true;
            }
        }
    } catch (error) {
        console.error("加载网络穿透配置失败:", error);
    }
}

async function saveNetworkConfig(): Promise<void> {
    try {
        const networkPort = document.getElementById("networkPort") as HTMLInputElement | null;
        const enableDiscovery = document.getElementById("enableDiscovery") as HTMLInputElement | null;
        if (!networkPort || !enableDiscovery) {
            showNotification("网络配置表单不完整", "error");
            return;
        }

        const data = await TrpgApi.post<ApiResponse>("/api/network/config", {
            port: Number.parseInt(networkPort.value, 10),
            discovery_enabled: enableDiscovery.checked,
        });

        if (data.success) {
            showNotification("网络配置保存成功", "success");
            await updateNetworkStatus();
        } else {
            showNotification(`网络配置保存失败: ${data.message || data.error || "未知错误"}`, "error");
        }
    } catch (error) {
        console.error("保存网络配置失败:", error);
        showNotification(`保存网络配置失败: ${networkErrorMessage(error)}`, "error");
    }
}

async function testNetworkConnection(): Promise<void> {
    try {
        const data = await TrpgApi.post<ApiResponse<NetworkTestResult>>("/api/network/test", {});

        if (data.success && data.data) {
            const testData = data.data;
            let message = `网络连接测试完成\n本地IP: ${testData.local_ip || "-"}\n端口: ${testData.port || "-"}\n连接状态: ${testData.connection_success ? "成功" : "失败"}`;
            if (!testData.connection_success) {
                message += `\n错误信息: ${testData.error_message || "未知"}`;
            }
            message += `\n服务发现: ${testData.discovery_success ? "成功" : "失败"}`;
            if (!testData.discovery_success) {
                message += `\n发现错误: ${testData.discovery_error || "未知"}`;
            }
            showNotification(message, testData.connection_success ? "success" : "error");
            await updateNetworkStatus();
        } else {
            showNotification(`网络连接测试失败: ${data.message || data.error || "未知错误"}`, "error");
        }
    } catch (error) {
        console.error("测试网络连接失败:", error);
        showNotification(`测试网络连接失败: ${networkErrorMessage(error)}`, "error");
    }
}

async function updateNetworkStatus(): Promise<void> {
    try {
        const data = await TrpgApi.get<ApiResponse<NetworkStatus>>("/api/network/status");

        if (data.success && data.data) {
            const status = data.data;
            const serverStatus = document.getElementById("serverStatus");
            if (serverStatus) {
                serverStatus.textContent = status.server_status || "未知";
                serverStatus.className = `status-value ${status.server_status === "运行中" ? "status-success" : "status-error"}`;
            }

            const lanIp = document.getElementById("lanIp");
            if (lanIp) {
                lanIp.textContent = status.lan_ip || "未知";
            }

            const externalAccess = document.getElementById("externalAccess");
            if (externalAccess) {
                externalAccess.textContent = status.external_access || "未知";
                externalAccess.className = `status-value ${status.external_access === "可访问" ? "status-success" : "status-error"}`;
            }
        }
    } catch (error) {
        console.error("更新网络状态失败:", error);
    }
}

function networkErrorMessage(error: unknown): string {
    return error instanceof Error ? error.message : String(error);
}
