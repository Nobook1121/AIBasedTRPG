// 剧本管理模块 - 封面处理

function initScenarioManagement() {
    new ScenarioController();

    document.addEventListener('change', function(e) {
        if (e.target.id === 'coverUpload') {
            handleCoverUpload(e);
        }
    });
}

function handleCoverUpload(e) {
    const file = e.target.files[0];
    if (!file) return;

    if (file.size > 5 * 1024 * 1024) {
        showNotification('封面文件大小不能超过5MB', 'error');
        return;
    }

    if (!file.type.startsWith('image/')) {
        showNotification('请上传图片文件', 'error');
        return;
    }

    const reader = new FileReader();
    reader.onload = function(e) {
        document.getElementById('coverPreview').src = e.target.result;
    };
    reader.readAsDataURL(file);

    window.uploadedCoverFile = file;

    const formData = new FormData();
    formData.append('cover', file);
    const scenarioTitle = document.getElementById('scenarioTitle').value.trim() || 'unknown_scenario';
    formData.append('scenario_title', scenarioTitle);

    TrpgApi.requestWithResponse('/api/scenarios/cover', {
        method: 'POST',
        body: formData
    })
    .then(({ response, data }) => {
        if (!response.ok) {
            throw new Error(data.message || '上传失败');
        }
        return data;
    })
    .then(data => {
        if (data.success) {
            showNotification('封面上传成功', 'success');
            document.getElementById('scenarioCoverUrl').value = data.data.cover_url;
        } else {
            showNotification(data.message, 'error');
        }
    })
    .catch(error => {
        console.error('上传封面失败:', error);
        showNotification('上传封面失败: ' + error.message, 'error');
    });
}
