interface BootstrapModalInstance {
    show(): void;
    hide(): void;
}

interface BootstrapModalConstructor {
    new(element: Element, options?: { backdrop?: boolean | "static" }): BootstrapModalInstance;
    getInstance(element: Element | null): BootstrapModalInstance | null;
}

declare const bootstrap: {
    Modal: BootstrapModalConstructor;
};

interface MarkedParser {
    (content: string, options?: Record<string, unknown>): string;
    parse(content: string): string;
    setOptions(options: Record<string, unknown>): void;
}

declare const marked: MarkedParser;

interface SocketLike {
    connected: boolean;
    on(eventName: string, handler: (payload: unknown) => void): void;
    emit(eventName: string, payload?: unknown): void;
    disconnect(): void;
}

declare function io(options?: Record<string, unknown>): SocketLike;
