/**
 * 赛博档案主题的背景动画层：低密度“矩阵字母雨”。
 *
 * 设计约束：
 * - 仅作为背景层存在（`z-index: -1`、`pointer-events: none`），不影响任何既有功能与交互。
 * - 只在 `body.theme-cyber-2` 下运行；切换主题后由 MutationObserver 自动启停。
 * - 字符池由数字、大小写英文字母与少量特殊符号混合，避免只有 “0/1” 的单调观感。
 * - 密度、速度、字符变化快慢由下方常量集中控制。
 * - 用户开启“减少动态效果”时完全停用，改为静态网格。
 */
namespace ThemeMatrixRain {
    interface Drop {
        x: number;
        y: number;
        speed: number;
        trail: number;
        glyphs: string[];
        lastGlyphY: number;
    }

    const CANVAS_CLASS = "theme-matrix-rain";
    const THEME_CLASS = "theme-cyber-2";

    /** 列间距（px）：值越小越密，是控制密度的主要参数。 */
    const COLUMN_SPACING = 34;
    /** 有字符下落的列占比。 */
    const ACTIVE_COLUMN_RATIO = 0.95;
    const FONT_SIZE = 15;
    /** 拖尾长度（字符数）：值越大，落下的字符串越长。 */
    const MIN_TRAIL = 16;
    const MAX_TRAIL = 30;
    /** 下落速度（px/秒）。 */
    const MIN_SPEED = 42;
    const MAX_SPEED = 104;
    /** 字符变化步长（px）：头部每前进这么远换一次字符，值越小字符变化越快。 */
    const GLYPH_STEP = FONT_SIZE * 0.3;
    /** 帧间隔（ms）：约 30fps，速度较快时保证运动足够顺滑。 */
    const FRAME_INTERVAL = 34;
    const HEAD_COLOR = "rgba(202, 255, 228, 0.9)";
    const TRAIL_RGB = "102, 226, 173";

    let canvas: HTMLCanvasElement | null = null;
    let ctx: CanvasRenderingContext2D | null = null;
    let drops: Drop[] = [];
    let frameHandle: number | null = null;
    let lastFrameAt = 0;
    let lastFrameTime = 0;
    let resizeTimer: number | null = null;
    let viewWidth = 0;
    let viewHeight = 0;

    function prefersReducedMotion(): boolean {
        return window.matchMedia("(prefers-reduced-motion: reduce)").matches;
    }

    function shouldAnimate(): boolean {
        return document.body.classList.contains(THEME_CLASS) && !prefersReducedMotion();
    }

    /** 字符池：数字、大写字母、小写字母、特殊符号，按权重混合，保证多样性又不失“矩阵”观感。 */
    const GLYPH_DIGITS = "01";
    const GLYPH_UPPER = "ABCDEFGHIJKLMNOPQRSTUVWXYZ";
    const GLYPH_LOWER = "abcdefghijklmnopqrstuvwxyz";
    const GLYPH_SYMBOLS = "#@%&*!?";

    const GLYPH_POOLS: ReadonlyArray<{ pool: string; weight: number }> = [
        { pool: GLYPH_DIGITS, weight: 0.4 },
        { pool: GLYPH_UPPER, weight: 0.22 },
        { pool: GLYPH_LOWER, weight: 0.22 },
        { pool: GLYPH_SYMBOLS, weight: 0.16 },
    ];

    function pickFrom(pool: string): string {
        return pool.charAt(Math.floor(Math.random() * pool.length));
    }

    function randomGlyph(): string {
        let roll = Math.random();
        for (const entry of GLYPH_POOLS) {
            if (roll < entry.weight) {
                return pickFrom(entry.pool);
            }
            roll -= entry.weight;
        }
        return pickFrom(GLYPH_DIGITS);
    }

    function createDrop(x: number, height: number, initial: boolean): Drop {
        const trail = MIN_TRAIL + Math.floor(Math.random() * (MAX_TRAIL - MIN_TRAIL + 1));
        const y = initial ? -Math.random() * height : -Math.random() * FONT_SIZE * MAX_TRAIL;
        const glyphs: string[] = [];
        for (let index = 0; index < trail; index += 1) {
            glyphs.push(randomGlyph());
        }
        return {
            x,
            y,
            speed: MIN_SPEED + Math.random() * (MAX_SPEED - MIN_SPEED),
            trail,
            glyphs,
            lastGlyphY: y,
        };
    }

    function buildDrops(width: number, height: number): void {
        drops = [];
        for (let x = COLUMN_SPACING; x < width; x += COLUMN_SPACING) {
            if (Math.random() > ACTIVE_COLUMN_RATIO) {
                continue;
            }
            drops.push(createDrop(x, height, true));
        }
    }

