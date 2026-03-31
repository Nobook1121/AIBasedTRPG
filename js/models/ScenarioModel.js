// 剧本模型类 - MVC架构的Model层
class ScenarioModel {
    constructor() {
        this.scenarios = [];
        this.apiBaseUrl = '/api';
        this.scenariosDir = 'scenarios';
        this.userId = null;
        this.isAuthenticated = false;
    }
    
    // 获取当前用户ID
    getCurrentUserId() {
        return this.userId;
    }

    // 检查认证状态
    async checkAuthStatus() {
        try {
            const response = await fetch('/api/auth/status');
            if (response.ok) {
                const data = await response.json();
                if (data.success) {
                    this.userId = data.data.user_id;
                    this.isAuthenticated = true;
                    return true;
                }
            }
        } catch (error) {
            console.error('检查认证状态失败:', error);
        }
        this.isAuthenticated = false;
        return false;
    }

    // 初始化
    async init() {
        await this.checkAuthStatus();
        return this.loadScenarios();
    }

    // 加载所有剧本
    async loadScenarios() {
        try {
            console.log('开始加载剧本...');
            this.scenarios = [];

            // 尝试从API加载
            try {
                const response = await fetch(`${this.apiBaseUrl}/scenarios`);
                if (response.ok) {
                    const data = await response.json();
                    if (data.success) {
                        console.log('从API加载剧本成功');
                        this.scenarios = data.data;
                        // 保存到本地存储作为备份
                        localStorage.setItem('trpg_scenarios', JSON.stringify(this.scenarios));
                        return this.scenarios;
                    } else {
                        console.log('API返回错误:', data.message);
                    }
                } else {
                    console.log('API请求失败:', response.status);
                }
            } catch (error) {
                console.log('从API加载剧本失败，尝试从本地存储加载:', error);
            }

            // 尝试从本地存储加载
            const storedScenarios = localStorage.getItem('trpg_scenarios');
            if (storedScenarios) {
                console.log('从本地存储加载剧本');
                this.scenarios = JSON.parse(storedScenarios);
                return this.scenarios;
            }

            // 使用默认剧本
            this.loadDefaultScenarios();
            return this.scenarios;
        } catch (error) {
            console.error('加载剧本时出错:', error);
            this.loadDefaultScenarios();
            return this.scenarios;
        }
    }



    // 加载默认剧本
    loadDefaultScenarios() {
        console.log('加载默认剧本');
        this.scenarios = [
            {
                id: 1,
                title: '古宅奇案',
                author: '匿名',
                playerCount: 4,
                notes: '经典的恐怖推理剧本',
                background: '一座古老的宅邸，隐藏着不为人知的秘密。多年前，宅邸的主人神秘失踪，从此宅邸被遗弃。最近，一群好奇的年轻人决定探索这座宅邸，却发现了一些可怕的真相...',
                preparation: '玩家需要创建调查员角色，推荐职业包括侦探、医生、记者等。GM需要准备一些恐怖氛围的描述。',
                scenes: [
                    {
                        id: 1,
                        content: '玩家们来到古宅门口，发现大门虚掩着。进入后，大厅里布满灰尘，墙上挂着褪色的肖像画。突然，楼梯上传来奇怪的脚步声...',
                        marker: ''
                    },
                    {
                        id: 2,
                        content: '玩家们在书房发现了一本日记，记录了宅邸主人的诡异实验。日记最后一页提到了一个隐藏的地下室...',
                        marker: ''
                    },
                    {
                        id: 3,
                        content: '玩家们找到了地下室入口，里面弥漫着奇怪的气味。在地下室深处，他们发现了一个祭坛和一些可怕的实验器材...',
                        marker: ''
                    }
                ],
                endings: [
                    {
                        id: 1,
                        content: '玩家们成功销毁了祭坛，阻止了邪恶的仪式。但古宅的秘密仍然存在...',
                        marker: ''
                    },
                    {
                        id: 2,
                        content: '玩家们被邪恶力量所困，永远留在了古宅中...',
                        marker: ''
                    }
                ],
                createdAt: new Date().toISOString()
            },
            {
                id: 2,
                title: '星际探索',
                author: '匿名',
                playerCount: 3,
                notes: '科幻题材剧本',
                background: '公元2150年，人类的太空探索计划发现了一个神秘的信号源，来自距离地球100光年的一颗未知行星。一支由科学家和宇航员组成的探索队被派遣前往调查，却发现了远超他们想象的秘密...',
                preparation: '玩家需要创建宇航员或科学家角色，推荐职业包括生物学家、工程师、飞行员等。GM需要准备一些科幻场景的描述。',
                scenes: [
                    {
                        id: 1,
                        content: '探索队抵达目标行星，发现这颗行星环境适宜生命存在。他们开始在表面建立基地，并进行初步探索...',
                        marker: ''
                    },
                    {
                        id: 2,
                        content: '探索队在地表发现了古老的外星文明遗迹，其中包含一些奇怪的技术和符号。科学家们开始解码这些信息...',
                        marker: ''
                    },
                    {
                        id: 3,
                        content: '探索队发现了一个地下设施，里面保存着外星文明的核心技术。但同时，他们也触发了某种防御机制...',
                        marker: ''
                    }
                ],
                endings: [
                    {
                        id: 1,
                        content: '探索队成功获取了外星技术，返回地球后推动了人类文明的巨大进步...',
                        marker: ''
                    },
                    {
                        id: 2,
                        content: '探索队被外星防御机制消灭，他们的故事成为了人类太空探索史上的一段传奇...',
                        marker: ''
                    }
                ],
                createdAt: new Date().toISOString()
            }
        ];
        // 保存到本地存储
        localStorage.setItem('trpg_scenarios', JSON.stringify(this.scenarios));
    }

