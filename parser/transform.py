# parser/transform.py
from __future__ import annotations
import pandas as pd
from typing import Dict, Optional

# ---------- Helpers ----------
def _sanitize_str(s: pd.Series) -> pd.Series:
    if s is None:
        return pd.Series(dtype="object")
    s = s.astype(str).str.strip()
    s = s.replace({"": pd.NA, "None": pd.NA, "NaN": pd.NA})
    return s

def _to_datetime(s: pd.Series) -> pd.Series:
    return pd.to_datetime(s, errors="coerce", dayfirst=True)

def _add_year_month(df: pd.DataFrame, date_col: str) -> pd.DataFrame:
    df = df.copy()
    df["año"] = df[date_col].dt.year
    df["mes"] = df[date_col].dt.month
    return df

def _to_num(val) -> float:
    try:
        return float(str(val).replace(",", "."))
    except Exception:
        return 0.0

# ---------- Captaciones ----------
def clean_inmuebles(df_inm: Optional[pd.DataFrame]) -> pd.DataFrame:
    if df_inm is None or df_inm.empty:
        return pd.DataFrame(columns=["fecha", "agente", "tipo", "precio", "precio_total", "año", "mes"])

    keep = {
        "fechaing": "fecha",
        "agente_captador": "agente",
        "tipo_operacion": "tipo",
        "precio": "precio",
        "precio_total": "precio_total",
    }
    df = df_inm.rename(columns=keep).reindex(columns=list(keep.values())).copy()

    df["fecha"] = _to_datetime(_sanitize_str(df["fecha"]))
    df["agente"] = _sanitize_str(df["agente"]).fillna("Desconocido")
    df["tipo"] = _sanitize_str(df["tipo"]).fillna("Sin especificar")

    if "precio" in df:
        df["precio"] = pd.to_numeric(df["precio"], errors="coerce").fillna(0.0)
    if "precio_total" in df:
        df["precio_total"] = pd.to_numeric(df["precio_total"], errors="coerce").fillna(0.0)

    df = df.dropna(subset=["fecha"])
    return _add_year_month(df, "fecha")

# ---------- Demandas ----------
def clean_demandas(df_dem: Optional[pd.DataFrame]) -> pd.DataFrame:
    if df_dem is None or df_dem.empty:
        return pd.DataFrame(columns=["fecha", "agente", "tipo", "año", "mes"])

    keep = {
        "fec_alta": "fecha",
        "captador": "agente",
        "tipo_operacion": "tipo",
    }
    df = df_dem.rename(columns=keep).reindex(columns=list(keep.values())).copy()

    df["fecha"] = _to_datetime(_sanitize_str(df["fecha"]))
    df["agente"] = _sanitize_str(df["agente"]).fillna("Desconocido")
    df["tipo"] = _sanitize_str(df["tipo"]).fillna("Sin especificar")

    df = df.dropna(subset=["fecha"])
    return _add_year_month(df, "fecha")

# ---------- Operaciones (Comisiones) ----------
def calcular_comision_total(row: pd.Series) -> float:
    total = 0.0
    precio = _to_num(row.get("precio_operacion", 0.0))
    for quien in ["propietario", "demandante", "cliente"]:
        tipo = str(row.get(f"tipoCom_{quien}", "") or "").strip().lower()
        valor = _to_num(row.get(f"valorCom_{quien}", 0.0))
        if valor == 0:
            continue
        if "%" in tipo:
            total += precio * valor / 100.0
        else:
            total += valor
    return total

def clean_operaciones(df_op: Optional[pd.DataFrame]) -> pd.DataFrame:
    if df_op is None or df_op.empty:
        return pd.DataFrame(columns=[
            "cod_operacion", "fecha", "agente", "tipo", "estado",
            "precio_operacion", "comision_total", "año", "mes"
        ])

    df = df_op.copy()
    df["fecha"] = _to_datetime(_sanitize_str(df["fecha"]))
    df["agente"] = _sanitize_str(df.get("vendedor")).fillna("Desconocido")
    df["tipo"] = _sanitize_str(df.get("tipo")).fillna("Sin especificar")
    df["precio_operacion"] = pd.to_numeric(df.get("precio_operacion"), errors="coerce").fillna(0.0)

    # calcular comisiones reales
    df["comision_total"] = df.apply(calcular_comision_total, axis=1)

    # filtrar solo operaciones firmadas/pagadas
    estados_validos = {"Firmada", "Pagado"}
    df = df[df["estado"].isin(estados_validos)].copy()

    df = df.dropna(subset=["fecha"])
    return _add_year_month(df, "fecha")

# ---------- Resúmenes ----------
def resumen_captaciones(df_inm: pd.DataFrame) -> pd.DataFrame:
    if df_inm.empty:
        return pd.DataFrame(columns=["año", "mes", "agente", "tipo", "num_inmuebles"])
    return (
        df_inm.groupby(["año", "mes", "agente", "tipo"], as_index=False)
        .size()
        .rename(columns={"size": "num_inmuebles"})
        .sort_values(["año", "mes", "agente", "tipo"])
        .reset_index(drop=True)
    )

def resumen_demandas(df_dem: pd.DataFrame) -> pd.DataFrame:
    if df_dem.empty:
        return pd.DataFrame(columns=["año", "mes", "agente", "tipo", "num_demandas"])
    return (
        df_dem.groupby(["año", "mes", "agente", "tipo"], as_index=False)
        .size()
        .rename(columns={"size": "num_demandas"})
        .sort_values(["año", "mes", "agente", "tipo"])
        .reset_index(drop=True)
    )

def resumen_comisiones(df_op: pd.DataFrame) -> pd.DataFrame:
    if df_op.empty:
        return pd.DataFrame(columns=["año", "mes", "agente", "total_comision", "num_ops"])
    return (
        df_op.groupby(["año", "mes", "agente"], as_index=False)
        .agg(
            total_comision=("comision_total", "sum"),
            num_ops=("cod_operacion", "count"),
        )
        .sort_values(["año", "mes", "agente"])
        .reset_index(drop=True)
    )

# ---------- Orquestador ----------
def build_all_resumenes(
    df_inmuebles: Optional[pd.DataFrame],
    df_demandas: Optional[pd.DataFrame],
    df_operaciones: Optional[pd.DataFrame],
) -> dict[str, pd.DataFrame]:
    df_inm = clean_inmuebles(df_inmuebles)
    df_dem = clean_demandas(df_demandas)
    df_op = clean_operaciones(df_operaciones)

    return {
        "captaciones": resumen_captaciones(df_inm),
        "demandas": resumen_demandas(df_dem),
        "comisiones": resumen_comisiones(df_op),
        "inmuebles_limpio": df_inm,
        "demandas_limpio": df_dem,
        "operaciones_limpio": df_op,
    }
