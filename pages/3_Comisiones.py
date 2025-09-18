# pages/3_Comisiones.py
import streamlit as st
import pandas as pd
import plotly.express as px
from datetime import date
import calendar

st.title("💰 Comisiones")

# --- Validación de datos ---
res = st.session_state.get("resumenes")
if not res or "operaciones_limpio" not in res:
    st.warning("⚠️ Sube primero un ZIP desde la pestaña 'Inicio'.")
    st.stop()

df_ops = res["operaciones_limpio"].copy()

# --- Saneado mínimo ---
df_ops["fecha"] = pd.to_datetime(df_ops["fecha"], errors="coerce")
df_ops = df_ops.dropna(subset=["fecha"])
df_ops["comision_total"] = pd.to_numeric(df_ops["comision_total"], errors="coerce").fillna(0.0)
if "agente" not in df_ops.columns:
    df_ops["agente"] = "(Sin agente)"
if "tipo" not in df_ops.columns:
    df_ops["tipo"] = "(Sin tipo)"

df_ops["mes_periodo"] = df_ops["fecha"].dt.to_period("M")

# --- Filtros ---
with st.container():
    agentes_all = sorted(df_ops["agente"].dropna().unique().tolist())
    preferidas = [a for a in agentes_all if any(x in a for x in ["Bibiana", "Pati", "Patricia", "Teresa"])]
    default_agentes = preferidas if preferidas else agentes_all

    min_d = df_ops["fecha"].min().date()
    max_d = df_ops["fecha"].max().date()

    default_start = date(max_d.year, max_d.month, 1)
    last_day = calendar.monthrange(max_d.year, max_d.month)[1]
    default_end = date(max_d.year, max_d.month, last_day)
    if default_end > max_d:
        default_end = max_d

    col_f1, col_f2 = st.columns([2, 3])
    agentes_sel = col_f1.multiselect("Agentes", agentes_all, default=default_agentes)
    fecha_ini, fecha_fin = col_f2.date_input(
        "Rango de fechas (por días)",
        value=(default_start, default_end),
        min_value=min_d,
        max_value=max_d,
    )

# --- Aplicar filtros ---
mask = (
    df_ops["agente"].isin(agentes_sel)
    & (df_ops["fecha"] >= pd.to_datetime(fecha_ini))
    & (df_ops["fecha"] <= pd.to_datetime(fecha_fin))
)
dff = df_ops.loc[mask].copy()

# --- KPIs ---
col_k1, col_k2, col_k3, col_k4, col_k5 = st.columns(5)
if dff.empty:
    total_sel = ult_mes_total = n_ops = media_por_op = mejor_mes_val = 0
    mejor_mes = "-"
else:
    total_sel = float(dff["comision_total"].sum())
    n_ops = len(dff)
    media_por_op = float(total_sel / n_ops) if n_ops else 0
    ult_mes = dff["mes_periodo"].max()
    ult_mes_total = float(dff.loc[dff["mes_periodo"] == ult_mes, "comision_total"].sum())
    by_month = dff.groupby("mes_periodo", as_index=False)["comision_total"].sum()
    if not by_month.empty:
        idxmax = by_month["comision_total"].idxmax()
        mejor_periodo = by_month.loc[idxmax, "mes_periodo"]
        mejor_mes_val = float(by_month.loc[idxmax, "comision_total"])
        mejor_mes = mejor_periodo.strftime("%b %Y")
    else:
        mejor_mes = "-"
        mejor_mes_val = 0

col_k1.metric("Comisión total", f"€{total_sel:,.0f}")
col_k2.metric("Último mes", f"€{ult_mes_total:,.0f}")
col_k3.metric("Nº operaciones", n_ops)
col_k4.metric("Media por operación", f"€{media_por_op:,.0f}")
col_k5.metric("Mejor mes", f"{mejor_mes} (€{mejor_mes_val:,.0f})")

st.divider()

# --- Ranking ---
st.subheader("Ranking de comisiones por agente")
if dff.empty:
    st.info("No hay datos para los filtros seleccionados.")
