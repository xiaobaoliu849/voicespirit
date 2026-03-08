import {
  SIDEBAR_ITEMS,
  type ActiveTab,
  type HistoryItem
} from "../appConfig";

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
  return (
    <aside className="vsSidebar">
      <div className="vsBrand">
        <div className="vsBrandIcon">VS</div>
        <h1>VoiceSpirit</h1>
      </div>

      <div className="vsSidebarAction">
        <button
          type="button"
          className="vsNewChatBtn"
          onClick={onNewChatSession}
        >
          + 新建对话
        </button>
      </div>

      <section className="vsSidebarSection">
        <p className="vsSectionLabel">工作台</p>
        <nav className="vsNav">
          {SIDEBAR_ITEMS.map((item) => (
            <button
              key={item.tab}
              type="button"
              className={activeTab === item.tab ? "vsNavItem active" : "vsNavItem"}
              onClick={() => onTabChange(item.tab)}
            >
              <span className="vsNavIcon" aria-hidden="true">
                {item.icon}
              </span>
              <span>{item.label}</span>
            </button>
          ))}
        </nav>
      </section>

      <section className="vsSidebarSection vsHistorySection">
        <div className="vsHistoryHead">
          <p className="vsSectionLabel">最近对话</p>
          <button
            type="button"
            className="vsHistoryClearBtn"
            onClick={onNewChatSession}
          >
            清除全部
          </button>
        </div>
        <div className="vsHistoryList">
          {chatHistoryItems.map((item) => (
            <button
              key={item.id}
              type="button"
              className="vsHistoryItem"
              onClick={() => onHistorySelect(item.content)}
            >
              {item.content}
            </button>
          ))}
          {!chatHistoryItems.length ? (
            <p className="vsHistoryEmpty">暂无历史会话</p>
          ) : null}
        </div>
      </section>

      <div className="vsProfileCard">
        <div className="vsProfileAvatar">A</div>
        <div>
          <p className="vsProfileName">本地工作区</p>
          <p className="vsProfilePlan">当前会话环境</p>
        </div>
      </div>
    </aside>
  );
}
