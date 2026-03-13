import { useState, useEffect } from "react";
import {
  getSidebarItems,
  type ActiveTab,
  type HistoryItem
} from "../appConfig";
import { useI18n } from "../i18n";
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
  MessageSquare,
  X
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
  onHistorySelect: (id: string) => void;
  onClearHistory: () => void;
  onDeleteHistoryItem: (id: string) => void;
};

export default function AppSidebar({
  activeTab,
  chatHistoryItems,
  onTabChange,
  onNewChatSession,
  onHistorySelect,
  onClearHistory,
  onDeleteHistoryItem,
}: Props) {
  const { t } = useI18n();
  const [isCollapsed, setIsCollapsed] = useState(() => {
    const saved = localStorage.getItem("vs_sidebar_collapsed");
    return saved === "true";
  });
  const navigationItems = getSidebarItems(t);
  const hasHistoryItems = chatHistoryItems.length > 0;

  useEffect(() => {
    localStorage.setItem("vs_sidebar_collapsed", String(isCollapsed));
  }, [isCollapsed]);

  return (
    <aside className={`vsSidebar ${isCollapsed ? "collapsed" : ""}`}>
      <div className="vsSidebarHeader">
        <div className="vsBrand">
          <div className="vsBrandIcon">VS</div>
          <div className="vsBrandCopy">
            <h1>VoiceSpirit</h1>
          </div>
        </div>
        <button
          className="vsCollapseBtn"
          onClick={() => setIsCollapsed(!isCollapsed)}
          title={isCollapsed ? t("展开侧边栏", "Expand sidebar") : t("收起侧边栏", "Collapse sidebar")}
        >
          {isCollapsed ? <ChevronRight size={18} /> : <ChevronLeft size={18} />}
        </button>
      </div>

      <div className="vsSidebarTop">
        <div className="vsSidebarAction">
          <button
            type="button"
            className="vsNewChatBtn"
            onClick={onNewChatSession}
            title={isCollapsed ? t("新建对话", "New chat") : undefined}
          >
            <span className="vsNewChatIcon">
              <MessageSquarePlus size={18} />
            </span>
            <span className="vsNewChatText">{t("新建对话", "New chat")}</span>
          </button>
        </div>
      </div>

      <div className="vsSidebarBody">
        <div className="vsSidebarNavScroll custom-scrollbar">
          <div className="vsSidebarSectionHead">
            <p className="vsSectionLabel">{t("工作流", "Workflows")}</p>
          </div>
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
        </div>

        {hasHistoryItems ? (
          <section className="vsSidebarSection vsHistorySection">
            <div className="vsHistoryHead">
              <p className="vsSectionLabel">{t("最近对话", "Recent chats")}</p>
              <button
                type="button"
                className="vsHistoryClearBtn"
                onClick={onClearHistory}
                title={isCollapsed ? t("清除全部对话", "Clear all chats") : undefined}
              >
                {isCollapsed ? "✕" : t("清除全部", "Clear all")}
              </button>
            </div>
            <div className="vsHistoryList custom-scrollbar">
              {chatHistoryItems.map((item) => (
                <div key={item.id} className="vsHistoryRow">
                  <button
                    type="button"
                    className="vsHistoryItem"
                    onClick={() => onHistorySelect(item.id)}
                    title={isCollapsed ? item.content : undefined}
                  >
                    <span className="vsHistoryIcon">
                      <MessageSquare size={16} />
                    </span>
                    <span className="vsHistoryText">{item.content}</span>
                  </button>
                  <button
                    type="button"
                    className="vsHistoryDeleteBtn"
                    aria-label={t(`删除历史 ${item.content}`, `Delete history ${item.content}`)}
                    title={t("删除这条历史", "Delete this history item")}
                    onClick={() => onDeleteHistoryItem(item.id)}
                  >
                    <X size={14} />
                  </button>
                </div>
              ))}
            </div>
          </section>
        ) : null}
      </div>

      <div className="vsSidebarFooter">
        <div className="vsSidebarFooterActions">
          {/* Mock Login Button - Positioned above Settings */}
          <button
            className="vsFooterAction vsLoginBtn"
            title={t("登录账号", "Login")}
            onClick={() => { }}
          >
            <Fingerprint size={18} />
            {!isCollapsed && <span>{t("登录账号", "Login")}</span>}
          </button>

          {/* Settings Button */}
          <button
            className={`vsFooterAction vsSettingsBtn ${activeTab === "settings" ? "active" : ""}`}
            title={t("设置", "Settings")}
            onClick={() => onTabChange("settings")}
          >
            <Settings size={18} />
            {!isCollapsed && <span>{t("设置", "Settings")}</span>}
          </button>
        </div>
        <div className="vsMemoryStatusWrapper">
          <MemoryStatusPanel />
        </div>
      </div>
    </aside>
  );
}
