
import re
import pandas as pd
import streamlit as st

# =========================================================
# AJ | CALCULADORA DE PROPUESTA DE PORTAFOLIO
# Uso: calcular métricas y generar un bloque de datos
# para copiar aquí y crear la imagen final.
# =========================================================

st.set_page_config(
    page_title="AJ | Calculadora Portafolio Deuda",
    layout="wide"
)

st.title("AJ | Calculadora de Propuesta de Portafolio")
st.caption("Calcula los datos finales para copiar y generar la imagen ejecutiva.")

# -----------------------------
# Datos base
# -----------------------------
DEFAULT_GOV = pd.DataFrame(
    [
        ["MBONO 31", 12.5, "Gobierno Federal", "AAA (mx) S&P / Fitch", 3.95, "8.50%", "Semestral"],
        ["MBONO 34", 12.5, "Gobierno Federal", "AAA (mx) S&P / Fitch", 5.82, "9.00%", "Semestral"],
        ["UDIBONO 28", 10.0, "Gobierno Federal", "AAA (mx) S&P / Fitch", 2.36, "UDIS + 3.80%", "Semestral"],
        ["UDIBONO 31", 15.0, "Gobierno Federal", "AAA (mx) S&P / Fitch", 5.01, "UDIS + 4.30%", "Semestral"],
    ],
    columns=[
        "Instrumento",
        "Part. (%)",
        "Emisor",
        "Calificación",
        "Duración",
        "Tasa / Sobretasa",
        "Periodicidad Cupones",
    ],
)

DEFAULT_CORP = pd.DataFrame(
    [
        ["FACTORING", 10.0, "Factoring", "AA (F1 Fitch)", 0.70, "8.30%*", "Mensual"],
        ["PDN", 10.0, "PDN", "AA (F1 Fitch)", 0.85, "8.45%*", "Mensual"],
        ["GM FIN 26-2", 10.0, "GM Financial", "AAA (S&P) / AA+ (Fitch)", 3.41, "9.20%", "Semestral"],
        ["ORBIA 22-2L", 10.0, "Orbia", "AA Fitch", 4.44, "10.15%", "Semestral"],
        ["CABEI 1-25S", 10.0, "CABEI", "AAA (S&P) / Aaa.mx (Moody's)", 2.67, "8.21%", "Mensual"],
    ],
    columns=[
        "Instrumento",
        "Part. (%)",
        "Emisor",
        "Calificación",
        "Duración",
        "Tasa",
        "Periodicidad Cupones",
    ],
)

# -----------------------------
# Funciones
# -----------------------------
def safe_float(value: object) -> float:
    try:
        if pd.isna(value):
            return 0.0
        return float(value)
    except Exception:
        return 0.0


def money(value: float) -> str:
    return f"${value:,.0f}"


def pct(value: float) -> str:
    value = float(value)
    if abs(value - round(value)) < 0.01:
        return f"{value:.0f}%"
    return f"{value:.1f}%"


def extract_rate(rate_text: str):
    """
    Extrae el primer número con % dentro de un texto:
    - 8.30%*
    - 8.45%
    - TIIE + 1.35%  -> extrae 1.35, por eso para tasa total conviene capturar 8.30%*
    - UDIS + 3.80% -> se excluye por contener UDI
    """
    if not isinstance(rate_text, str):
        return None

    match = re.search(r"(\d+(?:\.\d+)?)\s*%", rate_text)
    if match:
        return float(match.group(1))
    return None


def weighted_duration(df: pd.DataFrame) -> float:
    return sum(
        safe_float(row["Part. (%)"]) / 100 * safe_float(row["Duración"])
        for _, row in df.iterrows()
    )


def average_duration_by_block(df: pd.DataFrame) -> float:
    total_weight = df["Part. (%)"].astype(float).sum() if not df.empty else 0.0
    if total_weight == 0:
        return 0.0
    return weighted_duration(df) / (total_weight / 100)