    function resizeCanvas(): void {
        if (!canvas || !ctx) return;
        const dpr = Math.min(window.devicePixelRatio || 1, 2);
        viewWidth = window.innerWidth;
        viewHeight = window.innerHeight;
        canvas.width = Math.max(1, Math.round(viewWidth * dpr));
        canvas.height = Math.max(1, Math.round(viewHeight * dpr));
        ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
        ctx.textBaseline = "top";
        ctx.font = `${FONT_SIZE}px "Cascadia Mono", "SFMono-Regular", Consolas, monospace`;
        buildDrops(viewWidth, viewHeight);
    }

    function render(deltaSeconds: number): void {
        if (!ctx) return;
        ctx.clearRect(0, 0, viewWidth, viewHeight);

        for (const drop of drops) {
            drop.y += drop.speed * deltaSeconds;

            if (drop.y - drop.lastGlyphY >= GLYPH_STEP) {
                drop.lastGlyphY = drop.y;
                drop.glyphs.unshift(randomGlyph());
                drop.glyphs.length = drop.trail;
            }

            const head = drop.glyphs[0] ?? "0";
            ctx.fillStyle = HEAD_COLOR;
            ctx.fillText(head, drop.x, drop.y);

            for (let index = 1; index < drop.glyphs.length; index += 1) {
                const glyph = drop.glyphs[index];
                if (glyph === undefined) continue;
                const y = drop.y - index * FONT_SIZE;
                if (y < -FONT_SIZE || y > viewHeight + FONT_SIZE) continue;
                const fade = 1 - index / drop.glyphs.length;
                ctx.fillStyle = `rgba(${TRAIL_RGB}, ${(fade * fade * 0.58).toFixed(3)})`;
                ctx.fillText(glyph, drop.x, y);
            }

            if (drop.y - drop.trail * FONT_SIZE > viewHeight) {
                Object.assign(drop, createDrop(drop.x, viewHeight, false));
            }
        }
    }

    function loop(timestamp: number): void {
        frameHandle = window.requestAnimationFrame(loop);
        if (!ctx) return;
        if (timestamp - lastFrameAt < FRAME_INTERVAL) return;

        const previous = lastFrameTime === 0 ? timestamp : lastFrameTime;
        const deltaSeconds = Math.min((timestamp - previous) / 1000, 0.12);
        lastFrameAt = timestamp;
        lastFrameTime = timestamp;
        render(deltaSeconds);
    }

    function start(): void {
        if (frameHandle !== null || !canvas || !ctx) return;
        lastFrameAt = 0;
        lastFrameTime = 0;
        frameHandle = window.requestAnimationFrame(loop);
    }

    function stop(): void {
        if (frameHandle !== null) {
            window.cancelAnimationFrame(frameHandle);
            frameHandle = null;
        }
        if (ctx) {
            ctx.clearRect(0, 0, viewWidth, viewHeight);
        }
    }

    function syncState(): void {
        if (shouldAnimate()) {
            resizeCanvas();
            start();
        } else {
            stop();
        }
    }

    function handleResize(): void {
        if (resizeTimer !== null) {
            window.clearTimeout(resizeTimer);
        }
        resizeTimer = window.setTimeout(() => {
            resizeTimer = null;
            if (shouldAnimate()) {
                resizeCanvas();
            }
        }, 200);
    }

    function observe(): void {
        const observer = new MutationObserver(syncState);
        observer.observe(document.body, { attributes: true, attributeFilter: ["class"] });

        const motionQuery = window.matchMedia("(prefers-reduced-motion: reduce)");
        // 旧版 Safari 的 MediaQueryList 没有 addEventListener，缺了它会抛错并中断后续绑定
        if (typeof motionQuery.addEventListener === "function") {
            motionQuery.addEventListener("change", syncState);
        }

        window.addEventListener("resize", handleResize);
        // 主题类由异步配置加载流程挂到 body 上，可能晚于本脚本执行；window.load 时再兜底同步一次
        window.addEventListener("load", syncState, { once: true });
    }

    export function init(): void {
        if (canvas) return;
        const element = document.createElement("canvas");
        element.className = CANVAS_CLASS;
        element.setAttribute("aria-hidden", "true");
        document.body.appendChild(element);
        canvas = element;
        ctx = element.getContext("2d");
        resizeCanvas();
        observe();
        syncState();
    }
}

if (document.body) {
    ThemeMatrixRain.init();
} else {
    document.addEventListener("DOMContentLoaded", () => ThemeMatrixRain.init(), { once: true });
}