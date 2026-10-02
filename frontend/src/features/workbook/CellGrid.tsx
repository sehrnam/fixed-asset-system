import { useMemo, useRef, useState } from "react";
import { Cell } from "./types";

type Props = {
  rows: number;
  cols: number;
  cells: Cell[];
  readOnly: boolean;
  onCellCommit: (row: number, col: number, raw: string) => void;
  onCellSelect?: (row: number, col: number) => void;
};

const colLetter = (col: number): string => {
  let letters = "";
  let c = col;
  while (c > 0) {
    const rem = (c - 1) % 26;
    letters = String.fromCharCode(65 + rem) + letters;
    c = Math.floor((c - 1) / 26);
  }
  return letters;
};

export default function CellGrid({
  rows,
  cols,
  cells,
  readOnly,
  onCellCommit,
  onCellSelect,
}: Props) {
  const [selected, setSelected] = useState<{ row: number; col: number } | null>(null);
  const [editing, setEditing] = useState<{ row: number; col: number } | null>(null);
  const [draft, setDraft] = useState("");
  const inputRef = useRef<HTMLInputElement | null>(null);

  const byKey = useMemo(() => {
    const map = new Map<string, Cell>();
    for (const c of cells) map.set(`${c.row}:${c.col}`, c);
    return map;
  }, [cells]);

  const startEdit = (row: number, col: number) => {
    if (readOnly) return;
    const cell = byKey.get(`${row}:${col}`);
    setEditing({ row, col });
    setDraft(cell?.raw ?? "");
    setTimeout(() => inputRef.current?.focus(), 0);
  };

  const commit = () => {
    if (editing) {
      onCellCommit(editing.row, editing.col, draft);
    }
    setEditing(null);
    setDraft("");
  };

  const selectCell = (row: number, col: number) => {
    setSelected({ row, col });
    onCellSelect?.(row, col);
  };

  return (
    <div className="overflow-auto flex-1 bg-white">
      <table className="border-collapse text-sm">
        <thead>
          <tr>
            <th className="sticky top-0 left-0 z-10 w-12 bg-slate-100 border border-slate-200 text-xs font-medium text-slate-500">
              #
            </th>
            {Array.from({ length: cols }, (_, i) => i + 1).map((c) => (
              <th
                key={c}
                className="sticky top-0 z-10 min-w-[100px] bg-slate-100 border border-slate-200 text-xs font-medium text-slate-600 px-2 py-1"
              >
                {colLetter(c)}
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {Array.from({ length: rows }, (_, i) => i + 1).map((r) => (
            <tr key={r}>
              <td className="sticky left-0 z-10 bg-slate-100 border border-slate-200 text-xs text-slate-500 text-center">
                {r}
              </td>
              {Array.from({ length: cols }, (_, i) => i + 1).map((c) => {
                const cell = byKey.get(`${r}:${c}`);
                const isEditing = editing?.row === r && editing?.col === c;
                const isSelected = selected?.row === r && selected?.col === c;
                const display = cell?.error ? `#ERR` : cell?.computed ?? "";

                return (
                  <td
                    key={c}
                    onClick={() => selectCell(r, c)}
                    onDoubleClick={() => startEdit(r, c)}
                    className={`border border-slate-200 px-2 py-1 align-top ${
                      isSelected ? "bg-sky-50 ring-1 ring-sky-300" : "bg-white"
                    } ${cell?.error ? "text-red-600" : ""} ${
                      readOnly ? "" : "cursor-cell"
                    }`}
                    title={cell?.error ?? ""}
                  >
                    {isEditing ? (
                      <input
                        ref={inputRef}
                        value={draft}
                        onChange={(e) => setDraft(e.target.value)}
                        onBlur={commit}
                        onKeyDown={(e) => {
                          if (e.key === "Enter") {
                            e.preventDefault();
                            commit();
                          }
                          if (e.key === "Escape") {
                            setEditing(null);
                            setDraft("");
                          }
                        }}
                        className="w-full outline-none bg-yellow-50"
                      />
                    ) : (
                      <span className="block min-h-[18px]">{display}</span>
                    )}
                  </td>
                );
              })}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}