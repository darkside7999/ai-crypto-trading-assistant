import { LockKeyhole } from "lucide-react";
import { useState } from "react";

import { api, setToken } from "../services/api";

export default function LoginPage({ onLogin }) {
  const [username, setUsername] = useState("admin");
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");

  async function submit(event) {
    event.preventDefault();
    setError("");
    try {
      const data = await api.login(username, password);
      setToken(data.access_token);
      onLogin();
    } catch (err) {
      setError(err.message);
    }
  }

  return (
    <main className="flex min-h-screen items-center justify-center bg-mist px-4">
      <form onSubmit={submit} className="w-full max-w-sm border border-slate-200 bg-white p-6 shadow-sm">
        <div className="mb-5 flex items-center gap-3">
          <div className="flex h-10 w-10 items-center justify-center bg-pine text-white">
            <LockKeyhole size={20} />
          </div>
          <div>
            <h1 className="text-lg font-semibold text-ink">Admin</h1>
            <p className="text-sm text-slate-500">AI Crypto Trading Assistant</p>
          </div>
        </div>
        <label className="mb-3 block text-sm font-medium text-slate-700">
          Usuario
          <input className="focus-ring mt-1 w-full border border-slate-300 px-3 py-2" value={username} onChange={(event) => setUsername(event.target.value)} />
        </label>
        <label className="mb-4 block text-sm font-medium text-slate-700">
          Password
          <input className="focus-ring mt-1 w-full border border-slate-300 px-3 py-2" type="password" value={password} onChange={(event) => setPassword(event.target.value)} />
        </label>
        {error && <div className="mb-3 border border-coral bg-red-50 px-3 py-2 text-sm text-coral">{error}</div>}
        <button className="focus-ring w-full bg-pine px-4 py-2 font-semibold text-white">Entrar</button>
      </form>
    </main>
  );
}
