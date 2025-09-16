# parser/transform.py
from __future__ import annotations
import pandas as pd

# ---------- Helpers ----------
def _sanitize_str(s: pd.Series) -> pd.Series:
    # Limpia strings: quita espacios/saltos y normaliza nulos
    if s is None:
        return pd.Series(dtype="object")
    s = s.astype(str).str.strip()
    s = s.replace({"": pd.NA, "None": pd.NA, "NaN": pd.NA})
    return s

def _to_datetime(s: pd.Series) -> pd.Series:
    # dayfirst=True (formatos españoles). Recibe serie ya saneada.
    return pd.to_datetime(s, errors="coerce", dayfirst=True)

def _add_year_month(df: pd.DataFrame, date_col: str) -> pd.DataFrame:
    df = df.copy()
    df["año"] = df[date_col].dt.year
    df["mes"] = df[date_col].dt.month
    return df

def _to_num(s: pd.Series) -> pd.Series:
    # Soporta "€ 1.234,56", "1 234,56", "1234.56", etc.
    s = _sanitize_str(s)
    # mantener solo dígitos, separadores y signo
    s = s.str.replace(r"[^\d,.\-]", "", regex=True)
    # caso ES: miles con punto y decimales con coma -> quitar miles y convertir coma a punto
    s = s.str.replace(".", "", regex=False).str.replace(",", ".", regex=False)
    return pd.to_numeric(s, errors="coerce").fillna(0.0)

# ---------- Limpiezas base ----------
def clean_inmuebles(df_inm: pd.DataFrame) -> pd.DataFrame:
    if df_inm is None:
        return pd.DataFrame(columns=["fecha", "agente", "tipo", "precio", "precio_total", "año", "mes"])

    keep = {
        "fechaing": "fecha",
        "agente_captador": "agente",
        "tipo_operacion": "tipo",
        "precio": "precio",
        "precio_total": "precio_total",
    }
    df = df_inm.rename(columns=keep).reindex(columns=list(keep.values())).copy()

    # Fecha
    df["fecha"] = _to_datetime(_sanitize_str(df["fecha"]))
    # Agente (no eliminar por estar vacío)
    df["agente"] = _sanitize_str(df["agente"]).fillna("Desconocido")
    # Tipo
    df["tipo"] = _sanitize_str(df["tipo"]).fillna("Sin especificar")

    # Numéricos (por si luego los quieres usar)
    if "precio" in df:
        df["precio"] = _to_num(df["precio"])
    if "precio_total" in df:
        df["precio_total"] = _to_num(df["precio_total"])

    # Eliminar solo filas sin fecha
    df = df.dropna(subset=["fecha"])
    # Añadir año/mes
    return _add_year_month(df, "fecha")

def clean_demandas(df_dem: pd.DataFrame) -> pd.DataFrame:
    if df_dem is None:
        return pd.DataFrame(columns=["fecha", "agente", "tipo", "año", "mes"])

    keep = {
        "fec_alta": "fecha",
        "captador": "agente",
        "tipo_operacion": "tipo",
    }
    df = df_dem.rename(columns=keep).reindex(columns=list(keep.values())).copy()

    # Fecha
    df["fecha"] = _to_datetime(_sanitize_str(df["fecha"]))
    # Agente (no eliminar por estar vacío)
    df["agente"] = _sanitize_str(df["agente"]).fillna("Desconocido")
    # Tipo
    df["tipo"] = _sanitize_str(df["tipo"]).fillna("Sin especificar")

    # Eliminar solo filas sin fecha
    df = df.dropna(subset=["fecha"])
    # Añadir año/mes
    return _add_year_month(df, "fecha")

def clean_operaciones(df_op: pd.DataFrame) -> pd.DataFrame:
    if df_op is None:
        return pd.DataFrame(columns=["fecha", "agente", "tipo", "com_prop", "com_dem", "com_cli",
                                     "comision_total", "año", "mes"])

    keep = {
        "fecha": "fecha",
        "vendedor": "agente",
        "tipo": "tipo",
        "valorCom_propietario": "com_prop",
        "valorCom_demandante": "com_dem",
        "valorCom_cliente": "com_cli",
    }
    df = df_op.rename(columns=keep).reindex(columns=list(keep.values())).copy()

    # Fecha
    df["fecha"] = _to_datetime(_sanitize_str(df["fecha"]))
    # Agente / Tipo
    df["agente"] = _sanitize_str(df["agente"]).fillna("Desconocido")
    df["tipo"] = _sanitize_str(df["tipo"]).fillna("Sin especificar")

    # Comisiones numéricas
    for c in ("com_prop", "com_dem", "com_cli"):
        if c in df:
            df[c] = _to_num(df[c])
        else:
            df[c] = 0.0

    df["comision_total"] = df["com_prop"] + df["com_dem"] + df["com_cli"]

    # Eliminar solo filas sin fecha
    df = df.dropna(subset=["fecha"])
    # Añadir año/mes
    return _add_year_month(df, "fecha")

# ---------- Resúmenes para el dashboard ----------
def resumen_captaciones(df_inm_limpio: pd.DataFrame) -> pd.DataFrame:
    if df_inm_limpio.empty:
        return pd.DataFrame(columns=["año", "mes", "agente", "tipo", "num_inmuebles"])
    return (
        df_inm_limpio
        .groupby(["año", "mes", "agente", "tipo"], as_index=False)
        .size()
        .rename(columns={"size": "num_inmuebles"})
        .sort_values(["año", "mes", "agente", "tipo"])
        .reset_index(drop=True)
    )

def resumen_demandas(df_dem_limpio: pd.DataFrame) -> pd.DataFrame:
    if df_dem_limpio.empty:
        return pd.DataFrame(columns=["año", "mes", "agente", "tipo", "num_demandas"])
    return (
        df_dem_limpio
        .groupby(["año", "mes", "agente", "tipo"], as_index=False)
        .size()
        .rename(columns={"size": "num_demandas"})
        .sort_values(["año", "mes", "agente", "tipo"])
        .reset_index(drop=True)
    )

def resumen_comisiones(df_op_limpio: pd.DataFrame) -> pd.DataFrame:
    if df_op_limpio.empty:
        return pd.DataFrame(columns=["año", "mes", "agente", "comision_total"])
    return (
        df_op_limpio
        .groupby(["año", "mes", "agente"], as_index=False)["comision_total"]
        .sum()
        .sort_values(["año", "mes", "agente"])
        .reset_index(drop=True)
    )

# ---------- Orquestador ----------
def build_all_resumenes(
    df_inm_raw: pd.DataFrame,
    df_dem_raw: pd.DataFrame,
    df_op_raw: pd.DataFrame,
) -> dict[str, pd.DataFrame]:
    # Limpiar cada dataset (tolerante a None y a strings sucios)
    df_inm = clean_inmuebles(df_inm_raw)
    df_dem = clean_demandas(df_dem_raw)
    df_op = clean_operaciones(df_op_raw)

    return {
        "captaciones": resumen_captaciones(df_inm),
        "demandas": resumen_demandas(df_dem),
        "comisiones": resumen_comisiones(df_op),
        "inmuebles_limpio": df_inm,
        "demandas_limpio": df_dem,
        "operaciones_limpio": df_op,
    }
