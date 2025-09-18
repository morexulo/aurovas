# pages/2_Demandas.py
import streamlit as st
import pandas as pd
import plotly.express as px
from datetime import timedelta

st.title("📈 Demandas")

# --- Validación de datos ---
res = st.session_state.get("resumenes")
if not res or "demandas" not in res:
    st.warning("⚠️ Sube primero un ZIP desde la pestaña 'Inicio'.")
    st.stop()

df = res["demandas"].copy()
df["fecha"] = pd.to_datetime(
    dict(year=df["año"].astype(int), month=df["mes"].astype(int), day=1),
    errors="coerce"
)

# --- Filtros superiores ---
agentes_all = sorted(df["agente"].dropna().unique().tolist())
agentes_sel = st.multiselect("Agentes", agentes_all, default=agentes_all)

tipos_all = sorted(df["tipo"].dropna().unique().tolist())
tipos_sel = st.multiselect("Tipo de operación", tipos_all, default=tipos_all)

min_d, max_d = df["fecha"].min(), df["fecha"].max()
if pd.isna(min_d) or pd.isna(max_d):
    st.error("No hay fechas válidas en las demandas.")
    st.stop()

# Rango por defecto: últimos 30 días
ultimo_fin = max_d.date()
ultimo_ini = (max_d - timedelta(days=60)).date()
if ultimo_ini < min_d.date():
    ultimo_ini = min_d.date()

fi, ff = st.date_input(
    "Rango de fechas",
    value=(ultimo_ini, ultimo_fin),
    min_value=min_d.date(),
    max_value=max_d.date(),
)

# --- Aplicar filtros ---
mask = (
    df["agente"].isin(agentes_sel)
    & df["tipo"].isin(tipos_sel)
    & (df["fecha"] >= pd.to_datetime(fi))
    & (df["fecha"] <= pd.to_datetime(ff))
)
df_f = df.loc[mask].copy()

# --- KPIs ---
k1, k2, k3, k4 = st.columns(4)
total_sel = int(df_f["num_demandas"].sum()) if not df_f.empty else 0
if df_f.empty:
    ult_mes_total = ytd_total = 0
    media_mensual = 0
    año_ref = ""
else:
    ult_mes = df_f["fecha"].max()
    ult_mes_total = int(df_f.loc[df_f["fecha"] == ult_mes, "num_demandas"].sum())
    año_ref = ult_mes.year
    ytd_total = int(df_f.loc[df_f["fecha"].dt.year == año_ref, "num_demandas"].sum())
    meses_unicos = df_f["fecha"].dt.to_period("M").nunique()
    media_mensual = round(total_sel / meses_unicos, 1) if meses_unicos else 0

k1.metric("Total demandas (filtro)", total_sel)
k2.metric("Demandas último mes", ult_mes_total)
k3.metric(f"Demandas YTD ({año_ref})", ytd_total)
k4.metric("Media mensual", media_mensual)

st.divider()

# --- Evolución mensual por tipo ---
st.subheader("Evolución mensual por tipo")
if df_f.empty:
    st.info("No hay datos para los filtros seleccionados.")
else:
    evol = (
        df_f.groupby(["fecha", "tipo"], as_index=False)["num_demandas"].sum()
        .sort_values("fecha")
    )
    fig_area = px.area(
        evol,
        x="fecha",
        y="num_demandas",
        color="tipo",
        labels={"fecha": "Mes", "num_demandas": "Nº de demandas", "tipo": "Tipo"},
    )
    fig_area.update_layout(legend_title_text="Tipo de operación", height=420, margin=dict(t=10, b=10))
    st.plotly_chart(fig_area, use_container_width=True)

st.divider()

# --- Comparativa mensual por agente ---
st.subheader("Comparativa mensual por agente")
if df_f.empty:
    st.info("No hay datos para los filtros seleccionados.")
else:
    comp = (
        df_f.groupby(["fecha", "agente"], as_index=False)["num_demandas"].sum()
        .sort_values(["fecha", "agente"])
    )
    fig_bar = px.bar(
        comp,
        x="fecha",
        y="num_demandas",
        color="agente",
        barmode="group",
        text="num_demandas",  # <-- mostrar números
        labels={"fecha": "Mes", "num_demandas": "Nº de demandas", "agente": "Agente"},
    )
    fig_bar.update_traces(
        texttemplate="%{text}",
        textposition="outside"
    )
    fig_bar.update_layout(legend_title_text="Agente", height=420, margin=dict(t=10, b=10))
    st.plotly_chart(fig_bar, use_container_width=True)

st.divider()

# --- Reparto por tipo en el periodo ---
st.subheader("Reparto por tipo en el periodo seleccionado")
if df_f.empty:
    st.info("No hay datos para los filtros seleccionados.")
else:
    by_tipo = df_f.groupby("tipo", as_index=False)["num_demandas"].sum()
    fig_pie = px.pie(by_tipo, names="tipo", values="num_demandas", hole=0.5)
    fig_pie.update_layout(legend_title_text="Tipo", height=380, margin=dict(t=10, b=10))
    st.plotly_chart(fig_pie, use_container_width=True)

# --- Detalle ---
st.subheader("Detalle de demandas")
if df_f.empty:
    st.info("No hay datos para mostrar.")
else:
    orden = df_f.sort_values(["fecha", "agente", "tipo"], ascending=[False, True, True]).reset_index(drop=True)
    cols = ["fecha", "año", "mes", "agente", "tipo", "num_demandas"]
    cols = [c for c in cols if c in orden.columns]
    st.dataframe(orden[cols], use_container_width=True, hide_index=True)
