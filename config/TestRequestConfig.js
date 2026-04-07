// 测试请求配置文件
// 为不同模型定义不同的测试请求配置

const testRequestConfigs = {
    // Qwen3.5-Plus模型的测试请求配置
    'qwen3.5-plus': {
        messages: [
            {
                role: 'user',
                content: 'reply a'
            }
        ],
        temperature: 0,
        max_tokens: 1,
        stop: ['\n'],
        extra_body: {
            enable_thinking: false
        }
    },
    // LMStudio模型的测试请求配置
    'local-model': {
        messages: [
            {
                role: 'user',
                content: 'a'
            }
        ],
        temperature: 0,
        max_tokens: 1,
        stop: ['\n']
    },
    // 其他模型的默认测试请求配置
    'default': {
        messages: [
            {
                role: 'user',
                content: 'a'
            }
        ],
        temperature: 0,
        max_tokens: 1,
        stop: ['\n']
    }
};

// 获取模型的测试请求配置
export function getTestRequestConfig(modelId) {
    // 检查是否有特定模型的配置
    for (const key in testRequestConfigs) {
        if (modelId.toLowerCase().includes(key.toLowerCase())) {
            return testRequestConfigs[key];
        }
    }
    // 如果没有特定模型的配置，使用默认配置
    return testRequestConfigs.default;
}

export default testRequestConfigs;