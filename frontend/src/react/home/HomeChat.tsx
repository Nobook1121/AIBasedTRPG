export function HomeChat() {
    return (
        <>
            <header className="page-command-header chat-command-header" data-page-header="chat">
                <div>
                    <h2 id="homeRoomTitle" data-i18n="home.not_joined" data-i18n-dynamic="true">未加入房间</h2>
                    <p className="home-room-meta" id="homeRoomOnlineCount" data-i18n="room.status.online_players" data-i18n-dynamic="true">在线玩家 0/0</p>
                </div>
                <button className="btn btn-primary" id="startRoomGame" type="button" hidden>开始游戏</button>
            </header>

            <div className="save-status-bar" id="saveStatusBar" style={{ display: "none" }} aria-live="polite">
                <div className="save-status-content">
                    <span className="save-status-pill">
                        <i className="fa fa-comments-o" aria-hidden="true" />
                        <span className="save-status-label" data-i18n="room.status.current_room">
                            当前房间
                        </span>
                        <strong className="save-status-name" id="saveStatusName" data-i18n="room.status.not_joined" data-i18n-dynamic="true">
                            未加入
                        </strong>
                    </span>
                    <span className="save-status-script">
                        <i className="fa fa-book" aria-hidden="true" />
                        <span data-i18n="room.status.scenario">剧本</span>
                        <strong id="saveStatusScenario">-</strong>
                    </span>
                </div>
            </div>

            <div className="chat-history" id="chatHistory">
                <div className="welcome-text" data-i18n="home.welcome">欢迎来到 AI TRPG 系统，请选择一个剧本开始游戏。</div>
            </div>

            <div className="chat-input p-3 border-top">
                <div className="input-group">
                    <input
                        type="text"
                        className="form-control"
                        id="chatInput"
                        placeholder="加入房间后可发送消息，使用 @KP 呼叫 AI"
                        data-i18n-placeholder="chat.placeholder.room_required"
                    />
                    <button className="btn btn-primary" id="sendButton" type="button">
                        <i className="fa fa-paper-plane" aria-hidden="true" />{" "}
                        <span data-i18n="chat.action.send">发送</span>
                    </button>
                </div>
            </div>
        </>
    );
}
