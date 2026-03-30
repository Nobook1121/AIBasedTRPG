// 剧本控制器类 - MVC架构的Controller层
import ScenarioModel from '../models/ScenarioModel.js';
import ScenarioView from '../views/ScenarioView.js';

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
        this.view.openCreateModal();
    }

    // 保存剧本事件
    async onSaveScenario() {
        try {
            // 获取表单数据
            const scenarioData = this.view.getFormData();
            
            // 创建剧本
            await this.model.createScenario(scenarioData);
            
            // 渲染剧本列表
            this.renderScenarioList();
            
            // 关闭模态框
            this.view.closeModal();
            
            // 显示成功消息
            this.view.showMessage('剧本保存成功！');
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
            this.view.openEditModal(scenario);
            
            // 重新绑定保存按钮事件，处理编辑逻辑
            document.getElementById('saveScenario').onclick = async () => {
                try {
                    // 获取表单数据
                    const scenarioData = this.view.getFormData();
                    
                    // 更新剧本
                    await this.model.updateScenario(id, scenarioData);
                    
                    // 渲染剧本列表
                    this.renderScenarioList();
                    
                    // 关闭模态框
                    this.view.closeModal();
                    
                    // 显示成功消息
                    this.view.showMessage('剧本更新成功！');
                } catch (error) {
                    console.error('更新剧本时出错:', error);
                    this.view.showMessage(error.message, true);
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


}

// 导出模块
export default ScenarioController;