def weighted_fixed_rate(gov_df: pd.DataFrame, corp_df: pd.DataFrame):
    """
    Calcula tasa ponderada sobre instrumentos con tasa visible, excluyendo UDIS.
    Regresa:
    - tasa ponderada
    - tabla de cálculo
    - peso considerado
    - suma de aportes
    """
    rows = []

    for _, row in gov_df.iterrows():
        tasa_texto = str(row.get("Tasa / Sobretasa", ""))
        if "UDI" in tasa_texto.upper():
            continue

        tasa_num = extract_rate(tasa_texto)
        if tasa_num is None:
            continue

        peso = safe_float(row.get("Part. (%)", 0))
        rows.append(
            {
                "Tipo": "Gobierno",
                "Instrumento": row.get("Instrumento", ""),
                "Peso %": peso,
                "Tasa capturada": tasa_texto,
                "Tasa numérica": tasa_num,
                "Aporte": peso * tasa_num,
            }
        )

    for _, row in corp_df.iterrows():
        tasa_texto = str(row.get("Tasa", ""))

        tasa_num = extract_rate(tasa_texto)
        if tasa_num is None:
            continue

        peso = safe_float(row.get("Part. (%)", 0))
        rows.append(
            {
                "Tipo": "Corporativo",
                "Instrumento": row.get("Instrumento", ""),
                "Peso %": peso,
                "Tasa capturada": tasa_texto,
                "Tasa numérica": tasa_num,
                "Aporte": peso * tasa_num,
            }
        )

    calc_df = pd.DataFrame(rows)

    if calc_df.empty:
        return 0.0, calc_df, 0.0, 0.0

    peso_considerado = calc_df["Peso %"].sum()
    suma_aportes = calc_df["Aporte"].sum()

    tasa = suma_aportes / peso_considerado if peso_considerado else 0.0

    return tasa, calc_df, peso_considerado, suma_aportes


def add_amounts(df: pd.DataFrame, total_portfolio: float) -> pd.DataFrame:
    df = df.copy()
    df["Monto"] = df["Part. (%)"].astype(float) / 100 * total_portfolio
    return df


def format_table_for_copy(df: pd.DataFrame, rate_column: str) -> str:
    lines = []
    for _, r in df.iterrows():
        lines.append(
            f"{r['Instrumento']} | "
            f"{pct(r['Part. (%)'])} | "
            f"{money(r['Monto'])} | "
            f"{r['Emisor']} | "
            f"{r['Calificación']} | "
            f"{safe_float(r['Duración']):.2f} años | "
            f"{r[rate_column]} | "
            f"{r['Periodicidad Cupones']}"
        )
    return "\n".join(lines)


# -----------------------------
# Sidebar: datos generales
# -----------------------------
with st.sidebar:
    st.header("Datos generales")

    cliente = st.text_input("Cliente", "Salomón Elnecave")
    fecha = st.text_input("Fecha", "10 JUNIO 2026")
    monto_total = st.number_input(
        "Monto total",
        min_value=0.0,
        value=4_000_000.0,
        step=100_000.0,
        format="%.2f",
    )

    asesor = st.text_input("Asesor", "Alberto Jiménez")
    cargo = st.text_input("Cargo", "Asesor Financiero Afiliado GBM")
    estrategia = st.text_input(
        "Estrategia",
        "Renta Fija | Títulos Públicos y Corporativos",
    )

# -----------------------------
# Captura de instrumentos
# -----------------------------
st.subheader("Instrumentos gubernamentales")

gov_input = st.data_editor(
    DEFAULT_GOV,
    num_rows="dynamic",
    use_container_width=True,
    column_config={
        "Part. (%)": st.column_config.NumberColumn("Part. (%)", format="%.2f"),
        "Duración": st.column_config.NumberColumn("Duración", format="%.2f"),
    },
    key="gov_input",
)

st.subheader("Instrumentos corporativos")

corp_input = st.data_editor(
    DEFAULT_CORP,
    num_rows="dynamic",
    use_container_width=True,
    column_config={
        "Part. (%)": st.column_config.NumberColumn("Part. (%)", format="%.2f"),
        "Duración": st.column_config.NumberColumn("Duración", format="%.2f"),
    },
    key="corp_input",
)

# -----------------------------
# Cálculos
# -----------------------------
gov = add_amounts(gov_input, monto_total)
corp = add_amounts(corp_input, monto_total)

gov_pct = gov["Part. (%)"].astype(float).sum() if not gov.empty else 0.0
corp_pct = corp["Part. (%)"].astype(float).sum() if not corp.empty else 0.0
total_pct = gov_pct + corp_pct

gov_amount = monto_total * gov_pct / 100
corp_amount = monto_total * corp_pct / 100

udis_pct = gov[
    gov["Instrumento"].astype(str).str.upper().str.contains("UDI", na=False)
]["Part. (%)"].astype(float).sum() if not gov.empty else 0.0

udis_amount = monto_total * udis_pct / 100

duration_gov_avg = average_duration_by_block(gov)
duration_corp_avg = average_duration_by_block(corp)
duration_weighted = weighted_duration(gov) + weighted_duration(corp)

