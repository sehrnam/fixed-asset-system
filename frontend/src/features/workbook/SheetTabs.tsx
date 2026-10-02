import { useState } from "react";
import { SheetSummary } from "./types";

type Props = {
  sheets: SheetSummary[];
  activeSheetId: number | null;
  onSelect: (sheetId: number) => void;
  onCreate: () => void;
  onRename: (sheetId: number, newName: string) => void;
  onDelete: (sheetId: number) => void;
  onDuplicate: (sheetId: number) => void;
};

export default function SheetTabs({
  sheets,
  activeSheetId,
  onSelect,
  onCreate,
  onRename,
  onDelete,
  onDuplicate,
}: Props) {
  const [menuSheetId, setMenuSheetId] = useState<number | null>(null);
  const [renamingId, setRenamingId] = useState<number | null>(null);
  const [renameValue, setRenameValue] = useState("");

  const startRename = (sheet: SheetSummary) => {
    setRenamingId(sheet.id);
    setRenameValue(sheet.name);
    setMenuSheetId(null);
  };

  const commitRename = () => {
    if (renamingId !== null && renameValue.trim()) {
      onRename(renamingId, renameValue.trim());
    }
    setRenamingId(null);
  };

  return (
    <div className="flex items-center border-b border-slate-200 bg-slate-100 overflow-x-auto">
      {sheets.map((sheet) => {
        const isActive = sheet.id === activeSheetId;
        const isRenaming = renamingId === sheet.id;
        return (
          <div key={sheet.id} className="relative flex items-center">
            {isRenaming ? (
              <input
                autoFocus
                value={renameValue}
                onChange={(e) => setRenameValue(e.target.value)}
                onBlur={commitRename}
                onKeyDown={(e) => {
                  if (e.key === "Enter") commitRename();
                  if (e.key === "Escape") setRenamingId(null);
                }}
                className="text-sm px-3 py-2 border-r border-slate-200 bg-white outline-none w-32"
              />
            ) : (
              <button
                onClick={() => onSelect(sheet.id)}
                onContextMenu={(e) => {
                  e.preventDefault();
                  if (sheet.kind === "SYSTEM") return;
                  setMenuSheetId(menuSheetId === sheet.id ? null : sheet.id);
                }}
                className={`text-sm px-3 py-2 border-r border-slate-200 whitespace-nowrap ${
                  isActive
                    ? "bg-white text-slate-900 font-medium"
                    : "text-slate-600 hover:bg-white"
                }`}
                title={sheet.kind === "SYSTEM" ? "System sheet (read-only)" : ""}
              >
                {sheet.name}
                {sheet.kind === "SYSTEM" && (
                  <span className="ml-2 text-[10px] text-slate-400 uppercase">sys</span>
                )}
              </button>
            )}

            {menuSheetId === sheet.id && sheet.kind !== "SYSTEM" && (
              <div
                className="absolute top-full left-0 z-20 bg-white border border-slate-200 rounded shadow-md py-1 text-sm min-w-[150px]"
                onMouseLeave={() => setMenuSheetId(null)}
              >
                <button
                  onClick={() => startRename(sheet)}
                  className="block w-full text-left px-3 py-1.5 hover:bg-slate-100"
                >
                  Rename
                </button>
                <button
                  onClick={() => {
                    onDuplicate(sheet.id);
                    setMenuSheetId(null);
                  }}
                  className="block w-full text-left px-3 py-1.5 hover:bg-slate-100"
                >
                  Duplicate
                </button>
                <button
                  onClick={() => {
                    if (confirm(`Delete sheet "${sheet.name}"? This cannot be undone.`)) {
                      onDelete(sheet.id);
                    }
                    setMenuSheetId(null);
                  }}
                  className="block w-full text-left px-3 py-1.5 text-red-700 hover:bg-red-50"
                >
                  Delete
                </button>
              </div>
            )}
          </div>
        );
      })}

      <button
        onClick={onCreate}
        className="text-sm px-3 py-2 text-slate-600 hover:bg-white whitespace-nowrap"
        title="New sheet"
      >
        + New Sheet
      </button>
    </div>
  );
}