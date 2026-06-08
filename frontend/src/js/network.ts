// @ts-nocheck
// 网络配置管理模块

function initNetworkConfig() {
    loadNetworkConfig();

    const saveNetworkConfigBtn = document.getElementById('saveNetworkConfig');
    if (saveNetworkConfigBtn) {
        saveNetworkConfigBtn.addEventListener('click', saveNetworkConfig);
    }

    const testNetworkConnectionBtn = document.getElementById('testNetworkConnection');
    if (testNetworkConnectionBtn) {
        testNetworkConnectionBtn.addEventListener('click', testNetworkConnection);
    }

    setInterval(updateNetworkStatus, 5000);
    console.log('网络配置初始化成功');
}

async function loadNetworkConfig() {
    try {
        const data = await TrpgApi.get('/api/network/config');

        if (data.success) {
            const config = data.data;

            const networkPort = document.getElementById('networkPort');
            if (networkPort) {
                networkPort.value = config.port || 8086;
            }

            const enableDiscovery = document.getElementById('enableDiscovery');
            if (enableDiscovery) {
                enableDiscovery.checked = config.discovery_enabled !== false;
            }

            loadPenetrationConfig();
        }
    } catch (error) {
        console.error('加载网络配置失败:', error);
    }
}

async function loadPenetrationConfig() {
    try {
        const data = await TrpgApi.get('/api/network/penetration');

        if (data.success) {
            const config = data.data;

            const enablePenetration = document.getElementById('enablePenetration');
            if (enablePenetration) {
                enablePenetration.checked = config.enabled === true;
            }
        }
    } catch (error) {
        console.error('加载网络穿透配置失败:', error);
    }
}

async function saveNetworkConfig() {
    try {
        const port = document.getElementById('networkPort').value;
        const discoveryEnabled = document.getElementById('enableDiscovery').checked;

        const data = await TrpgApi.post('/api/network/config', {
            port: parseInt(port),
            discovery_enabled: discoveryEnabled
        });

        if (data.success) {
            showNotification('网络配置保存成功', 'success');
            updateNetworkStatus();
        } else {
            showNotification('网络配置保存失败: ' + data.message, 'error');
        }
    } catch (error) {
        console.error('保存网络配置失败:', error);
        showNotification('保存网络配置失败: ' + error.message, 'error');
    }
}

async function testNetworkConnection() {
    try {
        const data = await TrpgApi.post('/api/network/test', {});

        if (data.success) {
            const testData = data.data;
            let message = `网络连接测试完成\n本地IP: ${testData.local_ip}\n端口: ${testData.port}\n连接状态: ${testData.connection_success ? '成功' : '失败'}`;
            if (!testData.connection_success) {
                message += `\n错误信息: ${testData.error_message}`;
            }
            message += `\n服务发现: ${testData.discovery_success ? '成功' : '失败'}`;
            if (!testData.discovery_success) {
                message += `\n发现错误: ${testData.discovery_error}`;
            }
            showNotification(message, testData.connection_success ? 'success' : 'error');
            updateNetworkStatus();
        } else {
            showNotification('网络连接测试失败: ' + data.message, 'error');
        }
    } catch (error) {
        console.error('测试网络连接失败:', error);
        showNotification('测试网络连接失败: ' + error.message, 'error');
    }
}

async function updateNetworkStatus() {
    try {
        const data = await TrpgApi.get('/api/network/status');

        if (data.success) {
            const status = data.data;

            const serverStatus = document.getElementById('serverStatus');
            if (serverStatus) {
                serverStatus.textContent = status.server_status || '未知';
                serverStatus.className = 'status-value ' + (status.server_status === '运行中' ? 'status-success' : 'status-error');
            }

            const lanIp = document.getElementById('lanIp');
            if (lanIp) {
                lanIp.textContent = status.lan_ip || '未知';
            }

            const externalAccess = document.getElementById('externalAccess');
            if (externalAccess) {
                externalAccess.textContent = status.external_access || '未知';
                externalAccess.className = 'status-value ' + (status.external_access === '可访问' ? 'status-success' : 'status-error');
            }
        }
    } catch (error) {
        console.error('更新网络状态失败:', error);
    }
}
