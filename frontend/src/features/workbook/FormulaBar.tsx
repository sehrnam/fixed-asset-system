type Props = {
  address: string;       // e.g. "A1"
  value: string;         // raw value of the selected cell
  onChange: (value: string) => void;
  onCommit: () => void;
  disabled: boolean;
};

export default function FormulaBar({ address, value, onChange, onCommit, disabled }: Props) {
  return (
    <div className="flex items-stretch border-b border-slate-200 bg-white">
      <div className="w-20 flex items-center justify-center text-sm font-mono text-slate-700 bg-slate-50 border-r border-slate-200">
        {address}
      </div>
      <div className="flex-1 flex items-center px-2 text-slate-400 text-sm select-none">fx</div>
      <input
        value={value}
        onChange={(e) => onChange(e.target.value)}
        onKeyDown={(e) => {
          if (e.key === "Enter") {
            e.preventDefault();
            onCommit();
          }
        }}
        disabled={disabled}
        placeholder={disabled ? "Read-only" : ""}
        className="flex-1 text-sm px-2 py-2 outline-none disabled:bg-slate-50"
      />
    </div>
  );
}