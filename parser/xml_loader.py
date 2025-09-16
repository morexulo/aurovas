# parser/xml_loader.py
from __future__ import annotations
import io
import zipfile
from pathlib import Path
import xml.etree.ElementTree as ET
from typing import Dict, Optional, BinaryIO
import pandas as pd

# Mapeo de los ficheros esperados y su nodo raíz de registros
TARGETS = {
    "inmuebles": ("INMUEBLES.xml", "Inmueble"),
    "demandas": ("DEMANDAS.xml", "Demanda"),
    "operaciones": ("OPERACIONES.xml", "Operacion"),
    # opcional:
    "usuarios": ("USUARIOS.xml", "Usuario"),
}

def _iterparse_to_df(fobj: BinaryIO, node_tag: str) -> pd.DataFrame:
    """Parseo eficiente por eventos: extrae cada <node_tag> como una fila."""
    rows = []
    context = ET.iterparse(fobj, events=("end",))
    for _, elem in context:
        if elem.tag == node_tag:
            row = {child.tag: (child.text.strip() if isinstance(child.text, str) else child.text)
                   for child in list(elem)}
            rows.append(row)
            elem.clear()  # liberar memoria
    return pd.DataFrame(rows)

def _find_member(namelist, contains: str) -> Optional[str]:
    """Encuentra un nombre de archivo que contenga el patrón (case-insensitive)."""
    c = contains.lower()
    for name in namelist:
        if c in name.lower():
            return name
    return None

# ---------------- ZIP -> DataFrames ----------------
def load_zip_to_dfs(zip_source) -> Dict[str, pd.DataFrame]:
    """
    Acepta:
      - ruta al ZIP (str/Path)
      - bytes del ZIP
      - file-like (por ejemplo st.uploaded_file)
    Devuelve dict con DataFrames: inmuebles, demandas, operaciones, (usuarios si existe)
    """
    # Normalizar a bytes
    if hasattr(zip_source, "read"):     # file-like
        data = zip_source.read()
    elif isinstance(zip_source, (bytes, bytearray)):
        data = zip_source
    else:                               # ruta
        with open(zip_source, "rb") as f:
            data = f.read()

    out: Dict[str, pd.DataFrame] = {}
    with zipfile.ZipFile(io.BytesIO(data)) as zf:
        names = zf.namelist()
        for key, (fname_like, node) in TARGETS.items():
            member = _find_member(names, fname_like)
            if not member:
                continue
            with zf.open(member) as f:
                df = _iterparse_to_df(f, node)
                out[key] = df

    if not out:
        raise ValueError("No se encontraron XML válidos dentro del ZIP.")
    return out

# ---------------- Carpeta -> DataFrames ----------------
def load_folder_to_dfs(folder_path) -> Dict[str, pd.DataFrame]:
    """
    Lee los XML sueltos de una carpeta usando el mismo iterparse que el ZIP.
    Devuelve dict con DataFrames: inmuebles, demandas, operaciones, (usuarios si existe)
    """
    p = Path(folder_path)
    if not p.exists() or not p.is_dir():
        raise ValueError(f"La ruta no existe o no es una carpeta: {folder_path}")

    xml_files = list(p.glob("*.xml"))
    if not xml_files:
        raise ValueError(f"No se encontraron XML en {folder_path}")

    # Índice rápido por nombre
    names = [x.name for x in xml_files]

    def _find_path(contains: str) -> Optional[Path]:
        c = contains.lower()
        for name in names:
            if c in name.lower():
                return p / name
        return None

    out: Dict[str, pd.DataFrame] = {}
    for key, (fname_like, node) in TARGETS.items():
        path = _find_path(fname_like)
        if not path:
            continue
        with open(path, "rb") as f:
            df = _iterparse_to_df(f, node)
            out[key] = df

    if not out:
        raise ValueError("No se encontraron XML válidos en la carpeta.")
    return out
