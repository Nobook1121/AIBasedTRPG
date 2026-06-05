// 剧本控制器类 - MVC架构的Controller层
// 改为普通脚本，使用全局变量
class ScenarioController {
    constructor() {
        // 初始化Model
        this.model = new ScenarioModel();
        
        // 初始化View
        this.view = new ScenarioView();
        
        // 绑定事件处理函数
        this.bindEventHandlers();
        
        // 初始化
        this.init();
    }

    // 初始化
    async init() {
        try {
            // 加载剧本数据
            await this.model.init();
            
            // 渲染剧本列表
            this.renderScenarioList();
        } catch (error) {
            console.error('初始化剧本控制器时出错:', error);
            this.view.showMessage('初始化失败: ' + error.message, true);
        }
    }

    // 绑定事件处理函数
    bindEventHandlers() {
        const handlers = {
            onCreateScenarioClick: () => this.onCreateScenarioClick(),
            onSaveScenario: () => this.onSaveScenario(),
            onPreviewScenario: (id) => this.onPreviewScenario(id),
            onEditScenario: (id) => this.onEditScenario(id),
            onDeleteScenario: (id) => this.onDeleteScenario(id),
            onImportScenario: (files) => this.onImportScenario(files)
        };
        
        this.view.setEventHandlers(handlers);
    }

    // 渲染剧本列表
    renderScenarioList() {
        const scenarios = this.model.getScenarios();
        this.view.renderScenarioList(scenarios);
    }

    // 创建剧本按钮点击事件
    onCreateScenarioClick() {
        // 清除当前编辑的剧本ID，确保封面上传时使用时间戳作为临时ID
        if (window.setCurrentEditingScenarioId) {
            window.setCurrentEditingScenarioId(null);
        }
        this.view.openCreateModal();
    }

    // 保存剧本事件
    async onSaveScenario() {
        try {
            // 获取表单数据
            let scenarioData = this.view.getFormData();
            
            // 创建剧本，获取真实ID
            const scenario = await this.model.createScenario(scenarioData);
            
            // 使用统一的封面重命名方法处理封面
            const coverUrl = document.getElementById('scenarioCoverUrl').value;
            await this.renameScenarioCover(scenario, coverUrl, 'title');
            
            // 更新本地存储中的剧本数据
            this.model.scenarios[this.model.scenarios.findIndex(s => s.id === scenario.id)] = scenario;
            this.model.saveScenarios();
            
            // 渲染剧本列表
            this.renderScenarioList();
            
            // 关闭模态框
            this.view.closeModal();
            
            // 显示成功消息
            this.view.showMessage('剧本保存成功！');
            
            // 刷新页面以显示更新后的封面
            setTimeout(() => {
                location.reload();
            }, 1000);
        } catch (error) {
            console.error('保存剧本时出错:', error);
            this.view.showMessage(error.message, true);
        }
    }

    // 预览剧本事件
    onPreviewScenario(id) {
        const scenario = this.model.getScenario(id);
        if (scenario) {
            this.view.previewScenario(scenario);
        } else {
            this.view.showMessage('剧本不存在', true);
        }
    }

    // 编辑剧本事件
    onEditScenario(id) {
        const scenario = this.model.getScenario(id);
        if (scenario) {
            // 设置当前编辑的剧本ID，以便封面上传时使用
            if (window.setCurrentEditingScenarioId) {
                window.setCurrentEditingScenarioId(id);
            }
            
            this.view.openEditModal(scenario);
            
            // 移除原始的保存按钮事件监听器
            const saveButton = document.getElementById('saveScenario');
            if (this.view.saveScenarioHandler) {
                saveButton.removeEventListener('click', this.view.saveScenarioHandler);
            }
            
            // 重新绑定保存按钮事件，处理编辑逻辑
            saveButton.onclick = async () => {
                try {
                    // 获取表单数据
                    let scenarioData = this.view.getFormData();
                    
                    // 使用统一的封面重命名方法处理封面
                    const tempScenario = { id: id };
                    await this.renameScenarioCover(tempScenario, scenarioData.cover, 'id');
                    scenarioData.cover = tempScenario.cover;
                    
                    // 直接更新本地剧本数据，不调用updateScenario避免认证问题
                    const updatedScenario = {
                        ...scenario,
                        ...scenarioData,
                        id: id
                    };
                    // 更新本地存储中的剧本数据
                    this.model.scenarios[this.model.scenarios.findIndex(s => s.id === id)] = updatedScenario;
                    this.model.saveScenarios();
                    
                    // 重新添加原始的保存按钮事件监听器
                    saveButton.addEventListener('click', this.view.saveScenarioHandler);
                    
                    // 渲染剧本列表
                    this.renderScenarioList();
                    
                    // 关闭模态框
                    this.view.closeModal();
                    
                    // 显示成功消息
                    this.view.showMessage('剧本更新成功！');
                } catch (error) {
                    console.error('更新剧本时出错:', error);
                    this.view.showMessage(error.message, true);
                    // 即使出错也要重新添加原始的保存按钮事件监听器
                    saveButton.addEventListener('click', this.view.saveScenarioHandler);
                }
            };
        } else {
            this.view.showMessage('剧本不存在', true);
        }
    }

