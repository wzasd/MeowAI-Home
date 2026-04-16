import { useState } from "react";
import { useAuthStore } from "../../stores/authStore";
import { Loader2 } from "lucide-react";

export function LoginModal() {
  const [isRegister, setIsRegister] = useState(false);
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [role, setRole] = useState("member");

  const login = useAuthStore((s) => s.login);
  const register = useAuthStore((s) => s.register);
  const isLoading = useAuthStore((s) => s.isLoading);
  const error = useAuthStore((s) => s.error);
  const clearError = useAuthStore((s) => s.clearError);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    clearError();
    if (isRegister) {
      const ok = await register(username, password, role);
      if (ok) {
        setIsRegister(false);
      }
    } else {
      await login(username, password);
    }
  };

  return (
    <div className="flex h-full w-full items-center justify-center bg-black/80 p-4">
      <div className="relative w-full max-w-sm rounded-xl border border-gray-300 bg-white p-6 shadow-2xl">
        <div className="mb-6 text-center">
          <div className="mb-2 text-4xl">🐱</div>
          <h2 className="text-xl font-bold text-gray-900">
            {isRegister ? "注册账号" : "登录 MeowAI"}
          </h2>
          <p className="text-sm text-gray-600">
            {isRegister ? "创建新账号以开始使用" : "登录以继续与猫咪协作"}
          </p>
        </div>

        <form onSubmit={handleSubmit} className="space-y-4">
          <div>
            <label className="mb-1 block text-sm font-medium text-gray-700">
              用户名
            </label>
            <input
              type="text"
              value={username}
              onChange={(e) => setUsername(e.target.value)}
              required
              minLength={3}
              className="w-full rounded-lg border border-gray-300 bg-white px-3 py-2 text-sm text-gray-900 focus:border-blue-500 focus:outline-none"
              placeholder="输入用户名"
            />
          </div>

          <div>
            <label className="mb-1 block text-sm font-medium text-gray-700">
              密码
            </label>
            <input
              type="password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              required
              minLength={6}
              className="w-full rounded-lg border border-gray-300 bg-white px-3 py-2 text-sm text-gray-900 focus:border-blue-500 focus:outline-none"
              placeholder="输入密码"
            />
          </div>

          {isRegister && (
            <div>
              <label className="mb-1 block text-sm font-medium text-gray-700">
                角色
              </label>
              <select
                value={role}
                onChange={(e) => setRole(e.target.value)}
                className="w-full rounded-lg border border-gray-300 bg-white px-3 py-2 text-sm text-gray-900 focus:border-blue-500 focus:outline-none"
              >
                <option value="member">成员</option>
                <option value="admin">管理员</option>
                <option value="viewer">访客</option>
              </select>
            </div>
          )}

          {error && (
            <div className="rounded-lg bg-red-50 px-3 py-2 text-sm text-red-600">
              {error}
            </div>
          )}

          <button
            type="submit"
            disabled={isLoading || !username.trim() || !password.trim()}
            className="flex w-full items-center justify-center rounded-lg bg-blue-600 px-4 py-2 text-sm font-medium text-white hover:bg-blue-700 disabled:cursor-not-allowed disabled:opacity-50"
          >
            {isLoading ? (
              <>
                <Loader2 size={16} className="mr-2 animate-spin" />
                处理中...
              </>
            ) : isRegister ? (
              "注册"
            ) : (
              "登录"
            )}
          </button>
        </form>

        <div className="mt-4 text-center">
          <button
            type="button"
            onClick={() => {
              setIsRegister(!isRegister);
              clearError();
            }}
            className="text-sm text-blue-600 hover:text-blue-700"
          >
            {isRegister ? "已有账号？去登录" : "没有账号？去注册"}
          </button>
        </div>
      </div>
    </div>
  );
}
