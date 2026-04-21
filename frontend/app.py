"""
Dashboard de exportaciones — Streamlit
"""
import os

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import requests
import streamlit as st

API_BASE = os.getenv("API_BASE_URL", "http://localhost:8000/api/v1")

_ISO2_TO_ISO3 = {
    "AF":"AFG","AL":"ALB","DZ":"DZA","AD":"AND","AO":"AGO","AG":"ATG","AR":"ARG","AM":"ARM",
    "AU":"AUS","AT":"AUT","AZ":"AZE","BS":"BHS","BH":"BHR","BD":"BGD","BB":"BRB","BY":"BLR",
    "BE":"BEL","BZ":"BLZ","BJ":"BEN","BT":"BTN","BO":"BOL","BA":"BIH","BW":"BWA","BR":"BRA",
    "BN":"BRN","BG":"BGR","BF":"BFA","BI":"BDI","CV":"CPV","KH":"KHM","CM":"CMR","CA":"CAN",
    "CF":"CAF","TD":"TCD","CL":"CHL","CN":"CHN","CO":"COL","KM":"COM","CG":"COG","CD":"COD",
    "CR":"CRI","HR":"HRV","CU":"CUB","CY":"CYP","CZ":"CZE","DK":"DNK","DJ":"DJI","DM":"DMA",
    "DO":"DOM","EC":"ECU","EG":"EGY","SV":"SLV","GQ":"GNQ","ER":"ERI","EE":"EST","SZ":"SWZ",
    "ET":"ETH","FJ":"FJI","FI":"FIN","FR":"FRA","GA":"GAB","GM":"GMB","GE":"GEO","DE":"DEU",
    "GH":"GHA","GR":"GRC","GD":"GRD","GT":"GTM","GN":"GIN","GW":"GNB","GY":"GUY","HT":"HTI",
    "HN":"HND","HU":"HUN","IS":"ISL","IN":"IND","ID":"IDN","IR":"IRN","IQ":"IRQ","IE":"IRL",
    "IL":"ISR","IT":"ITA","JM":"JAM","JP":"JPN","JO":"JOR","KZ":"KAZ","KE":"KEN","KI":"KIR",
    "KW":"KWT","KG":"KGZ","LA":"LAO","LV":"LVA","LB":"LBN","LS":"LSO","LR":"LBR","LY":"LBY",
    "LI":"LIE","LT":"LTU","LU":"LUX","MG":"MDG","MW":"MWI","MY":"MYS","MV":"MDV","ML":"MLI",
    "MT":"MLT","MH":"MHL","MR":"MRT","MU":"MUS","MX":"MEX","FM":"FSM","MD":"MDA","MC":"MCO",
    "MN":"MNG","ME":"MNE","MA":"MAR","MZ":"MOZ","MM":"MMR","NA":"NAM","NR":"NRU","NP":"NPL",
    "NL":"NLD","NZ":"NZL","NI":"NIC","NE":"NER","NG":"NGA","NO":"NOR","OM":"OMN","PK":"PAK",
    "PW":"PLW","PA":"PAN","PG":"PNG","PY":"PRY","PE":"PER","PH":"PHL","PL":"POL","PT":"PRT",
    "PR":"PRI","QA":"QAT","RO":"ROU","RU":"RUS","RW":"RWA","KN":"KNA","LC":"LCA","VC":"VCT",
    "WS":"WSM","SM":"SMR","ST":"STP","SA":"SAU","SN":"SEN","RS":"SRB","SC":"SYC","SL":"SLE",
    "SG":"SGP","SK":"SVK","SI":"SVN","SB":"SLB","SO":"SOM","ZA":"ZAF","SS":"SSD","ES":"ESP",
    "LK":"LKA","SD":"SDN","SR":"SUR","SE":"SWE","CH":"CHE","SY":"SYR","TW":"TWN","TJ":"TJK",
    "TZ":"TZA","TH":"THA","TL":"TLS","TG":"TGO","TO":"TON","TT":"TTO","TN":"TUN","TR":"TUR",
    "TM":"TKM","TV":"TUV","UG":"UGA","UA":"UKR","AE":"ARE","GB":"GBR","US":"USA","UY":"URY",
    "UZ":"UZB","VU":"VUT","VE":"VEN","VN":"VNM","YE":"YEM","ZM":"ZMB","ZW":"ZWE","KR":"KOR",
    "KP":"PRK","TZ":"TZA","BO":"BOL","VE":"VEN",
}


def iso2_to_iso3(code: str) -> str:
    return _ISO2_TO_ISO3.get(str(code).upper(), code) if code else code

st.set_page_config(
    page_title="Análisis de Exportaciones DIAN",
    page_icon="📦",
    layout="wide",
    initial_sidebar_state="expanded",
)

