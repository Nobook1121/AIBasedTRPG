interface NavLinkItem {
    href: string;
    tab: string;
    label: string;
    active?: boolean;
}

interface NavGroup {
    label: string;
    links: NavLinkItem[];
}

const primaryLinks: NavLinkItem[] = [
    { href: "#home", tab: "home", label: "主页", active: true },
    { href: "#scenario", tab: "scenario", label: "剧本管理" },
    { href: "#character", tab: "character", label: "角色卡管理" },
    { href: "#save", tab: "save", label: "房间管理" },
];

const groupedLinks: NavGroup[] = [
    {
        label: "小工具",
        links: [
            { href: "#tools-dice", tab: "tools", label: "骰子工具" },
            { href: "#tools-other", tab: "tools", label: "其他工具" },
        ],
    },
    {
        label: "设置",
        links: [
            { href: "#settings-general", tab: "settings", label: "常规设置" },
            { href: "#settings-model", tab: "settings", label: "模型设置" },
            { href: "#settings-network", tab: "settings", label: "网络配置" },
            { href: "#settings-about", tab: "settings", label: "关于应用" },
        ],
    },
];

function NavLink({ href, tab, label, active = false }: NavLinkItem) {
    return (
        <a className={`nav-link${active ? " active" : ""}`} href={href} data-tab={tab}>
            {label}
        </a>
    );
}

function NavGroupSection({ group }: { group: NavGroup }) {
    return (
        <li className="nav-item">
            <button className="dropdown-btn" type="button">
                {group.label}
                <i className="fa fa-caret-down" aria-hidden="true" />
            </button>
            <div className="dropdown-container">
                {group.links.map((link) => (
                    <NavLink key={link.href} {...link} />
                ))}
            </div>
        </li>
    );
}

export function Sidebar() {
    return (
        <div className="col-2 bg-dark text-white sidebar-expanded" id="sidebar">
            <div className="d-flex flex-column h-100 p-3">
                <div className="sidebar-header">
                    <h2 className="sidebar-title" data-i18n="app.title">
                        AI TRPG
                    </h2>
                    <button
                        type="button"
                        className="sidebar-toggle"
                        id="sidebarToggle"
                        title="收起侧边栏"
                        aria-label="收起侧边栏"
                        aria-expanded="true"
                    >
                        <i className="fa fa-angle-double-left" aria-hidden="true" />
                    </button>
                </div>
                <ul className="nav flex-column mt-4">
                    {primaryLinks.map((link) => (
                        <li className="nav-item" key={link.href}>
                            <NavLink {...link} />
                        </li>
                    ))}
                    {groupedLinks.map((group) => (
                        <NavGroupSection key={group.label} group={group} />
                    ))}
                </ul>
                <div className="user-info mt-auto" id="userInfo" role="button" tabIndex={0} aria-label="打开用户设置">
                    <div className="user-avatar" id="userAvatar">
                        <img src="https://via.placeholder.com/40" alt="用户头像" width="40" height="40" />
                    </div>
                    <div className="user-details">
                        <div className="user-name" id="userName" data-i18n="auth.status.guest">
                            未登录
                        </div>
                    </div>
                </div>
            </div>
        </div>
    );
}
