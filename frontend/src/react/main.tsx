import { createRoot } from "react-dom/client";
import { flushSync } from "react-dom";
import "./app.css";
import { HomeChat } from "./home/HomeChat";
import { Sidebar } from "./shell/Sidebar";

function ReactRuntimeBridge() {
    return <span hidden data-framework="react" aria-hidden="true" />;
}

const mountNode = document.getElementById("react-runtime-root");
if (mountNode) {
    createRoot(mountNode).render(<ReactRuntimeBridge />);
}

const sidebarMountNode = document.getElementById("react-sidebar-root");
if (sidebarMountNode) {
    const root = createRoot(sidebarMountNode);
    flushSync(() => {
        root.render(<Sidebar />);
    });
}

const homeMountNode = document.getElementById("react-home-root");
if (homeMountNode) {
    const root = createRoot(homeMountNode);
    flushSync(() => {
        root.render(<HomeChat />);
    });
}
