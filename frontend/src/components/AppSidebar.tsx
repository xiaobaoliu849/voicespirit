import { useState } from "react";
import {
  SIDEBAR_ITEMS,
  type ActiveTab,
  type HistoryItem
} from "../appConfig";
import MemoryStatusPanel from "./MemoryStatusPanel";

type Props = {
  activeTab: ActiveTab;
  chatHistoryItems: HistoryItem[];
  onTabChange: (tab: ActiveTab) => void;
  onNewChatSession: () => void;
  onHistorySelect: (content: string) => void;
};

// Define logical groupings for the tabs based on vocabbook-modern's approach.
const TAB_GROUPS = [
  {
    title: "AI 助理",
    keys: ["chat", "translate"]
  },
  {
    title: "声音引擎",
    keys: ["tts", "voice_design", "voice_clone"]
  },
  {
    title: "音频创作",
    keys: ["audio_overview", "transcription"]
  },
  {
    title: "系统",
    keys: ["settings"]
  }
];

export default function AppSidebar({
  activeTab,
  chatHistoryItems,
  onTabChange,
  onNewChatSession,
  onHistorySelect
}: Props) {
  const [isCollapsed, setIsCollapsed] = useState(false);

  return (
    <aside className={`vsSidebar ${isCollapsed ? "collapsed" : ""}`}>
      {/* ── Header ── */}
      <div className="vsSidebarHeader">
        <button
          className="vsCollapseBtn"
          onClick={() => setIsCollapsed(!isCollapsed)}
          title={isCollapsed ? "展开侧边栏" : "收起侧边栏"}
        >
          {isCollapsed ? "›" : "‹"}
        </button>
        <div className="vsBrand">
          <div className="vsBrandIcon">VS</div>
          <h1>VoiceSpirit</h1>
        </div>
      </div>

      {/* ── Main Actions ── */}
      <div className="vsSidebarAction">
        <button
          type="button"
          className="vsNewChatBtn"
          onClick={onNewChatSession}
          title={isCollapsed ? "新建对话" : undefined}
        >
          <span className="vsNewChatIcon">+</span>
          <span className="vsNewChatText">新建对话</span>
        </button>
      </div>

      {/* ── Navigation Groups ── */}
      <div className="vsSidebarNavScroll custom-scrollbar">
        {TAB_GROUPS.map((group) => {
          // Filter actual items matching the group keys
          const items = SIDEBAR_ITEMS.filter((item) => group.keys.includes(item.tab));
          if (items.length === 0) return null;

          return (
            <section className="vsSidebarSection" key={group.title}>
              <p className="vsSectionLabel">{group.title}</p>
              <nav className="vsNav">
                {items.map((item) => (
                  <button
                    key={item.tab}
                    type="button"
                    className={`vsNavItem ${activeTab === item.tab ? "active" : ""}`}
                    onClick={() => onTabChange(item.tab)}
                    title={isCollapsed ? item.label : undefined}
                    data-testid={`nav-${item.tab}`}
                  >
                    <span className="vsNavIcon" aria-hidden="true">
                      {item.icon}
                    </span>
                    <span className="vsNavItemText">{item.label}</span>
                  </button>
                ))}
              </nav>
            </section>
          );
        })}

        {/* ── Chat History (Only visible in chat tab intuitively, but kept here for app context) ── */}
        <section className="vsSidebarSection vsHistorySection">
          <div className="vsHistoryHead">
            <p className="vsSectionLabel">最近对话</p>
            <button
              type="button"
              className="vsHistoryClearBtn"
              onClick={onNewChatSession}
              title={isCollapsed ? "清除全部对话" : undefined}
            >
              {isCollapsed ? "✕" : "清除全部"}
            </button>
          </div>
          <div className="vsHistoryList">
            {chatHistoryItems.map((item) => (
              <button
                key={item.id}
                type="button"
                className="vsHistoryItem"
                onClick={() => onHistorySelect(item.content)}
                title={isCollapsed ? item.content : undefined}
              >
                <span className="vsHistoryIcon">💬</span>
                <span className="vsHistoryText">{item.content}</span>
              </button>
            ))}
            {!chatHistoryItems.length ? (
              <p className="vsHistoryEmpty">{isCollapsed ? "空" : "暂无历史会话"}</p>
            ) : null}
          </div>
        </section>
      </div>

      {/* ── Footer ── */}
      <div className="vsSidebarFooter">
        <div className="vsProfileCard">
          <div className="vsProfileAvatar">A</div>
          <div className="vsProfileInfo">
            <p className="vsProfileName">本地工作区</p>
            <p className="vsProfilePlan">当前会话环境</p>
          </div>
        </div>
        <div className="vsMemoryStatusWrapper">
          <MemoryStatusPanel />
        </div>
      </div>
    </aside>
  );
}
