const defaultTestRequestConfig: TestRequestConfig = {
    messages: [{ role: "user", content: "a" }],
    temperature: 0,
    max_tokens: 1,
    stop: ["\n"],
};

const testRequestConfigs: Record<string, TestRequestConfig> = {
    "qwen3.5-plus": {
        messages: [{ role: "user", content: "reply a" }],
        temperature: 0,
        max_tokens: 1,
        stop: ["\n"],
        extra_body: {
            enable_thinking: false,
        },
    },
    "local-model": {
        messages: [{ role: "user", content: "a" }],
        temperature: 0,
        max_tokens: 1,
        stop: ["\n"],
    },
    default: defaultTestRequestConfig,
};

function getTestRequestConfig(modelId: string): TestRequestConfig {
    for (const key of Object.keys(testRequestConfigs)) {
        if (modelId.toLowerCase().includes(key.toLowerCase())) {
            return testRequestConfigs[key] || defaultTestRequestConfig;
        }
    }
    return defaultTestRequestConfig;
}

window.testRequestConfigs = testRequestConfigs;
window.getTestRequestConfig = getTestRequestConfig;
