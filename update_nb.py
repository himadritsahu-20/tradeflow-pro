import nbformat

with open('Tradeflow.ipynb', 'r', encoding='utf-8') as f:
    nb = nbformat.read(f, as_version=4)

for cell in nb.cells:
    if cell.cell_type == 'code':
        # Update add_sale
        if 'def add_sale' in cell.source:
            cell.source = cell.source.replace('    conn.commit()', '    conn.commit()\n    df_auto = pd.read_sql_query("SELECT * FROM sales", conn)\n    df_auto.to_csv("TradeFlow_Master_Sync.xls", index=False)')
            
        # Update edit_sale
        if 'def edit_sale' in cell.source:
            cell.source = cell.source.replace('    conn.commit()', '    conn.commit()\n    df_auto = pd.read_sql_query("SELECT * FROM sales", conn)\n    df_auto.to_csv("TradeFlow_Master_Sync.xls", index=False)')

        # Update export_pnl
        if 'def export_pnl' in cell.source:
            # We want to keep the print statement but change the filename
            old_filename_code = "filename = f\"TradeFlow_PnL_{user_session['username']}_{datetime.now().strftime('%Y%m%d_%H%M')}.csv\""
            new_filename_code = "filename = \"TradeFlow_Master_Sync.xls\""
            cell.source = cell.source.replace(old_filename_code, new_filename_code)

with open('Tradeflow.ipynb', 'w', encoding='utf-8') as f:
    nbformat.write(nb, f)

print("Jupyter Notebook successfully updated with auto-sync code!")
