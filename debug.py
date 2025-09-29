from parser.xml_loader import load_folder_to_dfs
from parser.transform import build_all_resumenes

# Cargar los XML desde la carpeta datos/
dfs_raw = load_folder_to_dfs("datos")

# Construir los resúmenes
res = build_all_resumenes(
    dfs_raw.get("inmuebles"),
    dfs_raw.get("demandas"),
    dfs_raw.get("operaciones"),
)

# Extraer operaciones limpias
df_ops = res["operaciones_limpio"]

# Mostrar info básica
print("Fechas:", df_ops["fecha"].min(), "→", df_ops["fecha"].max())
print("Estados únicos:", df_ops["estado"].unique())
print("Número de registros:", len(df_ops))
