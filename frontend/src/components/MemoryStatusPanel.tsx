import { useEffect, useState } from "react";
import { getEverMemRuntimeConfig } from "../api";

export default function MemoryStatusPanel() {
    const [config, setConfig] = useState(getEverMemRuntimeConfig());

    useEffect(() => {
        // Simple polling to keep panel somewhat in sync with localStorage changes
        // Alternatively can be driven by a React Context, but polling is lightweight enough for this panel.
        const interval = setInterval(() => {
            const current = getEverMemRuntimeConfig();
            setConfig((prev) => {
                if (
                    prev.enabled !== current.enabled ||
                    prev.temporary_session !== current.temporary_session ||
                    prev.remember_chat !== current.remember_chat ||
                    prev.remember_voice_chat !== current.remember_voice_chat ||
                    prev.remember_recordings !== current.remember_recordings ||
                    prev.remember_podcast !== current.remember_podcast ||
                    prev.remember_tts !== current.remember_tts
                ) {
                    return current;
                }
                return prev;
            });
        }, 1000);
        return () => clearInterval(interval);
    }, []);

    if (!config.enabled) {
        return (
            <div style={{ padding: "12px", background: "var(--surface-color)", borderTop: "1px solid var(--border-color)", fontSize: "12px", color: "var(--text-color-muted)" }}>
                <div style={{ display: "flex", alignItems: "center", gap: 6 }}>
                    <span style={{ display: "inline-block", width: 8, height: 8, borderRadius: "50%", background: "#666" }} />
                    EverMem 已关闭
                </div>
            </div>
        );
    }

    return (
        <div style={{ padding: "12px", background: "var(--surface-color)", borderTop: "1px solid var(--border-color)", fontSize: "12px", color: "var(--text-color)" }}>
            <div style={{ display: "flex", alignItems: "center", gap: 6, marginBottom: 4 }}>
                <span style={{ display: "inline-block", width: 8, height: 8, borderRadius: "50%", background: config.temporary_session ? "#f59e0b" : "#10b981" }} />
                <span style={{ fontWeight: 600 }}>EverMem 记忆中心</span>
            </div>

            <div style={{ color: "var(--text-color-muted)", marginTop: 8 }}>
                {config.temporary_session ? (
                    <span style={{ color: "#f59e0b" }}>当前为「临时会话」模式</span>
                ) : (
                    <div style={{ display: "flex", flexWrap: "wrap", gap: "4px 8px" }}>
                        <span style={{ color: config.remember_chat ? "#10b981" : "#666" }}>Chat: {config.remember_chat ? "ON" : "OFF"}</span>
                        <span style={{ color: config.remember_voice_chat ? "#10b981" : "#666" }}>Voice: {config.remember_voice_chat ? "ON" : "OFF"}</span>
                        <span style={{ color: config.remember_recordings ? "#10b981" : "#666" }}>Transcript: {config.remember_recordings ? "ON" : "OFF"}</span>
                        <span style={{ color: config.remember_podcast ? "#10b981" : "#666" }}>Podcast: {config.remember_podcast ? "ON" : "OFF"}</span>
                        <span style={{ color: config.remember_tts ? "#10b981" : "#666" }}>TTS: {config.remember_tts ? "ON" : "OFF"}</span>
                    </div>
                )}
            </div>
        </div>
    );
}
