import { useEffect, useState, type FormEvent } from "react";
import { LogOut, Shield, UserRoundPlus, X } from "lucide-react";
import { useI18n } from "../i18n";
import type { AuthRuntimeConfig } from "../api";

type Props = {
  open: boolean;
  auth: AuthRuntimeConfig;
  onClose: () => void;
  onLogin: (email: string, password: string) => Promise<void>;
  onRegister: (email: string, password: string) => Promise<void>;
  onLogout: () => void;
};

export default function AuthDialog({
  open,
  auth,
  onClose,
  onLogin,
  onRegister,
  onLogout,
}: Props) {
  const { t } = useI18n();
  const [mode, setMode] = useState<"login" | "register">("login");
  const [email, setEmail] = useState(auth.userEmail);
  const [password, setPassword] = useState("");
  const [confirmPassword, setConfirmPassword] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");

  useEffect(() => {
    if (!open) {
      return;
    }
    setEmail(auth.userEmail);
    setPassword("");
    setConfirmPassword("");
    setError("");
  }, [auth.userEmail, open]);

  useEffect(() => {
    if (!open || typeof document === "undefined") {
      return;
    }
    const previousOverflow = document.body.style.overflow;
    document.body.style.overflow = "hidden";
    return () => {
      document.body.style.overflow = previousOverflow;
    };
  }, [open]);

  if (!open) {
    return null;
  }

  function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setError("");
    const normalizedEmail = email.trim();
    if (!normalizedEmail) {
      setError(t("请输入邮箱。", "Enter your email."));
      return;
    }
    if (password.length < 6) {
      setError(t("密码至少需要 6 位。", "Password must be at least 6 characters."));
      return;
    }
    if (mode === "register" && password !== confirmPassword) {
      setError(t("两次密码输入不一致。", "Passwords do not match."));
      return;
    }
    const action = mode === "login" ? onLogin : onRegister;
    setBusy(true);
    void action(normalizedEmail, password)
      .then(() => {
        setPassword("");
        setConfirmPassword("");
        setBusy(false);
        onClose();
      })
      .catch((err: unknown) => {
        setError(
          err instanceof Error
            ? err.message
            : t("登录失败，请稍后重试。", "Authentication failed. Try again."),
        );
        setBusy(false);
      });
  }

  return (
    <div className="vsAuthDialogBackdrop" role="presentation" onClick={onClose}>
      <section
        className="vsAuthDialog"
        role="dialog"
        aria-modal="true"
        aria-labelledby="vs-auth-dialog-title"
        onClick={(event) => event.stopPropagation()}
      >
        <div className="vsAuthDialogHeader">
          <div className="vsAuthDialogTitleWrap">
            <span className="vsAuthDialogIcon" aria-hidden="true">
              <Shield size={18} />
            </span>
            <div>
              <h2 id="vs-auth-dialog-title">{t("账号登录", "Account Login")}</h2>
              <p>
                {t(
                  "使用邮箱密码登录本地账户，成功后自动接入当前后端。",
                  "Sign in with email and password and attach the session to the current backend."
                )}
              </p>
            </div>
          </div>
          <button
            type="button"
            className="vsAuthDialogClose"
            onClick={onClose}
            aria-label={t("关闭", "Close")}
          >
            <X size={16} />
          </button>
        </div>

        {auth.userEmail ? (
          <div className="vsAuthSessionCard">
            <div className="vsAuthSessionMeta">
              <span className="vsAuthSessionBadge">
                {auth.isAdmin ? t("管理员", "Admin") : t("已登录", "Signed in")}
              </span>
              <strong>{auth.userEmail}</strong>
              <p>
                {auth.isAdmin
                  ? t("当前账号拥有设置写入权限。", "This account can write settings.")
                  : t("当前账号可以访问受保护写接口。", "This account can access protected write routes.")}
              </p>
            </div>
            <div className="vsAuthDialogActions">
              <button type="button" className="vsBtnSecondary" onClick={onClose}>
                {t("关闭", "Close")}
              </button>
              <button type="button" className="vsBtnPrimary" onClick={onLogout}>
                <LogOut size={14} />
                {t("退出登录", "Log out")}
              </button>
            </div>
          </div>
        ) : (
          <form className="vsAuthDialogForm" onSubmit={handleSubmit}>
            <div className="vsAuthTabs" role="tablist" aria-label={t("账号操作", "Auth actions")}>
              <button
                type="button"
                role="tab"
                aria-selected={mode === "login"}
                className={`vsAuthTab ${mode === "login" ? "active" : ""}`}
                onClick={() => {
                  setMode("login");
                  setError("");
                }}
              >
                {t("登录", "Sign in")}
              </button>
              <button
                type="button"
                role="tab"
                aria-selected={mode === "register"}
                className={`vsAuthTab ${mode === "register" ? "active" : ""}`}
                onClick={() => {
                  setMode("register");
                  setError("");
                }}
              >
                <UserRoundPlus size={14} />
                {t("注册", "Register")}
              </button>
            </div>

            <label className="vsAuthDialogField">
              <span>{t("邮箱", "Email")}</span>
              <input
                type="email"
                autoComplete="email"
                value={email}
                placeholder="name@example.com"
                onChange={(event) => setEmail(event.target.value)}
              />
            </label>

            <label className="vsAuthDialogField">
              <span>{t("密码", "Password")}</span>
              <input
                type="password"
                autoComplete={mode === "login" ? "current-password" : "new-password"}
                value={password}
                placeholder={t("至少 6 位", "At least 6 characters")}
                onChange={(event) => setPassword(event.target.value)}
              />
            </label>

            {mode === "register" ? (
              <label className="vsAuthDialogField">
                <span>{t("确认密码", "Confirm Password")}</span>
                <input
                  type="password"
                  autoComplete="new-password"
                  value={confirmPassword}
                  placeholder={t("再次输入密码", "Repeat your password")}
                  onChange={(event) => setConfirmPassword(event.target.value)}
                />
              </label>
            ) : null}

            <div className="vsAuthDialogHints">
              <p>
                {mode === "register"
                  ? t("首个注册账号会自动成为管理员。", "The first registered account becomes an admin automatically.")
                  : t("登录成功后会自动保存会话，无需再次输入 token。", "Successful sign-in stores the session automatically, without manual token entry.")}
              </p>
              {auth.hasEnvApiToken || auth.hasEnvAdminToken ? (
                <p>
                  {t(
                    "当前构建仍兼容环境变量 token，但用户登录会优先使用当前账号会话。",
                    "This build still supports env tokens, but user login takes priority for the current session.",
                  )}
                </p>
              ) : null}
            </div>

            {error ? <div className="vsAuthDialogError">{error}</div> : null}

            <div className="vsAuthDialogActions">
              <button type="button" className="vsBtnSecondary" onClick={onClose} disabled={busy}>
                {t("取消", "Cancel")}
              </button>
              <button type="submit" className="vsBtnPrimary" disabled={busy}>
                {busy
                  ? t("提交中…", "Submitting…")
                  : mode === "login"
                    ? t("登录", "Sign in")
                    : t("注册并登录", "Register & sign in")}
              </button>
            </div>
          </form>
        )}
      </section>
    </div>
  );
}