    // 删除剧本事件
    async onDeleteScenario(id) {
        if (confirm('确定要删除这个剧本吗？')) {
            try {
                // 获取剧本信息，用于删除对应封面
                const scenario = this.model.getScenario(id);
                if (scenario) {
                    // 构建封面路径，确保只使用scenario_covers文件夹
                    const safeTitle = scenario.title.replace(/[^a-zA-Z0-9]/g, '_');
                    const coverPath = `/scenario_covers/${safeTitle}.png`;
                    
                    // 调用API删除封面
                    try {
                        await TrpgApi.del('/api/scenarios/cover', {
                            body: {
                                cover_path: coverPath
                            }
                        });
                    } catch (coverError) {
                        console.error('删除封面时出错:', coverError);
                        // 封面删除失败不影响剧本删除
                    }
                }
                
                // 删除剧本
                await this.model.deleteScenario(id);
                this.renderScenarioList();
                this.view.showMessage('剧本删除成功！');
            } catch (error) {
                console.error('删除剧本时出错:', error);
                this.view.showMessage('删除剧本失败: ' + error.message, true);
            }
        }
    }

    // 导入剧本事件
    async onImportScenario(files) {
        if (!files || files.length === 0) {
            return;
        }

        let successCount = 0;
        let errorCount = 0;
        const errors = [];

        for (const file of files) {
            try {
                const content = await this.readFile(file);
                const scenarioData = JSON.parse(content);
                
                // 导入剧本
                await this.model.importScenario(scenarioData);
                successCount++;
            } catch (error) {
                errorCount++;
                errors.push(`"${file.name}": ${error.message}`);
                console.error(`导入文件 "${file.name}" 失败:`, error);
            }
        }

        // 刷新列表
        this.renderScenarioList();

        // 显示结果
        if (successCount > 0 && errorCount === 0) {
            this.view.showMessage(`成功导入 ${successCount} 个剧本！`);
        } else if (successCount > 0 && errorCount > 0) {
            this.view.showMessage(`成功导入 ${successCount} 个剧本，${errorCount} 个失败。\n\n失败详情:\n${errors.join('\n')}`);
        } else {
            this.view.showMessage(`导入失败！\n\n错误详情:\n${errors.join('\n')}`, true);
        }
    }

    // 读取文件内容
    readFile(file) {
        return new Promise((resolve, reject) => {
            const reader = new FileReader();
            reader.onload = (e) => resolve(e.target.result);
            reader.onerror = (e) => reject(new Error('文件读取失败'));
            reader.readAsText(file);
        });
    }

    /**
     * 重命名剧本封面文件（统一处理新建和编辑时的封面重命名逻辑）
     * @param {Object} scenario - 剧本对象
     * @param {string} coverUrl - 当前封面URL
     * @param {string} namingStrategy - 命名策略：'title'使用标题命名，'id'使用ID命名
     * @returns {Promise<Object>} 更新后的剧本对象
     */
    async renameScenarioCover(scenario, coverUrl, namingStrategy = 'title') {
        const DEFAULT_COVER = '/scenario_covers/default_cover.png';

        // 如果没有封面或已是默认封面，直接返回
        if (!coverUrl || coverUrl === DEFAULT_COVER) {
            scenario.cover = DEFAULT_COVER;
            return scenario;
        }

        // 确保只使用scenario_covers文件夹的路径
        if (!coverUrl.startsWith('/scenario_covers/')) {
            scenario.cover = DEFAULT_COVER;
            return scenario;
        }

        try {
            // 提取旧封面文件名
            const oldCoverFilename = coverUrl.split('/').pop();

            // 根据策略生成新文件名
            let newCoverFilename;
            if (namingStrategy === 'title') {
                const safeTitle = (scenario.title || '').replace(/[\/\\]/g, '_');
                newCoverFilename = `${safeTitle}.png`;
            } else {
                newCoverFilename = `${scenario.id}.png`;
            }

            // 如果文件名没有变化，直接返回
            if (oldCoverFilename === newCoverFilename) {
                scenario.cover = `/scenario_covers/${newCoverFilename}`;
                return scenario;
            }

            // 调用API重命名文件
            const data = await TrpgApi.post('/api/scenarios/cover/rename', {
                old_filename: oldCoverFilename,
                new_filename: newCoverFilename
            });

            if (data.success) {
                console.log(`封面文件重命名成功: ${oldCoverFilename} -> ${newCoverFilename}`);
                scenario.cover = `/scenario_covers/${newCoverFilename}`;
            } else {
                console.warn('重命名封面文件失败:', data.message);
                scenario.cover = DEFAULT_COVER;
            }
        } catch (error) {
            console.error('重命名封面文件时出错:', error);
            scenario.cover = DEFAULT_COVER;
        }

        return scenario;
    }


}

// 导出为全局变量
window.ScenarioController = ScenarioController;
