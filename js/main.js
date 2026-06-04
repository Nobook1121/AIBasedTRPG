// 主入口文件 - 协调各模块初始化

let toolManager;

document.addEventListener('DOMContentLoaded', async function() {
    toolManager = new ToolManager();

    initTabs();
    initChat();
    initScenarioManagement();
    initCharacterManagement();
    initDiceTool();
    initToolTabs();
    initSettingsTabs();

    await loadAndApplyConfigs();

    initAIPlatforms();
    initAuth();
    initNetworkConfig();
    initSaveManagement();
    initSidebarToggle();

    await autoLoadLastSave();

    document.addEventListener('hidden.bs.modal', function(event) {
        setTimeout(() => {
            const openModals = document.querySelectorAll('.modal.show');
            if (openModals.length === 0) {
                const modalBackdrops = document.querySelectorAll('.modal-backdrop');
                modalBackdrops.forEach(backdrop => backdrop.remove());
                console.log('所有模态框已关闭，已移除所有遮罩层');
            } else {
                console.log('还有其他模态框打开，保留遮罩层');
            }
        }, 100);
    });
});

async function loadAndApplyConfigs() {
    try {
        await configManager.loadConfig('general');
        configManager.applyGeneralSettings();
        configManager.initThemeSystem();
        console.log('配置文件加载和应用完成');
    } catch (error) {
        console.error('加载配置文件时出错:', error);
    }
}

function initCharacterManagement() {
    const createCharacterBtn = document.getElementById('createCharacter');
    const saveCharacterBtn = document.getElementById('saveCharacter');
    const characterModal = new bootstrap.Modal(document.getElementById('characterModal'));
    const characterList = document.getElementById('characterList');

    let characters = [];

    createCharacterBtn.addEventListener('click', function() {
        document.getElementById('characterName').value = '';
        document.getElementById('playerId').value = '';
        document.getElementById('characterBio').value = '';
        document.getElementById('strength').value = '';
        document.getElementById('constitution').value = '';
        document.getElementById('dexterity').value = '';
        document.getElementById('intelligence').value = '';
        document.getElementById('willpower').value = '';
        document.getElementById('luck').value = '';
        document.getElementById('characterSkills').value = '';
        characterModal.show();
    });

    saveCharacterBtn.addEventListener('click', function() {
        const character = {
            id: Date.now(),
            name: document.getElementById('characterName').value,
            playerId: document.getElementById('playerId').value,
            bio: document.getElementById('characterBio').value,
            attributes: {
                strength: document.getElementById('strength').value,
                constitution: document.getElementById('constitution').value,
                dexterity: document.getElementById('dexterity').value,
                intelligence: document.getElementById('intelligence').value,
                willpower: document.getElementById('willpower').value,
                luck: document.getElementById('luck').value
            },
            skills: document.getElementById('characterSkills').value
        };

        characters.push(character);
        updateCharacterList();
        characterModal.hide();
    });

    function updateCharacterList() {
        characterList.innerHTML = '';

        characters.forEach(character => {
            const card = document.createElement('div');
            card.className = 'character-card';
            card.innerHTML = `
                <h5>${character.name}</h5>
                <p>玩家ID: ${character.playerId}</p>
                <p>简介: ${character.bio.substring(0, 50)}${character.bio.length > 50 ? '...' : ''}</p>
                <div class="character-card-actions">
                    <button class="btn btn-sm btn-primary">查看</button>
                    <button class="btn btn-sm btn-secondary">编辑</button>
                    <button class="btn btn-sm btn-danger">删除</button>
                </div>
            `;
            characterList.appendChild(card);
        });
    }

    loadMockCharacters();

    function loadMockCharacters() {
        characters = [
            {
                id: 1,
                name: '侦探',
                playerId: '玩家1',
                bio: '一名经验丰富的侦探，擅长调查和推理。',
                attributes: {
                    strength: 40, constitution: 50, dexterity: 60,
                    intelligence: 80, willpower: 70, luck: 50
                },
                skills: '侦查:70,推理:80,格斗:40'
            },
            {
                id: 2,
                name: '医生',
                playerId: '玩家2',
                bio: '一名专业的医生，擅长治疗和解剖。',
                attributes: {
                    strength: 30, constitution: 60, dexterity: 50,
                    intelligence: 70, willpower: 60, luck: 40
                },
                skills: '医学:80,急救:70,说服:50'
            }
        ];
        updateCharacterList();
    }
}

function initDiceTool() {
    const rollDiceBtn = document.getElementById('rollDice');
    const diceType = document.getElementById('diceType');
    const diceResult = document.getElementById('diceResult');

    rollDiceBtn.addEventListener('click', function() {
        const type = diceType.value;
        const sides = parseInt(type.replace('d', ''));
        const result = Math.floor(Math.random() * sides) + 1;
        diceResult.textContent = `结果: ${result}`;
    });
}

function initSidebarToggle() {
    const toggleBtn = document.getElementById('sidebarToggle');
    const sidebar = document.getElementById('sidebar');
    const mainContent = document.getElementById('mainContent');

    if (!toggleBtn || !sidebar || !mainContent) return;

    toggleBtn.addEventListener('click', function() {
        const isCollapsed = sidebar.classList.contains('sidebar-collapsed');

        if (isCollapsed) {
            sidebar.classList.remove('sidebar-collapsed');
            sidebar.classList.add('sidebar-expanded');
            mainContent.classList.remove('sidebar-collapsed-content');
            toggleBtn.querySelector('i').className = 'fa fa-angle-double-left';
            toggleBtn.title = '收起侧边栏';
            toggleBtn.setAttribute('aria-label', '收起侧边栏');
            toggleBtn.setAttribute('aria-expanded', 'true');
        } else {
            sidebar.classList.remove('sidebar-expanded');
            sidebar.classList.add('sidebar-collapsed');
            mainContent.classList.add('sidebar-collapsed-content');
            toggleBtn.querySelector('i').className = 'fa fa-angle-double-right';
            toggleBtn.title = '展开侧边栏';
            toggleBtn.setAttribute('aria-label', '展开侧边栏');
            toggleBtn.setAttribute('aria-expanded', 'false');
        }
    });
}
