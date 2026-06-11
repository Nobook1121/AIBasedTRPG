# Pattern Cyber

## 定位

`pattern_cyber` 是用于 TRPG 工具、调查员档案、规则面板、日志终端等界面的网络主题 UI 样式。整体气质应像“暗网档案库 + 调查终端”，强调可读性、信息密度和可操作性，而不是装饰性科幻海报。

## 视觉关键词

- 暗色终端背景
- 半透明档案面板
- 细网格/扫描线纹理
- 绿色荧光主色
- 蓝色冷光辅助色
- 低饱和文本层级
- 紧凑但不拥挤的信息卡
- 图标化命令按钮

## 色彩规则

主背景使用深青黑或近黑色，避免纯黑：

```css
background:
  linear-gradient(135deg, rgba(8, 19, 25, 0.96), rgba(11, 35, 38, 0.94)),
  radial-gradient(circle at 85% 8%, rgba(37, 170, 121, 0.22), transparent 30%),
  radial-gradient(circle at 12% 88%, rgba(47, 111, 237, 0.18), transparent 34%);
```

主强调色使用荧光绿 `#66e2ad`，用于主按钮、激活态、关键数值和状态标签。辅助冷光蓝可用于进度条渐变或次要状态，不要让界面变成单一蓝紫渐变。

文本建议：

- 主文本：`#e9f7f0`
- 强文本：`#f3fff9`
- 次级文本：`rgba(233, 247, 240, 0.62-0.72)`
- 深底按钮文本：`#061714`

## 背景纹理

使用细网格表达“网络/数据流”，只作为氛围层，不干扰内容阅读。

```css
.character-matrix-bg {
  position: absolute;
  inset: 0;
  pointer-events: none;
  opacity: 0.22;
  background-image:
    linear-gradient(rgba(101, 255, 190, 0.13) 1px, transparent 1px),
    linear-gradient(90deg, rgba(101, 255, 190, 0.13) 1px, transparent 1px);
  background-size: 28px 28px;
  mask-image: linear-gradient(to bottom, black, transparent 92%);
}
```

## 布局模式

推荐采用“左档案列表 + 右详情检查器”的工作台结构：

- 顶部命令区：页面名称、短说明、主要操作按钮。
- 左侧面板：对象列表、筛选器、状态摘要。
- 右侧面板：选中对象详情、规则计算、日志和可执行动作。
- 移动端降为单列，列表和详情顺序保持自然阅读流。

示例网格：

```css
.character-layout {
  display: grid;
  grid-template-columns: minmax(260px, 330px) minmax(0, 1fr);
  gap: 18px;
}
```

## 组件规范

按钮应像终端命令，不像营销 CTA。使用 Font Awesome 或项目现有 icon，按钮包含图标和短文本。

- 主按钮：荧光绿背景、深色文字、轻微光晕。
- 次按钮：透明暗底、绿边、浅色文字。
- 悬停：轻微上移 `translateY(-2px)`，增加边框亮度和光晕。
- 卡片：8px 或更小圆角，半透明暗底，细边框，避免套娃卡片。
- 筛选 pill：小尺寸、明确 active 态，用于技能等级或状态分组。
- 进度条：细条，使用绿到蓝/黄的线性渐变，表达负载或熟练度。

## 信息层级

面板标题使用图标 + 短标签。关键数值单独放入小型 stat card：

- HP / San / MOV / 伤害加值等规则计算值应大号显示。
- STR、CON、SIZ、DEX、INT、POW、AGE 使用等宽或紧凑网格。
- 技能按属性/领域分组，等级以 pill 或 badge 呈现。
- 装备区显示总重量、总体积和负载进度条。
- 伤势与 San 日志按时间倒序，避免长文本压缩主信息。

## 动效规则

动效只服务反馈：

- 页面空状态或终端图标可使用慢速 pulse。
- 卡片和按钮悬停使用 150-200ms 的轻微位移。
- 不使用大面积旋转、弹跳、漂浮装饰物。
- 必须提供 `prefers-reduced-motion` 降级。

```css
@media (prefers-reduced-motion: reduce) {
  .character-command-button,
  .character-card,
  .character-empty-state .fa {
    animation: none;
    transition: none;
  }
}
```

## 可访问性与交互

- 所有图标按钮必须有可见文本或 `title`/`aria-label`。
- 动态详情区域使用 `aria-live="polite"`。
- 筛选按钮使用真实 `button`，不要用纯 `div`。
- 深色背景上的文本对比必须足够，次级文本不要低于约 60% 不透明度。
- 表单标签必须绑定 `for` 和控件 `id`。

## 禁忌

- 不要使用大面积紫蓝渐变。
- 不要使用纯装饰性光球、漂浮圆斑或 bokeh。
- 不要把页面区块做成多层嵌套卡片。
- 不要用过大的 hero 字号占据工具界面。
- 不要让动画影响布局尺寸。
- 不要让文本压进按钮或卡片边界。

## 适用场景

此 pattern 适合：

- COC 调查员角色卡
- 装备与线索档案
- AI 角色配置终端
- 剧本节点/日志审计
- 网络配置与连接状态面板

不适合：

- 营销落地页
- 轻松休闲的小游戏界面
- 需要温暖生活化表达的个人资料页
