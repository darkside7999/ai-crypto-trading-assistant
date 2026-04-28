export default function SwitchButton({ active, label, onClick, disabled = false, tone = "pine" }) {
  const activeClass = tone === "coral" ? "bg-coral text-white" : "bg-pine text-white";
  return (
    <button
      type="button"
      onClick={onClick}
      disabled={disabled}
      className={`focus-ring inline-flex min-h-10 items-center justify-center border px-3 text-sm font-semibold transition ${
        active ? activeClass : "border-slate-300 bg-white text-slate-700 hover:bg-mist"
      } ${disabled ? "cursor-not-allowed opacity-50" : ""}`}
    >
      {label}
    </button>
  );
}
