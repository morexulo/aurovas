# pages/1_Captaciones.py
import streamlit as st
import pandas as pd
import plotly.express as px
from datetime import date

st.title("📊 Captaciones")

# --- Validación de datos en memoria ---
res = st.session_state.get("resumenes")
if not res or "captaciones" not in res:
    st.warning("⚠️ Sube primero un ZIP desde la pestaña 'Inicio'.")
    st.stop()

df = res["captaciones"].copy()

# --- Preparación de fecha mensual (1º de cada mes) ---
df["fecha"] = pd.to_datetime(
    dict(year=df["año"].astype(int), month=df["mes"].astype(int), day=1),
    errors="coerce"
)

# --- Filtros superiores (no en sidebar) ---
with st.container():
    # Defaults centrados en las agentes clave si existen
    agentes_all = sorted(df["agente"].dropna().unique().tolist())
    preferidas = [a for a in agentes_all if any(x in a for x in ["Bibiana", "Pati", "Teresa"])]
    default_agentes = preferidas if preferidas else agentes_all

    tipos_all = sorted(df["tipo"].dropna().unique().tolist())
    col_f1, col_f2, col_f3 = st.columns([2, 2, 3])

    agentes_sel = col_f1.multiselect("Agentes", agentes_all, default=default_agentes)
    tipos_sel = col_f2.multiselect("Tipo de operación", tipos_all, default=tipos_all)

    min_d = df["fecha"].min()
    max_d = df["fecha"].max()
    if pd.isna(min_d) or pd.isna(max_d):
        st.error("No hay fechas válidas en las captaciones.")
        st.stop()
    # Selector de rango de meses (usa fechas)
    fecha_ini, fecha_fin = col_f3.date_input(
        "Rango de meses",
        value=(date(2025, 1, 1), max_d.date()),
        min_value=date(2025, 1, 1),
        max_value=max_d.date(),
    )

# --- Aplicar filtros ---
mask = (
    df["agente"].isin(agentes_sel)
    & df["tipo"].isin(tipos_sel)
    & (df["fecha"] >= pd.to_datetime(fecha_ini))
    & (df["fecha"] <= pd.to_datetime(fecha_fin))
)
df_f = df.loc[mask].copy()

# --- KPIs ---
col_k1, col_k2, col_k3, col_k4 = st.columns(4)
total_sel = int(df_f["num_inmuebles"].sum()) if not df_f.empty else 0

# último mes dentro del rango filtrado
if df_f.empty:
    ult_mes_total = 0
    ytd_total = 0
    media_mensual = 0
else:
    ult_mes = df_f["fecha"].max()
    ult_mes_total = int(df_f.loc[df_f["fecha"] == ult_mes, "num_inmuebles"].sum())
    # YTD del año del último mes seleccionado
    ytd_mask = (df_f["fecha"].dt.year == ult_mes.year)
    ytd_total = int(df_f.loc[ytd_mask, "num_inmuebles"].sum())
    # media mensual del rango
    meses_unicos = df_f["fecha"].dt.to_period("M").nunique()
    media_mensual = round(total_sel / meses_unicos, 1) if meses_unicos else 0

col_k1.metric("Total captaciones (filtro)", total_sel)
col_k2.metric("Captaciones último mes", ult_mes_total)
col_k3.metric(f"Captaciones YTD ({ult_mes.year if not df_f.empty else ''})", ytd_total)
col_k4.metric("Media mensual", media_mensual)

st.divider()

# --- Gráfico 1: Evolución mensual (área apilada por tipo) ---
st.subheader("Evolución mensual por tipo")
if df_f.empty:
    st.info("No hay datos para los filtros seleccionados.")
else:
    evol = (
        df_f.groupby(["fecha", "tipo"], as_index=False)["num_inmuebles"].sum()
        .sort_values("fecha")
    )
    fig_area = px.area(
        evol,
        x="fecha",
        y="num_inmuebles",
        color="tipo",
        line_group="tipo",
        markers=False,
        title=None,
        labels={"fecha": "Mes", "num_inmuebles": "Nº de inmuebles", "tipo": "Tipo"},
    )
    fig_area.update_layout(legend_title_text="Tipo de operación", height=420, margin=dict(t=10, b=10))
    st.plotly_chart(fig_area, use_container_width=True)

st.divider()

# --- Gráfico 2: Comparativa por agente (barras agrupadas por mes) ---
st.subheader("Comparativa mensual por agente")
if df_f.empty:
    st.info("No hay datos para los filtros seleccionados.")
else:
    comp = (
        df_f.groupby(["fecha", "agente"], as_index=False)["num_inmuebles"].sum()
        .sort_values(["fecha", "agente"])
    )
    fig_bar = px.bar(
        comp,
        x="fecha",
        y="num_inmuebles",
        color="agente",
        barmode="group",
        title=None,
        labels={"fecha": "Mes", "num_inmuebles": "Nº de inmuebles", "agente": "Agente"},
    )
    fig_bar.update_layout(legend_title_text="Agente", height=420, margin=dict(t=10, b=10))
    st.plotly_chart(fig_bar, use_container_width=True)

st.divider()

# --- Gráfico 3: Reparto por tipo (donut) sobre el rango filtrado ---
st.subheader("Reparto por tipo en el periodo seleccionado")
if df_f.empty:
    st.info("No hay datos para los filtros seleccionados.")
else:
    by_tipo = df_f.groupby("tipo", as_index=False)["num_inmuebles"].sum()
    fig_pie = px.pie(
        by_tipo,
        names="tipo",
        values="num_inmuebles",
        hole=0.5,
        title=None,
    )
    fig_pie.update_layout(legend_title_text="Tipo", height=380, margin=dict(t=10, b=10))
    col_p1, col_p2 = st.columns([2, 3])
    col_p1.plotly_chart(fig_pie, use_container_width=True)

# --- Detalle en tabla ---
st.subheader("Detalle de captaciones")
if df_f.empty:
    st.info("No hay datos para mostrar.")
else:
    orden = df_f.sort_values(["fecha", "agente", "tipo"], ascending=[False, True, True]).reset_index(drop=True)
    # columnas ordenadas y legibles
    cols = ["fecha", "año", "mes", "agente", "tipo", "num_inmuebles"]
    cols = [c for c in cols if c in orden.columns]
    st.dataframe(orden[cols], use_container_width=True, hide_index=True)
