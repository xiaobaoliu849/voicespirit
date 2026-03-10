import { useState, useEffect } from "react";
import {
  SIDEBAR_ITEMS,
  type ActiveTab,
  type HistoryItem
} from "../appConfig";
import MemoryStatusPanel from "./MemoryStatusPanel";
import {
  Bot,
  Languages,
  Volume2,
  Settings2,
  Fingerprint,
  Mic2,
  FileAudio,
  Settings,
  ChevronLeft,
  ChevronRight,
  MessageSquarePlus,
  MessageSquare
} from "lucide-react";

const IconMap: Record<string, React.ElementType> = {
  Bot,
  Languages,
  Volume2,
  Settings2,
  Fingerprint,
  Mic2,
  FileAudio,
  Settings
};

type Props = {
  activeTab: ActiveTab;
  chatHistoryItems: HistoryItem[];
  onTabChange: (tab: ActiveTab) => void;
  onNewChatSession: () => void;
  onHistorySelect: (content: string) => void;
};

export default function AppSidebar({
  activeTab,
  chatHistoryItems,
  onTabChange,
  onNewChatSession,
  onHistorySelect
}: Props) {
  const [isCollapsed, setIsCollapsed] = useState(() => {
    const saved = localStorage.getItem("vs_sidebar_collapsed");
    return saved === "true";
  });
  const navigationItems = SIDEBAR_ITEMS.filter((item) => item.tab !== "chat");
  const hasHistoryItems = chatHistoryItems.length > 0;

  useEffect(() => {
    localStorage.setItem("vs_sidebar_collapsed", String(isCollapsed));
  }, [isCollapsed]);

  return (
    <aside className={`vsSidebar ${isCollapsed ? "collapsed" : ""}`}>
      {/* ── Header ── */}
      <div className="vsSidebarHeader">
        <button
          className="vsCollapseBtn"
          onClick={() => setIsCollapsed(!isCollapsed)}
          title={isCollapsed ? "展开侧边栏" : "收起侧边栏"}
        >
          {isCollapsed ? <ChevronRight size={18} /> : <ChevronLeft size={18} />}
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
          <span className="vsNewChatIcon">
            <MessageSquarePlus size={18} />
          </span>
          <span className="vsNewChatText">新建对话</span>
        </button>
      </div>

      {/* ── Navigation ── */}
      <div className="vsSidebarNavScroll custom-scrollbar">
        <nav className="vsNav vsSidebarMainNav">
          {navigationItems.map((item) => {
            const IconComponent = IconMap[item.icon];
            return (
              <button
                key={item.tab}
                type="button"
                className={`vsNavItem ${activeTab === item.tab ? "active" : ""}`}
                onClick={() => onTabChange(item.tab as ActiveTab)}
                title={isCollapsed ? item.tooltip || item.label : undefined}
                data-testid={`nav-${item.tab}`}
              >
                <span className="vsNavIcon" aria-hidden="true">
                  {IconComponent && <IconComponent size={20} />}
                </span>
                <span className="vsNavItemText">{item.label}</span>
                {activeTab === item.tab ? (
                  <div className="vsNavActiveIndicator" />
                ) : null}
              </button>
            );
          })}
        </nav>

        {hasHistoryItems ? (
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
                  <span className="vsHistoryIcon">
                    <MessageSquare size={16} />
                  </span>
                  <span className="vsHistoryText">{item.content}</span>
                </button>
              ))}
            </div>
          </section>
        ) : null}
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
