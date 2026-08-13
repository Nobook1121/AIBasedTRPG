interface TrpgTemplateRenderer {
    render(templateId: string, values?: Record<string, unknown>): string;
    escapeHtml(value: unknown): string;
}