    // 创建剧本
    async createScenario(scenarioData) {
        try {
            // 检查认证状态
            if (!this.isAuthenticated) {
                const authStatus = await this.checkAuthStatus();
                if (!authStatus) {
                    throw new Error('请先登录');
                }
            }

            // 通过API创建剧本
            const response = await fetch(`${this.apiBaseUrl}/scenarios`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({
                    ...scenarioData,
                    user_id: this.userId
                })
            });
            
            const data = await response.json();
            
            if (!response.ok || !data.success) {
                throw new Error(data.message || `API请求失败: ${response.status}`);
            }
            
            const scenario = data.data;
            this.scenarios.push(scenario);
            this.saveScenarios();
            console.log('剧本创建成功');
            return scenario;
        } catch (error) {
            console.error('创建剧本时出错:', error);
            throw error;
        }
    }

    // 更新剧本
    async updateScenario(id, scenarioData) {
        try {
            // 检查认证状态
            if (!this.isAuthenticated) {
                const authStatus = await this.checkAuthStatus();
                if (!authStatus) {
                    throw new Error('请先登录');
                }
            }

            // 通过API更新剧本
            const response = await fetch(`${this.apiBaseUrl}/scenarios/${id}`, {
                method: 'PUT',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({
                    ...scenarioData,
                    user_id: this.userId
                })
            });
            
            const data = await response.json();
            
            if (!response.ok || !data.success) {
                throw new Error(data.message || `API请求失败: ${response.status}`);
            }
            
            const updatedScenario = data.data;
            const index = this.scenarios.findIndex(s => s.id === id);
            if (index !== -1) {
                this.scenarios[index] = updatedScenario;
                this.saveScenarios();
                console.log('剧本更新成功');
                return updatedScenario;
            }
            throw new Error('剧本不存在');
        } catch (error) {
            console.error('更新剧本时出错:', error);
            throw error;
        }
    }

    // 删除剧本
    async deleteScenario(id) {
        try {
            // 检查认证状态
            if (!this.isAuthenticated) {
                const authStatus = await this.checkAuthStatus();
                if (!authStatus) {
                    throw new Error('请先登录');
                }
            }

            // 通过API删除剧本
            const response = await fetch(`${this.apiBaseUrl}/scenarios/${id}`, {
                method: 'DELETE',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({
                    user_id: this.userId
                })
            });
            
            const data = await response.json();
            
            if (!response.ok || !data.success) {
                throw new Error(data.message || `API请求失败: ${response.status}`);
            }
            
            const index = this.scenarios.findIndex(s => s.id === id);
            if (index !== -1) {
                this.scenarios.splice(index, 1);
                this.saveScenarios();
                console.log('剧本删除成功');
                return true;
            }
            throw new Error('剧本不存在');
        } catch (error) {
            console.error('删除剧本时出错:', error);
            throw error;
        }
    }

    // 获取单个剧本
    getScenario(id) {
        return this.scenarios.find(s => s.id === id);
    }

    // 获取所有剧本
    getScenarios() {
        return this.scenarios;
    }

    // 保存所有剧本到本地存储
    saveScenarios() {
        localStorage.setItem('trpg_scenarios', JSON.stringify(this.scenarios));
    }

    // 导入剧本
    async importScenario(scenarioData) {
        try {
            // 验证剧本数据格式
            if (!this.validateScenarioData(scenarioData)) {
                throw new Error('剧本数据格式不正确');
            }

            // 移除原有ID，让系统生成新ID
            delete scenarioData.id;
            
            // 创建剧本
            return await this.createScenario(scenarioData);
        } catch (error) {
            console.error('导入剧本时出错:', error);
            throw error;
        }
    }

    // 验证剧本数据格式
    validateScenarioData(data) {
        // 检查必需字段
        if (!data || typeof data !== 'object') {
            return false;
        }
        
        // 检查基本字段
        if (!data.title || typeof data.title !== 'string') {
            return false;
        }
        
        if (!data.author || typeof data.author !== 'string') {
            return false;
        }
        
        // playerCount 可以是数字或字符串数字
        if (data.playerCount === undefined || data.playerCount === null) {
            return false;
        }

        // scenes 和 endings 应该是数组（如果存在）
        if (data.scenes && !Array.isArray(data.scenes)) {
            return false;
        }
        
        if (data.endings && !Array.isArray(data.endings)) {
            return false;
        }

        return true;
    }
}

// 导出模块
export default ScenarioModel;