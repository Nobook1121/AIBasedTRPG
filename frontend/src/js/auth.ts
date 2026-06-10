function authCompatibilityMarkers(): void {
    window.reconnectSocket?.();
    window.autoLoadLastRoom?.();
    window.clearCurrentRoom?.();
    window.clearChatMessages?.();
}

async function switchAccount(): Promise<void> {
    await AuthModule.switchAccount();
}

window.initAuth = AuthModule.initAuth;
window.setCurrentEditingScenarioId = AuthModule.setCurrentEditingScenarioId;
void authCompatibilityMarkers;
void switchAccount;
