import { ChangeEvent, useEffect, useRef, useState } from "react";
import { useAuth } from "../auth/AuthContext";
import { workbookApi } from "./api";
import CellGrid from "./CellGrid";
import FormulaBar from "./FormulaBar";
import SheetTabs from "./SheetTabs";
import { SheetRender, Workbook } from "./types";

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

export default function WorkbookPage() {
  const { user } = useAuth();
  const [workbook, setWorkbook] = useState<Workbook | null>(null);
  const [render, setRender] = useState<SheetRender | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [selectedCell, setSelectedCell] = useState<{ row: number; col: number } | null>(null);
  const [formulaDraft, setFormulaDraft] = useState("");

  // --- M6b: export / import state ---
  const [exporting, setExporting] = useState(false);
  const [importing, setImporting] = useState(false);
  const fileInputRef = useRef<HTMLInputElement | null>(null);

  const activeSheetId = workbook?.active_sheet_id ?? null;
  const activeSheet = workbook?.sheets.find((s) => s.id === activeSheetId) ?? null;
  const isSystemSheet = activeSheet?.kind === "SYSTEM";
  const canEdit = user?.role === "admin" || user?.role === "accounting";

  const refreshWorkbook = async () => {
    const wb = await workbookApi.getDefault();
    setWorkbook(wb);
    return wb;
  };

  const refreshSheet = async (sheetId: number) => {
    const data = await workbookApi.renderSheet(sheetId);
    setRender(data);
  };

  useEffect(() => {
    setLoading(true);
    refreshWorkbook()
      .then((wb) => {
        const active = wb.active_sheet_id ?? wb.sheets[0]?.id ?? null;
        if (active) return refreshSheet(active);
      })
      .catch((e) => setError(e instanceof Error ? e.message : "Failed to load"))
      .finally(() => setLoading(false));
  }, []);

  const selectSheet = async (sheetId: number) => {
    if (!workbook) return;
    try {
      await workbookApi.setActiveSheet(workbook.id, sheetId);
      await refreshWorkbook();
      await refreshSheet(sheetId);
      setSelectedCell(null);
      setFormulaDraft("");
    } catch (e) {
      setError(e instanceof Error ? e.message : "Failed to switch sheet");
    }
  };

  const createSheet = async () => {
    if (!workbook) return;
    const name = window.prompt("New sheet name", `Sheet ${workbook.sheets.length + 1}`);
    if (!name) return;
    try {
      const created = await workbookApi.createSheet(workbook.id, name);
      await refreshWorkbook();
      await selectSheet(created.id);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Failed to create sheet");
    }
  };

  const renameSheet = async (sheetId: number, newName: string) => {
    try {
      await workbookApi.renameSheet(sheetId, newName);
      await refreshWorkbook();
    } catch (e) {
      setError(e instanceof Error ? e.message : "Failed to rename");
    }
  };

  const deleteSheet = async (sheetId: number) => {
    if (!workbook) return;
    try {
      await workbookApi.deleteSheet(sheetId);
      const wb = await refreshWorkbook();
      const next = wb.sheets[0]?.id;
      if (next) await selectSheet(next);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Failed to delete");
    }
  };

  const duplicateSheet = async (sheetId: number) => {
    try {
      const dup = await workbookApi.duplicateSheet(sheetId);
      await refreshWorkbook();
      await selectSheet(dup.id);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Failed to duplicate");
    }
  };

  const commitCell = async (row: number, col: number, raw: string) => {
    if (!render) return;
    try {
      const result = await workbookApi.writeCells(render.sheet_id, [{ row, col, raw }]);
      setRender(result);
      setSelectedCell({ row, col });
      setFormulaDraft(raw);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Failed to save cell");
    }
  };

  const commitFormulaBar = async () => {
    if (!selectedCell) return;
    await commitCell(selectedCell.row, selectedCell.col, formulaDraft);
  };

  const handleCellSelect = (row: number, col: number) => {
    setSelectedCell({ row, col });
    const cell = render?.grid?.cells.find((c) => c.row === row && c.col === col);
    setFormulaDraft(cell?.raw ?? "");
  };

  // --- M6b: export / import handlers ---

  const onExport = async () => {
    if (!activeSheet || isSystemSheet) return;
    setError(null);
    setExporting(true);
    try {
      await workbookApi.exportSheetXlsx(activeSheet.id, activeSheet.name);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Export failed");
    } finally {
      setExporting(false);
    }
  };

  const onImportClick = () => {
    if (!workbook || !canEdit) return;
    fileInputRef.current?.click();
  };

  const onFileSelected = async (e: ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    // Reset the input so the same file can be selected again later.
    e.target.value = "";
    if (!file || !workbook) return;

    const defaultName = file.name.replace(/\.xlsx?$/i, "") || "Imported Sheet";
    const sheetName = window.prompt("Name for the imported sheet", defaultName);
    if (!sheetName) return;

    setError(null);
    setImporting(true);
    try {
      const created = await workbookApi.importXlsx(workbook.id, sheetName, file);
      await refreshWorkbook();
      await selectSheet(created.id);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Import failed");
    } finally {
      setImporting(false);
    }
  };

  if (loading) return <div className="text-sm text-slate-500">Loading workbook…</div>;
  if (!workbook) return null;

  const selectedAddress = selectedCell
    ? `${colLetter(selectedCell.col)}${selectedCell.row}`
    : "";

  const isReadOnly = render?.sheet_kind === "SYSTEM";

  return (
    <div className="h-full flex flex-col -m-6">
      <div className="border-b border-slate-200 bg-white px-6 py-3 flex items-center justify-between">
        <div>
          <h1 className="text-lg font-semibold text-slate-900">{workbook.name}</h1>
          <p className="text-xs text-slate-500">
            {render?.sheet_name} ·{" "}
            {isReadOnly ? "read-only system view" : "editable"}
          </p>
        </div>

        <div className="flex gap-2">
          <input
            ref={fileInputRef}
            type="file"
            accept=".xlsx,application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            className="hidden"
            onChange={onFileSelected}
          />
          <button
            type="button"
            onClick={onImportClick}
            disabled={!canEdit || importing}
            className="rounded border border-slate-300 px-3 py-2 text-sm text-slate-700 hover:bg-slate-50 disabled:opacity-50 disabled:cursor-not-allowed"
            title={
              canEdit
                ? "Import an XLSX file as a new sheet"
                : "Insufficient permissions to import"
            }
          >
            {importing ? "Importing…" : "Import XLSX"}
          </button>
          <button
            type="button"
            onClick={onExport}
            disabled={!activeSheet || isSystemSheet || exporting}
            className="rounded bg-brand-600 text-white px-3 py-2 text-sm font-medium hover:bg-brand-700 disabled:opacity-50 disabled:cursor-not-allowed"
            title={
              isSystemSheet
                ? "System sheets are exported via the Reports page"
                : "Download the current sheet as XLSX"
            }
          >
            {exporting ? "Exporting…" : "Export XLSX"}
          </button>
        </div>
      </div>

      <SheetTabs
        sheets={workbook.sheets}
        activeSheetId={activeSheetId}
        onSelect={selectSheet}
        onCreate={createSheet}
        onRename={renameSheet}
        onDelete={deleteSheet}
        onDuplicate={duplicateSheet}
      />

      {error && (
        <div className="text-sm text-red-700 bg-red-50 border border-red-200 rounded m-4 px-3 py-2">
          {error}
        </div>
      )}

      {render?.grid && (
        <>
          <FormulaBar
            address={selectedAddress}
            value={formulaDraft}
            onChange={setFormulaDraft}
            onCommit={commitFormulaBar}
            disabled={isReadOnly || !canEdit}
          />
          <CellGrid
            rows={render.grid.rows}
            cols={render.grid.cols}
            cells={render.grid.cells}
            readOnly={isReadOnly || !canEdit}
            onCellCommit={commitCell}
            onCellSelect={handleCellSelect}
          />
        </>
      )}

      {render?.table && (
        <div className="flex-1 overflow-auto bg-white p-6">
          <h2 className="text-sm font-semibold text-slate-800 mb-3">
            {render.table.title}
          </h2>
          {render.table.rows.length === 0 ? (
            <p className="text-sm text-slate-500">No data yet.</p>
          ) : (
            <table className="min-w-full text-sm border border-slate-200">
              <thead className="bg-slate-50 text-slate-600">
                <tr>
                  {render.table.columns.map((c) => (
                    <th
                      key={c}
                      className="text-left px-3 py-2 font-medium border-b border-slate-200"
                    >
                      {c}
                    </th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {render.table.rows.map((row, i) => (
                  <tr key={i} className="border-b border-slate-100">
                    {row.map((v, j) => (
                      <td key={j} className="px-3 py-2 tabular-nums">
                        {v}
                      </td>
                    ))}
                  </tr>
                ))}
              </tbody>
            </table>
          )}
        </div>
      )}
    </div>
  );
}