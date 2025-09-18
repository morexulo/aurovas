# parser/transform_data.py
from __future__ import annotations
import pandas as pd
from typing import Dict, Optional

# -----------------------------
# Funciones auxiliares
# -----------------------------
def _parse_fecha(df: pd.DataFrame, col: str) -> pd.Series:
    if col not in df.columns:
        return pd.NaT
    return pd.to_datetime(df[col], errors="coerce", dayfirst=True)

def _to_num(val) -> float:
    """Convierte string/num a float seguro."""
    try:
        return float(str(val).replace(",", "."))
    except Exception:
        return 0.0

def calcular_comision_total(row: pd.Series) -> float:
    """Suma de comisiones aplicando lógica de tipo % o €."""
    total = 0.0
    precio = _to_num(row.get("precio_operacion", 0.0))
    for quien in ["propietario", "demandante", "cliente"]:
        tipo = str(row.get(f"tipoCom_{quien}", "") or "").strip().lower()
        valor = _to_num(row.get(f"valorCom_{quien}", 0.0))
        if valor == 0:
            continue
        if "%" in tipo:
            total += precio * valor / 100.0
        else:  # por defecto asumimos que es importe fijo en €
            total += valor
    return total

# -----------------------------
# Generar resumenes
# -----------------------------
def generar_resumenes(dfs_raw: Dict[str, pd.DataFrame]) -> Dict[str, pd.DataFrame]:
    out: Dict[str, pd.DataFrame] = {}

    # ---------------- OPERACIONES ----------------
    df_ops = dfs_raw.get("operaciones")
    if df_ops is None or df_ops.empty:
        return out

    # Parsear fecha
    df_ops["fecha"] = _parse_fecha(df_ops, "fecha")

    # Calcular comisiones totales
    df_ops["comision_total"] = df_ops.apply(calcular_comision_total, axis=1)

    # Mapear agente (usamos columna vendedor si existe)
    if "vendedor" in df_ops.columns:
        df_ops["agente"] = df_ops["vendedor"].fillna("(Sin asignar)")
    else:
        df_ops["agente"] = "(Sin asignar)"

    # Filtrar operaciones válidas (Firmada / Pagado)
    estados_validos = {"Firmada", "Pagado"}
    ops_validas = df_ops[df_ops["estado"].isin(estados_validos)].copy()

    # ---------------- Resumen mensual por agente ----------------
    if not ops_validas.empty:
        ops_validas["año"] = ops_validas["fecha"].dt.year
        ops_validas["mes"] = ops_validas["fecha"].dt.month
        resumen = (
            ops_validas.groupby(["año", "mes", "agente"], as_index=False)
            .agg(
                total_comision=("comision_total", "sum"),
                num_ops=("cod_operacion", "count"),
            )
            .sort_values(["año", "mes", "agente"])
        )
    else:
        resumen = pd.DataFrame(columns=["año", "mes", "agente", "total_comision", "num_ops"])

    out["comisiones"] = resumen

    # ---------------- Detalle limpio de operaciones ----------------
    detalle_cols = [
        "cod_operacion",
        "fecha",
        "agente",
        "tipo",
        "estado",
        "precio_operacion",
        "comision_total",
    ]

    operaciones_limpio = ops_validas.copy()
    for c in detalle_cols:
        if c not in operaciones_limpio.columns:
            operaciones_limpio[c] = None

    operaciones_limpio = operaciones_limpio[detalle_cols].copy()
    out["operaciones_limpio"] = operaciones_limpio

    return out

# -----------------------------
# Compatibilidad con app.py
# -----------------------------
def build_all_resumenes(
    df_inmuebles: Optional[pd.DataFrame],
    df_demandas: Optional[pd.DataFrame],
    df_operaciones: Optional[pd.DataFrame],
) -> Dict[str, pd.DataFrame]:
    dfs_raw: Dict[str, pd.DataFrame] = {}
    if df_inmuebles is not None:
        dfs_raw["inmuebles"] = df_inmuebles
    if df_demandas is not None:
        dfs_raw["demandas"] = df_demandas
    if df_operaciones is not None:
        dfs_raw["operaciones"] = df_operaciones

    return generar_resumenes(dfs_raw)
