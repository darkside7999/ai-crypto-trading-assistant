import { Check, Clock, ShieldAlert, X } from "lucide-react";

function money(value) {
  if (value === null || value === undefined) return "-";
  return `${Number(value).toFixed(2)} EUR`;
}

export default function TradeTable({ trades, onConfirmBuy, onConfirmSell, onLongTerm }) {
  if (!trades.length) {
    return <div className="py-6 text-sm text-slate-500">Sin operaciones para mostrar.</div>;
  }

  return (
    <div className="overflow-x-auto">
      <table className="w-full min-w-[780px] text-left text-sm">
        <thead className="border-b border-slate-200 text-xs uppercase text-slate-500">
          <tr>
            <th className="py-2">Par</th>
            <th>Estado</th>
            <th>Capital</th>
            <th>Entrada</th>
            <th>Actual</th>
            <th>Objetivo</th>
            <th>PnL neto</th>
            <th className="text-right">Acciones</th>
          </tr>
        </thead>
        <tbody>
          {trades.map((trade) => (
            <tr key={trade.id} className="border-b border-slate-100 align-top">
              <td className="py-3 font-semibold text-ink">{trade.symbol}</td>
              <td className="py-3">
                <span className="inline-flex items-center gap-1 text-xs font-semibold text-slate-700">
                  {trade.status === "RISK" ? <ShieldAlert size={14} /> : <Clock size={14} />}
                  {trade.status}
                </span>
              </td>
              <td>{money(trade.amount_eur)}</td>
              <td>{trade.entry_price ? Number(trade.entry_price).toFixed(6) : "-"}</td>
              <td>{trade.current_price ? Number(trade.current_price).toFixed(6) : "-"}</td>
              <td>{trade.target_price ? Number(trade.target_price).toFixed(6) : "-"}</td>
              <td className={trade.net_pnl_eur >= 0 ? "text-pine" : "text-coral"}>{money(trade.net_pnl_eur)}</td>
              <td className="space-x-2 text-right">
                {trade.status === "PROPOSED" && (
                  <button className="focus-ring border border-pine px-2 py-1 text-pine" onClick={() => onConfirmBuy(trade.id)} title="Confirmar compra">
                    <Check size={16} />
                  </button>
                )}
                {(trade.status === "OPEN" || trade.status === "RISK") && (
                  <button className="focus-ring border border-coral px-2 py-1 text-coral" onClick={() => onConfirmSell(trade.id)} title="Confirmar venta">
                    <X size={16} />
                  </button>
                )}
                {(trade.status === "OPEN" || trade.status === "RISK") && (
                  <button className="focus-ring border border-slate-300 px-2 py-1 text-slate-700" onClick={() => onLongTerm(trade.id)}>
                    Largo plazo
                  </button>
                )}
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
