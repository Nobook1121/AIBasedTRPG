// @ts-nocheck
// 标签页切换模块
function initTabs() {
    try {
        const navLinks = document.querySelectorAll('#sidebar .nav-link');
        const tabContents = document.querySelectorAll('.tab-content');
        if (navLinks.length === 0 || tabContents.length === 0) {
            console.error('无法找到导航链接或标签内容');
            return;
        }
        function updateNavigationState(activeLink) {
            navLinks.forEach(link => {
                if (link === activeLink) {
                    link.setAttribute('aria-current', 'page');
                }
                else {
                    link.removeAttribute('aria-current');
                }
            });
        }
        updateNavigationState(document.querySelector('#sidebar .nav-link.active'));
        navLinks.forEach(link => {
            link.addEventListener('click', function (e) {
                e.preventDefault();
                const isInDropdown = this.closest('.dropdown-container');
                if (!isInDropdown) {
                    const dropdownBtns = document.querySelectorAll('.dropdown-btn');
                    dropdownBtns.forEach(btn => {
                        btn.classList.remove('active');
                        const dropdownContent = btn.nextElementSibling;
                        if (dropdownContent) {
                            dropdownContent.style.display = 'none';
                        }
                    });
                }
                navLinks.forEach(l => l.classList.remove('active'));
                tabContents.forEach(tab => tab.classList.remove('active'));
                this.classList.add('active');
                updateNavigationState(this);
                const tabId = this.getAttribute('data-tab');
                if (!tabId) {
                    console.error('导航链接缺少data-tab属性');
                    return;
                }
                const targetTab = document.getElementById(tabId);
                if (!targetTab) {
                    console.error(`找不到id为${tabId}的标签内容`);
                    return;
                }
                targetTab.classList.add('active');
                console.log(`切换到标签页: ${tabId}`);
                if (tabId === 'settings') {
                    const settingsLink = this.getAttribute('href');
                    if (settingsLink) {
                        const settingsTab = settingsLink.replace('#', '');
                        const tabName = settingsTab.replace('settings-', '');
                        switchSettingsTab(tabName);
                    }
                }
                if (tabId === 'tools') {
                    const toolsLink = this.getAttribute('href');
                    if (toolsLink) {
                        const toolsTab = toolsLink.replace('#', '');
                        if (toolsTab === 'tools-dice') {
                            switchToolTab('dice');
                        }
                    }
                }
            });
        });
        const dropdownBtns = document.querySelectorAll('.dropdown-btn');
        dropdownBtns.forEach(btn => {
            btn.setAttribute('aria-expanded', btn.classList.contains('active') ? 'true' : 'false');
            btn.addEventListener('click', function () {
                this.classList.toggle('active');
                const dropdownContent = this.nextElementSibling;
                const isExpanded = dropdownContent.style.display !== 'block';
                if (isExpanded) {
                    dropdownContent.style.display = 'block';
                }
                else {
                    dropdownContent.style.display = 'none';
                }
                this.setAttribute('aria-expanded', String(isExpanded));
                dropdownBtns.forEach(otherBtn => {
                    if (otherBtn !== this) {
                        otherBtn.classList.remove('active');
                        otherBtn.setAttribute('aria-expanded', 'false');
                        const otherContent = otherBtn.nextElementSibling;
                        if (otherContent) {
                            otherContent.style.display = 'none';
                        }
                    }
                });
            });
        });
        console.log('标签切换初始化成功');
    }
    catch (error) {
        console.error('初始化标签切换时出错:', error);
    }
}
function switchSettingsTab(tabName) {
    const settingsTabs = document.querySelectorAll('.settings-tab');
    const settingsContents = document.querySelectorAll('.settings-content');
    settingsTabs.forEach(tab => {
        tab.classList.remove('active');
        tab.setAttribute('aria-selected', 'false');
    });
    settingsContents.forEach(content => content.classList.remove('active'));
    const targetTab = document.querySelector(`.settings-tab[data-settings="${tabName}"]`);
    const targetContent = document.getElementById(`${tabName}-settings-content`);
    if (targetTab) {
        targetTab.classList.add('active');
        targetTab.setAttribute('aria-selected', 'true');
    }
    if (targetContent)
        targetContent.classList.add('active');
}
function switchToolTab(toolName) {
    const toolTabs = document.querySelectorAll('.tool-tab');
    const toolContents = document.querySelectorAll('.tool-content');
    toolTabs.forEach(tab => {
        tab.classList.remove('active');
        tab.setAttribute('aria-selected', 'false');
    });
    toolContents.forEach(content => content.classList.remove('active'));
    const targetTab = document.querySelector(`.tool-tab[data-tool="${toolName}"]`);
    const targetContent = document.getElementById(`${toolName}-tool-content`);
    if (targetTab) {
        targetTab.classList.add('active');
        targetTab.setAttribute('aria-selected', 'true');
    }
    if (targetContent)
        targetContent.classList.add('active');
}
function initToolTabs() {
    const toolTabs = document.querySelectorAll('.tool-tab');
    const toolContents = document.querySelectorAll('.tool-content');
    if (toolTabs.length === 0 || toolContents.length === 0) {
        console.error('无法找到工具标签或工具内容');
        return;
    }
    toolTabs.forEach(tab => {
        tab.setAttribute('role', 'tab');
        tab.setAttribute('aria-selected', tab.classList.contains('active') ? 'true' : 'false');
    });
    toolTabs.forEach(tab => {
        tab.addEventListener('click', function () {
            const toolName = this.getAttribute('data-tool');
            switchToolTab(toolName);
        });
    });
    console.log('工具标签页初始化成功');
}
function initSettingsTabs() {
    const settingsTabs = document.querySelectorAll('.settings-tab');
    const settingsContents = document.querySelectorAll('.settings-content');
    if (settingsTabs.length === 0 || settingsContents.length === 0) {
        console.error('无法找到设置标签或设置内容');
        return;
    }
    settingsTabs.forEach(tab => {
        tab.setAttribute('role', 'tab');
        tab.setAttribute('aria-selected', tab.classList.contains('active') ? 'true' : 'false');
    });
    settingsTabs.forEach(tab => {
        tab.addEventListener('click', function () {
            const settingsName = this.getAttribute('data-settings');
            switchSettingsTab(settingsName);
        });
    });
    const temperatureSlider = document.getElementById('temperature');
    const temperatureValue = document.getElementById('temperatureValue');
    if (temperatureSlider && temperatureValue) {
        temperatureSlider.addEventListener('input', function () {
            temperatureValue.textContent = this.value;
        });
    }
    const themeSelect = document.getElementById('themeSelect');
    if (themeSelect) {
        themeSelect.addEventListener('change', async function () {
            const themeValue = this.value;
            const generalConfig = configManager.getConfig('general') || {};
            if (!generalConfig.appearance) {
                generalConfig.appearance = {};
            }
            generalConfig.appearance.theme = themeValue;
            await configManager.saveConfig('general', generalConfig);
            configManager.applyTheme();
        });
    }
    console.log('设置标签页初始化成功');
}