st.markdown("""
<style>
.metric-card {
    background: #f0f2f6; border-radius: 8px;
    padding: 16px; text-align: center;
}
</style>
""", unsafe_allow_html=True)


@st.cache_data(ttl=300)
def fetch(endpoint: str, params: dict = None):
    try:
        r = requests.get(f"{API_BASE}{endpoint}", params=params, timeout=15)
        r.raise_for_status()
        return r.json()
    except Exception as e:
        st.error(f"Error conectando a la API: {e}")
        return None

# ─── Header ─────────────────────────────────────────────────────────────────
st.title("Dashboard de Exportaciones DIAN")
st.caption("Formulario 600 — Oct / Nov / Dic 2025")
st.markdown("---")

# ─── KPIs Globales ──────────────────────────────────────────────────────────
metricas = fetch("/metricas")
if metricas:
    c1, c2, c3, c4, c5 = st.columns(5)
    c1.metric("Total Declaraciones", f"{metricas['total_declaraciones']:,}")
    c2.metric("Empresas Exportadoras", f"{metricas['total_empresas']:,}")
    c3.metric("Países Destino", f"{metricas['total_paises_destino']:,}")
    c4.metric("FOB Total (USD)", f"${metricas['fob_total_usd']:,.0f}")
    c5.metric("Peso Total (Ton)", f"{metricas['peso_total_kg'] / 1000:,.1f}")

st.markdown("---")

# ─── Tabs ───────────────────────────────────────────────────────────────────
tab1, tab2, tab3, tab4 = st.tabs([
    "🏆 Top Empresas", "📈 Tendencia Mensual",
    "🌍 Países Destino", "📋 Declaraciones",
])

# ── Tab 1: Top Empresas ─────────────────────────────────────────────────────
with tab1:
    st.subheader("Top 10 Empresas por FOB Exportado")
    n_empresas = st.slider("Número de empresas", 5, 50, 10)

    data = fetch("/empresas/top", {"limit": n_empresas})
    if data:
        df = pd.DataFrame(data)
        df["fob_total_usd_M"] = df["fob_total_usd"] / 1e6

        fig = px.bar(
            df, x="fob_total_usd_M", y="razon_social",
            orientation="h", text_auto=".2f",
            labels={"fob_total_usd_M": "FOB (Millones USD)", "razon_social": "Empresa"},
            title="FOB Total Exportado por Empresa (Millones USD)",
            color="fob_total_usd_M",
            color_continuous_scale="Blues",
        )
        fig.update_layout(yaxis={"categoryorder": "total ascending"}, height=500)
        st.plotly_chart(fig, use_container_width=True)

        col1, col2 = st.columns(2)
        with col1:
            fig2 = px.scatter(
                df, x="total_declaraciones", y="fob_total_usd_M",
                size="paises_destino", hover_name="razon_social",
                labels={
                    "total_declaraciones": "Nº Declaraciones",
                    "fob_total_usd_M": "FOB (M USD)",
                    "paises_destino": "Países destino",
                },
                title="Declaraciones vs FOB",
            )
            st.plotly_chart(fig2, use_container_width=True)

        with col2:
            fig3 = px.pie(
                df, values="fob_total_usd", names="razon_social",
                title="Participación en FOB Total",
            )
            fig3.update_traces(textposition="inside", textinfo="percent+label")
            st.plotly_chart(fig3, use_container_width=True)

        st.dataframe(
            df[["nit", "razon_social", "total_declaraciones", "fob_total_usd",
                "peso_total_kg", "paises_destino", "primera_exportacion", "ultima_exportacion"]]
            .rename(columns={
                "fob_total_usd": "FOB USD", "peso_total_kg": "Peso KG",
                "total_declaraciones": "Declaraciones", "paises_destino": "Países",
            })
            .style.format({"FOB USD": "${:,.0f}", "Peso KG": "{:,.0f}"}),
            use_container_width=True,
        )

