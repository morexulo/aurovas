# pages/3_Comisiones.py
import streamlit as st
import pandas as pd
import plotly.express as px
from datetime import date

st.title("💰 Comisiones")

# --- Validación de datos ---
res = st.session_state.get("resumenes")
if not res or "comisiones" not in res:
    st.warning("⚠️ Sube primero un ZIP desde la pestaña 'Inicio'.")
    st.stop()

df = res["comisiones"].copy()  # resumen mensual por agente (sin 'tipo')
df_ops = res.get("operaciones_limpio")  # operaciones detalladas (con 'tipo' si existe)

# --- Preparación ---
df["fecha"] = pd.to_datetime(
    dict(year=df["año"].astype(int), month=df["mes"].astype(int), day=1),
    errors="coerce"
)

# --- Filtros ---
with st.container():
    agentes_all = sorted(df["agente"].dropna().unique().tolist())
    preferidas = [a for a in agentes_all if any(x in a for x in ["Bibiana", "Pati", "Teresa"])]
    default_agentes = preferidas if preferidas else agentes_all

    col_f1, col_f2 = st.columns([2, 3])
    agentes_sel = col_f1.multiselect("Agentes", agentes_all, default=default_agentes)

    min_d, max_d = df["fecha"].min(), df["fecha"].max()
    if pd.isna(min_d) or pd.isna(max_d):
        st.error("No hay fechas válidas en comisiones.")
        st.stop()

    fecha_ini, fecha_fin = col_f2.date_input(   
        "Rango de meses",
        value=(date(2025, 8, 1), date(2025, 8, 1)),  # valor inicial marcado
        min_value=df["fecha"].min().date(),           # límite inferior dinámico
        max_value=df["fecha"].max().date(),           # límite superior dinámico
    )

# --- Aplicar filtros (para ranking/tablas) ---
mask = (
    df["agente"].isin(agentes_sel)
    & (df["fecha"] >= pd.to_datetime(fecha_ini))
    & (df["fecha"] <= pd.to_datetime(fecha_fin))
)
df_f = df.loc[mask].copy()

# --- KPIs ---
col_k1, col_k2, col_k3, col_k4, col_k5 = st.columns(5)
if df_f.empty:
    total_sel = ult_mes_total = n_ops = media_por_op = mejor_mes_val = 0
    mejor_mes = "-"
else:
    total_sel = float(df_f["comision_total"].sum())
    ult_mes = df_f["fecha"].max()
    ult_mes_total = float(df_f.loc[df_f["fecha"] == ult_mes, "comision_total"].sum())
    n_ops = len(df_f)
    media_por_op = float(total_sel / n_ops) if n_ops else 0
    idx_mejor = df_f.groupby("fecha")["comision_total"].sum().idxmax()
    mejor_mes_val = float(df_f.groupby("fecha")["comision_total"].sum().max())
    mejor_mes = idx_mejor.strftime("%b %Y")

col_k1.metric("Comisión total", f"€{total_sel:,.0f}")
col_k2.metric("Último mes", f"€{ult_mes_total:,.0f}")
col_k3.metric("Nº operaciones", n_ops)
col_k4.metric("Media por operación", f"€{media_por_op:,.0f}")
col_k5.metric("Mejor mes", f"{mejor_mes} (€{mejor_mes_val:,.0f})")

st.divider()

# --- Ranking de agentes ---
st.subheader("Ranking de comisiones por agente")
if df_f.empty:
    st.info("No hay datos para los filtros seleccionados.")
else:
    by_agente = df_f.groupby("agente", as_index=False)["comision_total"].sum()
    by_agente = by_agente.sort_values("comision_total", ascending=True)

    fig_rank = px.bar(
        by_agente,
        x="comision_total",
        y="agente",
        orientation="h",
        text="comision_total",
        labels={"comision_total": "Comisión (€)", "agente": "Agente"},
    )
    fig_rank.update_traces(texttemplate="€%{text:,.0f}", textposition="outside")
    fig_rank.update_layout(height=400, margin=dict(t=10, b=10))
    st.plotly_chart(fig_rank, use_container_width=True)

    # Tabla resumen
    resumen = df_f.groupby("agente").agg(
        total_comision=("comision_total", "sum"),
        num_ops=("comision_total", "count"),
        media_op=("comision_total", "mean"),
    ).reset_index()
    resumen["total_comision"] = resumen["total_comision"].map(lambda x: f"€{x:,.0f}")
    resumen["media_op"] = resumen["media_op"].map(lambda x: f"€{x:,.0f}")
    st.dataframe(resumen, use_container_width=True, hide_index=True)

