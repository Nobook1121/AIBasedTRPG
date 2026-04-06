// Qwen模型配置文件
// 处理Qwen模型的API请求

/**
 * 处理Qwen模型请求
 * @param {Object} input - 输入数据
 * @param {Object} config - 平台配置
 * @param {AbortSignal} abortSignal - 中止信号
 * @returns {AsyncGenerator} 生成器函数，用于流式输出
 */
async function processQwenModel(input, config, abortSignal) {
    const requestData = {
        messages: input.messages,
        model: 'Qwen3.5-Plus',
        stream: true,
        max_tokens: 4096,
        temperature: 0.7,
        top_p: 0.9
    };

    try {
        const response = await fetch(`${config.baseUrl}/v1/chat/completions`, {
            method: 'POST',
            headers: {
                'Authorization': `Bearer ${config.apiKey}`,
                'Content-Type': 'application/json'
            },
            body: JSON.stringify(requestData),
            signal: abortSignal
        });

        if (!response.ok) {
            const e = await response.text();
            throw new Error(`API 错误 ${response.status}: ${e}`);
        }

        const reader = response.body.getReader();
        const decoder = new TextDecoder();

        return (async function* () {
            let buffer = '';
            try {
                while (true) {
                    const { done, value } = await reader.read();
                    if (done) break;
                    buffer += decoder.decode(value, { stream: true });
                    const lines = buffer.split('\n');
                    buffer = lines.pop() || '';
                    for (const line of lines) {
                        const t = line.trim();
                        if (!t || t === 'data: [DONE]') continue;
                        if (t.startsWith('data: ')) {
                            try {
                                const data = JSON.parse(t.slice(6));
                                if (data.choices?.[0]?.delta) {
                                    const delta = data.choices[0].delta;
                                    const content = delta.content ?? '';
                                    const reasoning_content = delta.reasoning_content ?? '';
                                    const finished = data.choices[0].finish_reason === 'stop';
                                    if (content || reasoning_content || finished) {
                                        yield { content, reasoning_content, finished };
                                    }
                                }
                            } catch (e) {
                                console.warn('解析失败:', e);
                            }
                        }
                    }
                }
            } finally {
                reader.releaseLock();
            }
        })();
    } catch (error) {
        console.error('API 调用失败:', error);
        throw error;
    }
}

export default processQwenModel;