# app.py
import streamlit as st
from pathlib import Path
import os
from dotenv import load_dotenv  # para cargar .env en local
from parser.xml_loader import load_folder_to_dfs, load_zip_to_dfs
from parser.transform import build_all_resumenes

st.set_page_config(page_title="Inmo Dashboard", layout="wide")

# ---------------- Cargar secretos ----------------
# En local: .env | En producción (Streamlit Cloud): st.secrets
load_dotenv()
PASSWORD = os.getenv("DASHBOARD_PASSWORD") or st.secrets.get("DASHBOARD_PASSWORD", "")

# ---------------- Autenticación simple ----------------
if "auth" not in st.session_state:
    st.session_state["auth"] = False

if not st.session_state["auth"]:
    st.title("🔐 Inmo Dashboard – Acceso")
    pwd = st.text_input("Introduce la contraseña para acceder:", type="password", placeholder="•••••••••••••")
    col_a, col_b = st.columns([1, 3])
    if col_a.button("Entrar"):
        if pwd == PASSWORD:
            st.session_state["auth"] = True
            st.rerun()
        else:
            st.error("❌ Contraseña incorrecta.")
    st.stop()

# ---------------- Portada explicativa ----------------
st.title("🏠 Inmo Dashboard (Versión de prueba)")

st.markdown(
    """
    Bienvenido a **Inmo Dashboard**, una herramienta diseñada para dar
    **visibilidad inmediata** al trabajo comercial de la inmobiliaria.

    ### 📌 ¿Qué encontrará en cada apartado?
    - **Captaciones** → seguimiento de las viviendas captadas, clasificadas por tipo
      de operación (*venta, alquiler, vacacional*), con evolución mensual y comparativa
      entre agentes.
    - **Demandas** → análisis de las demandas registradas, mostrando su evolución
      en el tiempo y quiénes son los agentes responsables de cada captación.
    - **Comisiones** → desglose de las comisiones generadas por agente y por periodo,
      con posibilidad de descargar una hoja de pago mensual lista para usarse.

    ### 🚀 Cómo usar esta versión
    Esta versión de prueba ya tiene integrados los datos de ejemplo.
    Solo hay que **esperar a que aparezca el aviso de que los datos han sido cargados**.
    A partir de ahí podrá navegar por las páginas de la izquierda (*Captaciones, Demandas,
    Comisiones*) y explorar los indicadores.

    ### 🔄 Objetivo de esta demo
    Esta es una **versión inicial de prueba**, preparada para mostrar la propuesta de valor
    y recoger feedback.  
    La idea es validar si la estructura, gráficos y métricas cumplen con las necesidades del
    equipo, para después ajustar y evolucionar la herramienta según sus comentarios.
    """
)

# ---------------- Estado de datos ----------------
if "resumenes" not in st.session_state:
    st.session_state["resumenes"] = None

datos_dir = Path("datos")
loaded_from = None

# 1) Intentar cargar desde carpeta 'datos/' si hay XML
if st.session_state["resumenes"] is None and datos_dir.exists() and any(datos_dir.glob("*.xml")):
    with st.spinner("⏳ Cargando datos de prueba..."):
        dfs_raw = load_folder_to_dfs(datos_dir)
        resumenes = build_all_resumenes(
            dfs_raw.get("inmuebles"),
            dfs_raw.get("demandas"),
            dfs_raw.get("operaciones"),
        )
        st.session_state["resumenes"] = resumenes
        loaded_from = "carpeta"

# 2) Alternativa: subir ZIP manual
if st.session_state["resumenes"] is None:
    uploaded_file = st.file_uploader(
        "📂 Si desea, puede subir un archivo ZIP de datos",
        type="zip"
    )
    if uploaded_file:
        with st.spinner("⏳ Procesando ZIP..."):
            dfs_raw = load_zip_to_dfs(uploaded_file)
            resumenes = build_all_resumenes(
                dfs_raw.get("inmuebles"),
                dfs_raw.get("demandas"),
                dfs_raw.get("operaciones"),
            )
            st.session_state["resumenes"] = resumenes
            loaded_from = "zip"

# Mensajes de estado
if st.session_state["resumenes"] is not None:
    st.success("✅ Los datos se han cargado correctamente. Ya puede navegar por las páginas de la izquierda.")
else:
    st.info("ℹ️ Espere a que aparezca la confirmación de carga de datos antes de navegar por el panel.")