rate_weighted, rate_calc_df, peso_considerado, suma_aportes = weighted_fixed_rate(gov, corp)

# -----------------------------
# Métricas visuales
# -----------------------------
st.divider()
st.subheader("Resultados calculados")

c1, c2, c3, c4, c5 = st.columns(5)
c1.metric("Gobierno", f"{gov_pct:.2f}%", money(gov_amount))
c2.metric("Corporativos", f"{corp_pct:.2f}%", money(corp_amount))
c3.metric("UDIS", f"{udis_pct:.2f}%", money(udis_amount))
c4.metric("Tasa ponderada", f"{rate_weighted:.2f}%")
c5.metric("Duración ponderada", f"{duration_weighted:.2f} años")

c6, c7, c8 = st.columns(3)
c6.metric("Duración promedio Gobierno", f"{duration_gov_avg:.2f} años")
c7.metric("Duración promedio Corporativos", f"{duration_corp_avg:.2f} años")
c8.metric("Peso considerado tasa", f"{peso_considerado:.2f}%")

if abs(total_pct - 100) > 0.01:
    st.warning(f"La suma total de participaciones es {total_pct:.2f}%. Idealmente debe sumar 100%.")

# -----------------------------
# Desglose de cálculos
# -----------------------------
with st.expander("Ver desglose de tasa ponderada"):
    if rate_calc_df.empty:
        st.warning("No hay tasas numéricas capturadas.")
    else:
        st.dataframe(rate_calc_df, use_container_width=True)

        st.markdown(
            f"""
            **Suma de aportes:** {suma_aportes:.4f}  
            **Peso considerado:** {peso_considerado:.2f}%  
            **Tasa ponderada:** {suma_aportes:.4f} / {peso_considerado:.2f} = **{rate_weighted:.2f}%**
            """
        )

with st.expander("Ver desglose de duración ponderada"):
    dur_rows = []

    for _, r in gov.iterrows():
        peso = safe_float(r["Part. (%)"])
        dur = safe_float(r["Duración"])
        dur_rows.append(
            {
                "Tipo": "Gobierno",
                "Instrumento": r["Instrumento"],
                "Peso %": peso,
                "Duración": dur,
                "Aporte duración": peso / 100 * dur,
            }
        )

    for _, r in corp.iterrows():
        peso = safe_float(r["Part. (%)"])
        dur = safe_float(r["Duración"])
        dur_rows.append(
            {
                "Tipo": "Corporativo",
                "Instrumento": r["Instrumento"],
                "Peso %": peso,
                "Duración": dur,
                "Aporte duración": peso / 100 * dur,
            }
        )

    dur_calc_df = pd.DataFrame(dur_rows)
    st.dataframe(dur_calc_df, use_container_width=True)

    st.markdown(
        f"""
        **Duración ponderada total:** {duration_weighted:.4f} años  
        **Duración promedio Gobierno:** {duration_gov_avg:.2f} años  
        **Duración promedio Corporativos:** {duration_corp_avg:.2f} años
        """
    )

# -----------------------------
# Bloque listo para copiar
# -----------------------------
st.divider()
st.subheader("Bloque listo para copiar aquí")

copy_block = f"""Cliente: {cliente}
Fecha: {fecha}
Asesor: {asesor}
Cargo: {cargo}
Estrategia: {estrategia}
Monto total: {money(monto_total)}

Gobierno total: {pct(gov_pct)} | {money(gov_amount)}
Corporativos total: {pct(corp_pct)} | {money(corp_amount)}
UDIS total: {pct(udis_pct)} | {money(udis_amount)}
Tasa ponderada: {rate_weighted:.2f}%
Duración ponderada: {duration_weighted:.2f} años
Duración promedio Gobierno: {duration_gov_avg:.2f} años
Duración promedio Corporativos: {duration_corp_avg:.2f} años

Gobierno:
Instrumento | Part. | Monto | Emisor | Calificación | Duración | Tasa/Sobretasa | Periodicidad
{format_table_for_copy(gov, "Tasa / Sobretasa")}

Corporativos:
Instrumento | Part. | Monto | Emisor | Calificación | Duración | Tasa | Periodicidad
{format_table_for_copy(corp, "Tasa")}

Nota tasa:
* TIIE+
"""

st.code(copy_block, language="text")

st.download_button(
    "Descargar bloque en TXT",
    data=copy_block.encode("utf-8"),
    file_name=f"datos_propuesta_{cliente.replace(' ', '_')}.txt",
    mime="text/plain",
)
