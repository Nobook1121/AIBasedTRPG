namespace AuthModule {
    export function bindFloatingFields(root: ParentNode = document): void {
        root.querySelectorAll<HTMLElement>(".auth-floating-field").forEach((field) => {
            const input = field.querySelector<HTMLInputElement | HTMLTextAreaElement>("input, textarea");
            if (!input) return;
            const update = () => field.classList.toggle("has-value", input.value.trim().length > 0);
            input.addEventListener("input", update);
            input.addEventListener("change", update);
            update();
        });
    }
}