st.divider()

# --- Donut (agentes, todos los usuarios) + Donut (tipos generales) ---
st.subheader("Distribución general de comisiones en el periodo")
col1, col2 = st.columns(2)

# Donut por AGENTE (todos los agentes; solo filtro de fechas)
with col1:
    if df.empty:
        st.info("No hay datos disponibles.")
    else:
        df_periodo = df.loc[
            (df["fecha"] >= pd.to_datetime(fecha_ini)) &
            (df["fecha"] <= pd.to_datetime(fecha_fin))
        ].copy()
        if df_periodo.empty:
            st.info("Sin comisiones en el rango seleccionado.")
        else:
            share = df_periodo.groupby("agente", as_index=False)["comision_total"].sum()
            fig_share = px.pie(
                share,
                names="agente",
                values="comision_total",
                hole=0.5,
            )
            fig_share.update_traces(
                texttemplate="%{label}<br>€%{value:,.0f} (%{percent})",
                hovertemplate="%{label}<br>€%{value:,.0f} (%{percent})<extra></extra>",
                textposition="inside"
            )
            fig_share.update_layout(height=380, margin=dict(t=10, b=10))
            st.plotly_chart(fig_share, use_container_width=True, key="donut_agentes")

# Donut por TIPO (usa operaciones_limpio para tener 'tipo'; solo filtro de fechas)
with col2:
    if df_ops is None or "tipo" not in df_ops.columns:
        st.caption("No hay información de tipo de operación disponible.")
    else:
        ops_periodo = df_ops.loc[
            (df_ops["fecha"] >= pd.to_datetime(fecha_ini)) &
            (df_ops["fecha"] <= pd.to_datetime(fecha_fin))
        ].copy()
        if ops_periodo.empty or ops_periodo["tipo"].dropna().empty:
            st.info("No hay datos de tipos en este rango.")
        else:
            by_tipo = ops_periodo.groupby("tipo", as_index=False)["comision_total"].sum()
            fig_tipo = px.pie(
                by_tipo,
                names="tipo",
                values="comision_total",
                hole=0.5,
            )
            fig_tipo.update_traces(
                texttemplate="%{label}<br>€%{value:,.0f} (%{percent})",
                hovertemplate="%{label}<br>€%{value:,.0f} (%{percent})<extra></extra>",
                textposition="inside"
            )
            fig_tipo.update_layout(height=380, margin=dict(t=10, b=10))
            st.plotly_chart(fig_tipo, use_container_width=True, key="donut_tipos")

st.divider()

# --- Hoja de pago ---
st.subheader("Hoja de pago (mensual por agente)")
if df_f.empty:
    st.info("No hay datos para mostrar.")
else:
    pivot = df_f.pivot_table(
        index=df_f["fecha"].dt.to_period("M"),
        columns="agente",
        values="comision_total",
        aggfunc="sum",
        fill_value=0,
    ).sort_index(ascending=False)

    pivot_display = pivot.copy()
    for c in pivot_display.columns:
        pivot_display[c] = pivot_display[c].map(lambda x: f"€{x:,.0f}")

    st.dataframe(pivot_display, use_container_width=True)

    csv = pivot.to_csv().encode("utf-8")
    st.download_button(
        "⬇️ Descargar hoja de pago (CSV)",
        data=csv,
        file_name="hoja_pago.csv",
        mime="text/csv",
    )

st.divider()

# --- Detalle de operaciones ---
st.subheader("Detalle de operaciones con comisiones")
if df_f.empty:
    st.info("No hay datos para mostrar.")
else:
    detalle = df_f.sort_values("fecha", ascending=False).copy()
    detalle["comision_total"] = detalle["comision_total"].map(lambda x: f"€{x:,.0f}")
    st.dataframe(detalle, use_container_width=True, hide_index=True)
