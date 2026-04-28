import { Activity, Bell, Bot, Pause, Play, RefreshCw, Shield, TestTube2 } from "lucide-react";
import { useEffect, useState } from "react";

import Panel from "../components/Panel";
import SwitchButton from "../components/SwitchButton";
import TradeTable from "../components/TradeTable";
import { api } from "../services/api";

const initialSettings = {
  max_daily_capital_eur: 5,
  max_daily_loss_eur: 10,
  target_profit_eur: 0.3,
  max_open_trades: 2,
  max_capital_per_trade_eur: 2.5,
  max_loss_per_trade_eur: 1,
  min_volume_quote: 1000000,
  max_spread_pct: 0.25,
  max_trade_minutes: 240,
  allow_sell_small_loss: false,
  trailing_take_profit_pct: 0.15,
  allowed_symbols: ["BTC/USDT", "ETH/USDT", "SOL/USDT"],
  blocked_symbols: []
};

export default function Dashboard() {
  const [status, setStatus] = useState(null);
  const [settings, setSettings] = useState(initialSettings);
  const [openTrades, setOpenTrades] = useState([]);
  const [history, setHistory] = useState([]);
  const [decisions, setDecisions] = useState([]);
  const [logs, setLogs] = useState([]);
  const [notice, setNotice] = useState("");
  const [loading, setLoading] = useState(false);

  async function loadAll() {
    setLoading(true);
    try {
      const [nextStatus, nextSettings, nextOpen, nextHistory, nextDecisions, nextLogs] = await Promise.all([
        api.status(),
        api.riskSettings(),
        api.openTrades(),
        api.history(),
        api.decisions(),
        api.logs()
      ]);
      setStatus(nextStatus);
      setSettings(nextSettings);
      setOpenTrades(nextOpen);
      setHistory(nextHistory);
      setDecisions(nextDecisions);
      setLogs(nextLogs);
    } catch (err) {
      setNotice(err.message);
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    loadAll();
    const id = setInterval(loadAll, 15000);
    return () => clearInterval(id);
  }, []);

  async function run(action) {
    setNotice("");
    try {
      const result = await action();
      setNotice(result.message || "OK");
      await loadAll();
    } catch (err) {
      setNotice(err.message);
    }
  }

  function updateNumber(key, value) {
    setSettings((current) => ({ ...current, [key]: Number(value) }));
  }

  function updateSymbols(key, value) {
    setSettings((current) => ({
      ...current,
      [key]: value
        .split(",")
        .map((item) => item.trim().toUpperCase())
        .filter(Boolean)
    }));
  }

  const stat = status || { enabled: false, trading_mode: "DEMO", control_mode: "MANUAL", open_trades: 0 };

  return (
    <main className="min-h-screen bg-[#f6f8f7]">
      <header className="border-b border-slate-200 bg-white">
        <div className="mx-auto flex max-w-7xl flex-wrap items-center justify-between gap-4 px-4 py-4">
          <div>
            <h1 className="text-xl font-semibold text-ink">AI Crypto Trading Assistant</h1>
            <p className="text-sm text-slate-500">Fase 1: paper trading con datos de mercado y trazabilidad.</p>
          </div>
          <div className="flex flex-wrap gap-2">
            <button className="focus-ring inline-flex items-center gap-2 border border-slate-300 bg-white px-3 py-2 text-sm font-semibold" onClick={loadAll}>
              <RefreshCw size={16} /> Refrescar
            </button>
            <button className="focus-ring inline-flex items-center gap-2 bg-amberline px-3 py-2 text-sm font-semibold text-white" onClick={() => run(api.tick)}>
              <Activity size={16} /> Tick demo
            </button>
            <button className="focus-ring inline-flex items-center gap-2 border border-slate-300 bg-white px-3 py-2 text-sm font-semibold" onClick={() => run(api.telegramTest)}>
              <Bell size={16} /> Telegram
            </button>
          </div>
        </div>
      </header>

      <div className="mx-auto grid max-w-7xl gap-4 px-4 py-4 lg:grid-cols-[320px_1fr]">
        <aside className="space-y-4">
          <Panel title="Estado">
            <div className="grid grid-cols-2 gap-2 text-sm">
              <div className="border border-slate-200 p-3">
                <div className="mb-1 flex items-center gap-2 text-slate-500"><Bot size={15} /> Bot</div>
                <strong className={stat.enabled ? "text-pine" : "text-coral"}>{stat.enabled ? "ON" : "OFF"}</strong>
              </div>
              <div className="border border-slate-200 p-3">
                <div className="mb-1 flex items-center gap-2 text-slate-500"><TestTube2 size={15} /> Modo</div>
                <strong>{stat.trading_mode}</strong>
              </div>
              <div className="border border-slate-200 p-3">
                <div className="mb-1 flex items-center gap-2 text-slate-500"><Shield size={15} /> Control</div>
                <strong>{stat.control_mode}</strong>
              </div>
              <div className="border border-slate-200 p-3">
                <div className="mb-1 text-slate-500">Abiertas</div>
                <strong>{stat.open_trades}</strong>
              </div>
            </div>
            <div className="mt-4 grid grid-cols-2 gap-2">
              <SwitchButton active={stat.enabled} label="ON" onClick={() => run(api.start)} />
              <SwitchButton active={!stat.enabled} label="OFF" onClick={() => run(api.stop)} tone="coral" />
              <SwitchButton active={stat.trading_mode === "DEMO"} label="DEMO" onClick={() => run(api.setDemo)} />
              <SwitchButton active={stat.trading_mode === "REAL"} label="REAL" onClick={() => run(api.setReal)} tone="coral" />
              <SwitchButton active={stat.control_mode === "MANUAL"} label="Manual" onClick={() => run(api.setManual)} />
              <SwitchButton active={stat.control_mode === "AUTONOMOUS"} label="Autonomo" onClick={() => run(api.setAutonomous)} />
            </div>
            {notice && <div className="mt-3 border border-slate-200 bg-mist px-3 py-2 text-sm text-slate-700">{notice}</div>}
          </Panel>

          <Panel title="Riesgo">
            <div className="space-y-3 text-sm">
              {[
                ["max_daily_capital_eur", "Capital maximo diario"],
                ["max_daily_loss_eur", "Perdida maxima diaria"],
                ["target_profit_eur", "Beneficio objetivo"],
                ["max_open_trades", "Max. operaciones abiertas"],
                ["max_capital_per_trade_eur", "Capital max. por operacion"],
                ["max_loss_per_trade_eur", "Perdida max. por operacion"],
                ["max_spread_pct", "Spread max. %"],
                ["min_volume_quote", "Volumen minimo"]
              ].map(([key, label]) => (
                <label key={key} className="block">
                  <span className="mb-1 block text-slate-600">{label}</span>
                  <input className="focus-ring w-full border border-slate-300 px-3 py-2" type="number" step="0.01" value={settings[key]} onChange={(event) => updateNumber(key, event.target.value)} />
                </label>
              ))}
              <label className="block">
                <span className="mb-1 block text-slate-600">Permitidas</span>
                <input className="focus-ring w-full border border-slate-300 px-3 py-2" value={settings.allowed_symbols.join(", ")} onChange={(event) => updateSymbols("allowed_symbols", event.target.value)} />
              </label>
              <label className="block">
                <span className="mb-1 block text-slate-600">Bloqueadas</span>
                <input className="focus-ring w-full border border-slate-300 px-3 py-2" value={settings.blocked_symbols.join(", ")} onChange={(event) => updateSymbols("blocked_symbols", event.target.value)} />
              </label>
              <button className="focus-ring w-full bg-pine px-3 py-2 font-semibold text-white" onClick={() => run(() => api.updateRiskSettings(settings))}>
                Guardar riesgo
              </button>
            </div>
          </Panel>
        </aside>

        <section className="space-y-4">
          <Panel title="Operaciones abiertas" action={loading ? <span className="text-xs text-slate-500">Cargando...</span> : null}>
            <TradeTable trades={openTrades} onConfirmBuy={(id) => run(() => api.confirmBuy(id))} onConfirmSell={(id) => run(() => api.confirmSell(id))} onLongTerm={(id) => run(() => api.convertLongTerm(id))} />
          </Panel>

          <div className="grid gap-4 xl:grid-cols-2">
            <Panel title="Historial">
              <TradeTable trades={history.slice(0, 8)} onConfirmBuy={(id) => run(() => api.confirmBuy(id))} onConfirmSell={(id) => run(() => api.confirmSell(id))} onLongTerm={(id) => run(() => api.convertLongTerm(id))} />
            </Panel>
            <Panel title="Decisiones">
              <div className="space-y-3">
                {decisions.slice(0, 8).map((decision) => (
                  <div key={decision.id} className="border border-slate-200 p-3 text-sm">
                    <div className="flex justify-between gap-3">
                      <strong>{decision.action} {decision.symbol || ""}</strong>
                      <span className="text-slate-500">{Number(decision.expected_net_profit).toFixed(2)} EUR</span>
                    </div>
                    <p className="mt-1 text-slate-600">{decision.reason}</p>
                  </div>
                ))}
                {!decisions.length && <div className="py-6 text-sm text-slate-500">Sin decisiones registradas.</div>}
              </div>
            </Panel>
          </div>

          <Panel title="Logs">
            <div className="max-h-80 space-y-2 overflow-auto text-sm">
              {logs.map((log) => (
                <div key={log.id} className="grid gap-2 border-b border-slate-100 py-2 md:grid-cols-[150px_160px_1fr]">
                  <span className="text-slate-500">{new Date(log.created_at).toLocaleString()}</span>
                  <strong className={log.level === "ERROR" ? "text-coral" : "text-slate-700"}>{log.event}</strong>
                  <span className="text-slate-600">{log.message}</span>
                </div>
              ))}
              {!logs.length && <div className="py-6 text-sm text-slate-500">Sin logs.</div>}
            </div>
          </Panel>
        </section>
      </div>
    </main>
  );
}
