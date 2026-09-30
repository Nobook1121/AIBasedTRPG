interface RoomMember {
    user_id?: string | number;
    username?: string;
    role?: string;
    room_role?: "owner" | "admin" | "member";
    status?: "active" | "removed";
    is_active?: boolean;
    permission_label?: string;
    character_card?: Partial<COC7CharacterCard>;
    character_state?: CharacterRuntimeState;
    is_online?: boolean;
}

interface CharacterRuntimeRecord {
    id: string;
    type: "damage" | "san";
    value: number;
    reason: string;
    created_at?: string;
    created_by?: string | number;
}

interface CharacterRuntimeState {
    current_hp?: number;
    max_hp?: number;
    current_san?: number;
    max_san?: number;
    injury_records?: CharacterRuntimeRecord[];
    sanity_records?: CharacterRuntimeRecord[];
    records?: CharacterRuntimeRecord[];
}

interface Room {
    id: string;
    code?: string;
    room_code?: string;
    name: string;
    created_at?: string;
    creator_id?: string | number;
    owner_id?: string | number;
    scenario_id?: number;
    scenario_title?: string;
    scenario_started_at?: string;
    scenario_started_by?: string | number;
    invisible_view?: boolean;
    archived?: boolean;
    completed_at?: string;
    archived_at?: string;
    members?: RoomMember[];
    messages?: ChatMessage[];
    ai_history?: ChatMessage[];
    house_rules?: RoomHouseRules;
    saves?: Array<{ filename: string; title?: string; created_at?: string }>;
}

interface RoomHouseRules {
    action_suggestions_enabled?: boolean;
}

interface ChatMessage {
    id?: string;
    role?: string;
    type?: string;
    content: string;
    sender?: string;
    sender_id?: string | number | null;
    sender_name?: string;
    senderName?: string;
    avatar?: string;
    timestamp?: string;
    time?: string;
    processing_time?: number;
    token_count?: number;
    metadata?: Record<string, unknown>;
}

interface CharacterRecordPayload extends Record<string, unknown> {
    roomId?: string;
    roomName?: string;
    username?: string;
    type?: "damage" | "san";
    value?: number;
    reason?: string;
}