else:
    rank = (
        dff.groupby("agente", as_index=False)
           .agg(
               total_comision=("comision_total", "sum"),
               num_ops=("comision_total", "count")  # ✅ usamos comision_total para contar filas
           )
           .sort_values("total_comision", ascending=True)
    )
    fig_rank = px.bar(rank, x="total_comision", y="agente", orientation="h", text="total_comision")
    fig_rank.update_traces(texttemplate="€%{text:,.0f}", textposition="outside")
    st.plotly_chart(fig_rank, use_container_width=True)

    resumen_tbl = rank.copy()
    resumen_tbl["media_op"] = (resumen_tbl["total_comision"] / resumen_tbl["num_ops"]).fillna(0.0)
    resumen_tbl_display = resumen_tbl[["agente", "total_comision", "num_ops", "media_op"]].copy()
    resumen_tbl_display["total_comision"] = resumen_tbl_display["total_comision"].map(lambda x: f"€{x:,.0f}")
    resumen_tbl_display["media_op"] = resumen_tbl_display["media_op"].map(lambda x: f"€{x:,.0f}")
    st.dataframe(resumen_tbl_display, use_container_width=True, hide_index=True)

st.divider()

# --- Distribuciones ---
st.subheader("Distribución general de comisiones en el periodo")
col1, col2 = st.columns(2)

with col1:
    if dff.empty:
        st.info("Sin datos para el periodo seleccionado.")
    else:
        share = dff.groupby("agente", as_index=False)["comision_total"].sum()
        fig_share = px.pie(share, names="agente", values="comision_total", hole=0.5)
        fig_share.update_traces(texttemplate="%{label}<br>€%{value:,.0f} (%{percent})")
        st.plotly_chart(fig_share, use_container_width=True, key="donut_agentes")

with col2:
    if dff.empty or dff["tipo"].dropna().empty:
        st.info("No hay información de tipo disponible en este rango.")
    else:
        by_tipo = dff.groupby("tipo", as_index=False)["comision_total"].sum()
        fig_tipo = px.pie(by_tipo, names="tipo", values="comision_total", hole=0.5)
        fig_tipo.update_traces(texttemplate="%{label}<br>€%{value:,.0f} (%{percent})")
        st.plotly_chart(fig_tipo, use_container_width=True, key="donut_tipos")

st.divider()

# --- Hoja de pago ---
st.subheader("Hoja de pago (mensual por agente)")
if dff.empty:
    st.info("No hay datos para mostrar.")
else:
    pivot = (
        dff.groupby(["mes_periodo", "agente"], as_index=False)["comision_total"].sum()
           .pivot(index="mes_periodo", columns="agente", values="comision_total")
           .fillna(0.0)
           .sort_index(ascending=False)
    )
    pivot_display = pivot.copy()
    for c in pivot_display.columns:
        pivot_display[c] = pivot_display[c].map(lambda x: f"€{x:,.0f}")
    st.dataframe(pivot_display, use_container_width=True)

    csv = pivot.to_csv().encode("utf-8")
    st.download_button("⬇️ Descargar hoja de pago (CSV)", data=csv,
                       file_name="hoja_pago.csv", mime="text/csv")

st.divider()

# --- Detalle ---
st.subheader("Detalle de operaciones con comisiones")
if dff.empty:
    st.info("No hay datos para mostrar.")
else:
    detalle_cols = ["cod_operacion", "fecha", "agente", "tipo", "estado",
                    "precio_operacion", "comision_total"]
    detalle = dff.copy()
    for c in detalle_cols:
        if c not in detalle.columns:
            detalle[c] = None
    detalle = detalle[detalle_cols].sort_values("fecha", ascending=False)
    for col_money in ["precio_operacion", "comision_total"]:
        detalle[col_money] = pd.to_numeric(detalle[col_money], errors="coerce").fillna(0.0).map(lambda x: f"€{x:,.0f}")
    st.dataframe(detalle, use_container_width=True, hide_index=True)
