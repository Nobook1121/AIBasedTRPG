import { createRoot } from "react-dom/client";

function ReactRuntimeBridge() {
    return <span hidden data-framework="react" aria-hidden="true" />;
}

const mountNode = document.getElementById("react-runtime-root");
if (mountNode) {
    createRoot(mountNode).render(<ReactRuntimeBridge />);
}