# ── Tab 2: Tendencia Mensual ─────────────────────────────────────────────────
with tab2:
    st.subheader("Tendencia Mensual de Exportaciones")

    col_f, col_t = st.columns(2)
    pais_filter = col_f.text_input("Filtrar por país (ISO 2 o nombre)", "").upper() or None
    modo_filter = col_t.text_input("Filtrar por modo transporte (ej: aéreo, marítimo)", "") or None

    tendencia = fetch("/tendencia/mensual", {
        k: v for k, v in {"pais_destino": pais_filter, "modo_transporte": modo_filter}.items()
        if v
    })

    if tendencia:
        df_t = pd.DataFrame(tendencia)
        df_t["mes"] = pd.to_datetime(df_t["mes"])

        # Agrupar si hay múltiples destinos
        df_agg = df_t.groupby("mes").agg(
            fob_usd=("fob_usd", "sum"),
            declaraciones=("declaraciones", "sum"),
            peso_kg=("peso_kg", "sum"),
        ).reset_index()

        fig_t = go.Figure()
        fig_t.add_trace(go.Bar(
            x=df_agg["mes"], y=df_agg["fob_usd"] / 1e6,
            name="FOB (M USD)", marker_color="#1f77b4",
        ))
        fig_t.add_trace(go.Scatter(
            x=df_agg["mes"], y=df_agg["declaraciones"],
            name="Declaraciones", yaxis="y2", line=dict(color="#ff7f0e"),
        ))
        fig_t.update_layout(
            title="FOB mensual vs Número de Declaraciones",
            yaxis=dict(title="FOB (M USD)"),
            yaxis2=dict(title="Declaraciones", overlaying="y", side="right"),
            legend=dict(x=0.01, y=0.99),
            hovermode="x unified",
        )
        st.plotly_chart(fig_t, use_container_width=True)

        if not pais_filter:
            st.subheader("FOB por País Destino (acumulado)")
            df_pais = (
                df_t.groupby(["pais_destino"])["fob_usd"]
                .sum()
                .sort_values(ascending=False)
                .head(15)
                .reset_index()
            )
            fig_p = px.bar(
                df_pais, x="pais_destino", y="fob_usd",
                title="Top 15 Países por FOB",
                labels={"fob_usd": "FOB USD", "pais_destino": "País"},
                color="fob_usd", color_continuous_scale="Viridis",
            )
            st.plotly_chart(fig_p, use_container_width=True)

# ── Tab 3: Países Destino ────────────────────────────────────────────────────
with tab3:
    st.subheader("Distribución por País Destino")
    paises = fetch("/analisis/paises", {"top_n": 30})
    if paises:
        df_p = pd.DataFrame(paises)
        df_p["iso3"] = df_p["cod_pais_destino"].map(iso2_to_iso3)
        fig_map = px.choropleth(
            df_p, locations="iso3",
            color="fob_usd", hover_name="pais_destino",
            color_continuous_scale="Blues",
            title="Mapa de calor — FOB exportado por destino",
            labels={"fob_usd": "FOB USD"},
        )
        st.plotly_chart(fig_map, use_container_width=True)

        col1, col2 = st.columns(2)
        with col1:
            fig_bar = px.bar(
                df_p.head(15), x="cod_pais_destino", y="fob_usd",
                title="Top 15 Países por FOB",
                labels={"fob_usd": "FOB USD", "cod_pais_destino": "País"},
                color="fob_usd", color_continuous_scale="Blues",
            )
            st.plotly_chart(fig_bar, use_container_width=True)
        with col2:
            st.subheader("Top subpartidas arancelarias")
            subs = fetch("/analisis/subpartidas", {"top_n": 15})
            if subs:
                df_s = pd.DataFrame(subs)
                df_s["etiqueta"] = df_s.apply(
                    lambda r: f"{r['descripcion_corta']}<br><sup>{r['subpartida']}</sup>"
                    if r.get("descripcion_corta") else r["subpartida"],
                    axis=1,
                )
                fig_s = px.treemap(
                    df_s, path=["etiqueta"], values="fob_usd",
                    title="Subpartidas por FOB",
                    color="fob_usd", color_continuous_scale="RdYlGn",
                    hover_data={"subpartida": True, "lineas": True, "fob_usd": ":.0f"},
                )
                st.plotly_chart(fig_s, use_container_width=True)

# ── Tab 4: Declaraciones ─────────────────────────────────────────────────────
with tab4:
    st.subheader("Búsqueda de Declaraciones")

    col1, col2, col3, col4 = st.columns(4)
    nit_q = col1.text_input("NIT exportador") or None
    pais_q = col2.text_input("País destino (ISO 2 o nombre)").upper() or None
    f_desde = col3.date_input("Desde", value=None)
    f_hasta = col4.date_input("Hasta", value=None)

    params = {k: v for k, v in {
        "nit": nit_q, "pais": pais_q,
        "fecha_desde": str(f_desde) if f_desde else None,
        "fecha_hasta": str(f_hasta) if f_hasta else None,
        "page_size": 100,
    }.items() if v}

    result = fetch("/declaraciones", params)
    if result:
        st.info(f"Total encontrado: {result['total']:,} declaraciones")
        df_decl = pd.DataFrame(result["data"])
        if not df_decl.empty:
            st.dataframe(
                df_decl.style.format({"valor_fob_usd": "${:,.2f}", "total_peso_bruto_kg": "{:,.1f}"}),
                use_container_width=True,
                height=400,
            )
