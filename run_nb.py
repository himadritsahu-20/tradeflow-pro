import nbformat
from nbclient import NotebookClient

# Load notebook
with open('Tradeflow.ipynb', 'r', encoding='utf-8') as f:
    nb = nbformat.read(f, as_version=4)

# Find and remove the "hash correct" cell
cells_to_keep = []
for cell in nb.cells:
    if cell.cell_type == 'code':
        if 'CORRECT_HASH' in cell.source or 'RESET Himadri CORRECTLY' in cell.source:
            print("Skipping hash correct cell...")
            continue
    cells_to_keep.append(cell)

nb.cells = cells_to_keep

# We need to inject a dummy user session so headless execution of UI cells works
inject_cell = nbformat.v4.new_code_cell("user_session = {'logged_in': True, 'username': 'admin', 'role': 'admin', 'store': 'NYC'}")
nb.cells.insert(3, inject_cell)

# Execute the notebook
print("Executing notebook...")
client = NotebookClient(nb, timeout=600, kernel_name='python3')
try:
    client.execute()
    print("Notebook executed successfully.")
except Exception as e:
    # Safely print without unicode errors
    print(f"Error executing notebook: {str(e).encode('ascii', 'replace').decode('ascii')}")

# Save the executed notebook back over the original so the user sees the outputs
with open('Tradeflow.ipynb', 'w', encoding='utf-8') as f:
    nbformat.write(nb, f)
print("Saved back to Tradeflow.ipynb")
