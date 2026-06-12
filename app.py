
import io
import math
from datetime import date

import pandas as pd
import streamlit as st

from reportlab.lib import colors
from reportlab.lib.pagesizes import letter
from reportlab.lib.units import inch
from reportlab.pdfgen import canvas


# =========================
# PALETA AJ
# =========================
NAVY = colors.HexColor("#0B1F2E")
NAVY_2 = colors.HexColor("#062033")
GOLD = colors.HexColor("#D4AF37")
GOLD_DARK = colors.HexColor("#B8860B")
WHITE = colors.white
LIGHT_BG = colors.HexColor("#F5F6F7")
GRID = colors.HexColor("#D9DEE5")
TEXT = colors.HexColor("#111827")
MUTED = colors.HexColor("#6B7280")


DISCLAIMER = (
    "Los fines de este documento son meramente informativos. Ni Grupo Bursátil Mexicano S.A. de C.V., "
    "Casa de Bolsa, ni cualquiera de las sociedades relacionadas a ésta, ofrecen ni pretenden garantizar "
    "de manera expresa o implícita la rentabilidad de los productos de inversión referidos en el presente. "
    "Rendimientos pasados no garantizan rendimientos futuros, la información y análisis contenidos no "
    "constituyen ni pretenden ofrecer asesoría de inversión. Los papeles listados están sujetos a "
    "disponibilidad al momento de la boletinación."
)


DEFAULT_GOV = pd.DataFrame(
    [
        ["MBONO 31", 12.5, 500000, "Gobierno Federal", "AAA (mx)\nS&P / Fitch", 3.95, "8.50%", "Semestral"],
        ["MBONO 34", 12.5, 500000, "Gobierno Federal", "AAA (mx)\nS&P / Fitch", 5.82, "9.00%", "Semestral"],
        ["UDIBONO 28", 10.0, 400000, "Gobierno Federal", "AAA (mx)\nS&P / Fitch", 2.36, "UDIS + 3.80%", "Semestral"],
        ["UDIBONO 31", 15.0, 600000, "Gobierno Federal", "AAA (mx)\nS&P / Fitch", 5.01, "UDIS + 4.30%", "Semestral"],
    ],
    columns=["Instrumento", "Part. (%)", "Monto", "Emisor", "Calificación", "Duración", "Tasa / Sobretasa", "Periodicidad Cupones"],
)

DEFAULT_CORP = pd.DataFrame(
    [
        ["FACTORING", 10.0, 400000, "Factoring", "AA (F1 Fitch)", 0.70, "8.30%*", "Mensual"],
        ["PDN", 10.0, 400000, "PDN", "AA (F1 Fitch)", 0.85, "8.45%*", "Mensual"],
        ["GM FIN 26-2", 10.0, 400000, "GM Financial", "AAA (S&P) /\nAA+ (Fitch)", 3.41, "9.20%", "Semestral"],
        ["ORBIA 22-2L", 10.0, 400000, "Orbia", "AA Fitch", 4.44, "10.15%", "Semestral"],
        ["CABEI 1-25S", 10.0, 400000, "CABEI", "AAA (S&P) /\nAaa.mx (Moody's)", 2.67, "8.21%", "Mensual"],
    ],
    columns=["Instrumento", "Part. (%)", "Monto", "Emisor", "Calificación", "Duración", "Tasa", "Periodicidad Cupones"],
)


# =========================
# HELPERS
# =========================
def money(v: float) -> str:
    return f"${v:,.0f}"


def pct(v: float) -> str:
    return f"{v:.1f}%" if abs(v - round(v)) > 0.01 else f"{v:.0f}%"


def safe_num(x, default=0.0):
    try:
        if pd.isna(x):
            return default
        return float(x)
    except Exception:
        return default


def weighted_duration(df: pd.DataFrame) -> float:
    if df.empty:
        return 0
    return sum(safe_num(r["Part. (%)"]) / 100 * safe_num(r["Duración"]) for _, r in df.iterrows())


def fixed_rate_from_text(rate_text: str):
    """Convierte '8.50%' o '8.30%*' a 8.50. Ignora UDIS/TIIE si no hay número principal."""
    import re
    if not isinstance(rate_text, str):
        return None
    match = re.search(r"(\d+(?:\.\d+)?)\s*%", rate_text)
    return float(match.group(1)) if match else None


def calculate_weighted_fixed_rate(gov_df, corp_df):
    """
    Promedio ponderado sobre instrumentos con tasa visible.
    - Excluye UDIBONOS / UDIS.
    - Incluye tasas como 8.30%*, 8.45%*, 9.20%, etc.
    - Corrige el caso de DataFrames combinados donde una columna puede existir pero venir vacía/NaN.
    """
    total_weight = 0.0
    contribution = 0.0

    for _, r in gov_df.iterrows():
        rate_text = str(r.get("Tasa / Sobretasa", ""))
        if "UDI" in rate_text.upper():
            continue
        rate = fixed_rate_from_text(rate_text)
        if rate is None:
            continue
        w = safe_num(r.get("Part. (%)", 0))
        total_weight += w
        contribution += w * rate

    for _, r in corp_df.iterrows():
        rate_text = str(r.get("Tasa", ""))
        if "UDI" in rate_text.upper():
            continue
        rate = fixed_rate_from_text(rate_text)
        if rate is None:
            continue
        w = safe_num(r.get("Part. (%)", 0))
        total_weight += w
        contribution += w * rate

    return contribution / total_weight if total_weight else 0.0


def wrap_text(c, text, x, y, max_width, font="Helvetica", size=8, leading=10, color=TEXT):
    c.setFont(font, size)
    c.setFillColor(color)

    words = str(text).replace("\n", " \n ").split()
    lines = []
    current = ""
    for w in words:
        if w == "\n":
            lines.append(current)
            current = ""
            continue
        test = (current + " " + w).strip()
        if c.stringWidth(test, font, size) <= max_width:
            current = test
        else:
            if current:
                lines.append(current)
            current = w
    if current:
        lines.append(current)

    for i, line in enumerate(lines):
        c.drawString(x, y - i * leading, line)
    return y - len(lines) * leading


def draw_header(c, width, height, adviser_name, adviser_role, client_name, strategy, proposal_date):
    c.setFillColor(NAVY)
    c.rect(0, height * 0.725, width, height * 0.275, stroke=0, fill=1)

    # Decorative curve lines
    c.setStrokeColor(GOLD)
    c.setLineWidth(0.8)
    c.bezier(width*0.38, height*0.89, width*0.58, height*0.90, width*0.61, height*0.99, width*0.98, height*1.02)
    c.bezier(width*0.40, height*0.875, width*0.58, height*0.88, width*0.61, height*0.97, width*0.98, height*1.0)

    # Logo AJ
    c.setFillColor(GOLD)
    c.setFont("Times-Bold", 48)
    c.drawString(0.28*inch, height-0.70*inch, "AJ")
    c.setStrokeColor(GOLD)
    c.line(1.28*inch, height-0.28*inch, 1.28*inch, height-0.95*inch)

    c.setFont("Times-Bold", 16)
    c.drawString(1.45*inch, height-0.55*inch, adviser_name.upper())
    c.setFont("Helvetica", 9)
    c.setFillColor(WHITE)
    c.drawString(1.45*inch, height-0.73*inch, adviser_role)

    c.setFillColor(GOLD)
    c.setFont("Helvetica-Bold", 8.5)
    c.drawRightString(width-0.30*inch, height-0.28*inch, proposal_date.upper())

    c.setFillColor(WHITE)
    c.setFont("Times-Bold", 36)
    c.drawString(0.28*inch, height-1.55*inch, "Propuesta")
    c.drawString(0.28*inch, height-2.02*inch, "de Portafolio")

    c.setFillColor(GOLD)
    c.setFont("Times-Bold", 18)
    c.drawString(0.28*inch, height-2.33*inch, client_name)

    c.setFillColor(WHITE)
    c.setFont("Helvetica", 11)
    c.drawString(0.28*inch, height-2.58*inch, strategy)


def draw_summary_panel(c, width, height, total, gov_pct, corp_pct, rate, duration, udis_pct):
    x = width - 2.85*inch
    y = height - 0.45*inch
    w = 2.55*inch
    h = 2.85*inch

    c.setFillColor(NAVY_2)
    c.setStrokeColor(GOLD)
    c.setLineWidth(1.1)
    c.roundRect(x, y-h, w, h, 10, stroke=1, fill=1)

    rows = [
        ("PORTAFOLIO TOTAL", money(total), ""),
        ("GOBIERNO FEDERAL", f"{pct(gov_pct)}  |  {money(total*gov_pct/100)}", ""),
        ("CORPORATIVOS", f"{pct(corp_pct)}  |  {money(total*corp_pct/100)}", ""),
        ("TASA PONDERADA", f"{rate:.2f}%", "anual"),
        ("DURACIÓN PONDERADA", f"{duration:.2f}", "años"),
        ("EXPOSICIÓN UDIS", f"{pct(udis_pct)}", "del portafolio"),
    ]

    row_h = h / 6
    for i, (label, value, suffix) in enumerate(rows):
        yy = y - (i + 0.5) * row_h

        # icon circle
        c.setStrokeColor(GOLD)
        c.setFillColor(NAVY)
        c.circle(x + 0.35*inch, yy, 0.16*inch, stroke=1, fill=0)

        if i < len(rows) - 1:
            c.setStrokeColor(GOLD_DARK)
            c.line(x+0.65*inch, y-(i+1)*row_h, x+w-0.18*inch, y-(i+1)*row_h)

        c.setFillColor(WHITE)
        c.setFont("Helvetica", 7.7)
        c.drawString(x + 0.62*inch, yy + 0.08*inch, label)
        c.setFont("Helvetica-Bold", 15)
        c.drawString(x + 0.62*inch, yy - 0.13*inch, value)
        if suffix:
            c.setFont("Helvetica", 8)
            c.drawString(x + 1.35*inch, yy - 0.10*inch, suffix)


def draw_feature_blocks(c, width, height, gov_pct, corp_pct, udis_pct):
    y_top = height * 0.715
    c.setFillColor(WHITE)
    c.rect(0, y_top-1.65*inch, width, 1.65*inch, stroke=0, fill=1)

    blocks = [
        (f"{pct(gov_pct)}", "Gobierno Federal", "Máxima calidad\ncrediticia soberana."),
        (f"{pct(corp_pct)}", "Instrumentos\nCorporativos", "Emisores de alta\ncalidad crediticia."),
        (f"{pct(udis_pct)}", "Cobertura\nInflacionaria", "Invertido en\nUDIBONOS\n(UDI + sobretasa)."),
        ("Ingresos\nPeriódicos", "", "Cobro recurrente de\ncupones durante la\nvida de las emisiones."),
    ]

    left = 0.28*inch
    block_w = (width - 0.56*inch) / 4
    for i, (big, title, sub) in enumerate(blocks):
        x = left + i*block_w
        if i > 0:
            c.setStrokeColor(GRID)
            c.line(x, y_top-1.47*inch, x, y_top-0.10*inch)

        c.setFillColor(NAVY)
        c.circle(x + block_w/2, y_top - 0.35*inch, 0.22*inch, stroke=0, fill=1)
        c.setFillColor(GOLD)
        c.setFont("Helvetica-Bold", 16)
        c.drawCentredString(x + block_w/2, y_top - 0.40*inch, "•")

        c.setFillColor(NAVY)
        c.setFont("Helvetica-Bold", 17 if i < 3 else 14)
        lines = big.split("\n")
        for j, line in enumerate(lines):
            c.drawCentredString(x + block_w/2, y_top - 0.78*inch - j*0.18*inch, line)

        c.setFont("Helvetica-Bold", 8.5)
        for j, line in enumerate(title.split("\n")):
            c.drawCentredString(x + block_w/2, y_top - 1.00*inch - j*0.13*inch, line)

        c.setFont("Helvetica", 7.6)
        c.setFillColor(TEXT)
        for j, line in enumerate(sub.split("\n")):
            c.drawCentredString(x + block_w/2, y_top - 1.25*inch - j*0.13*inch, line)


def draw_section_table(c, title, top_label, df, x, y, w, row_h, header_color, columns, subtotal_label, duration_avg):
    # Section band
    band_h = 0.33*inch
    c.setFillColor(header_color)
    c.rect(x, y-band_h, w, band_h, stroke=0, fill=1)
    c.setFillColor(WHITE)
    c.setFont("Helvetica-Bold", 10)
    c.drawString(x + 0.16*inch, y - 0.21*inch, title)
    c.setFont("Helvetica", 9)
    c.drawRightString(x + w - 0.15*inch, y - 0.21*inch, top_label)

    y -= band_h
    header_h = 0.32*inch

    widths = [0.15, 0.09, 0.13, 0.13, 0.13, 0.12, 0.14, 0.11]
    col_ws = [w * pct_w for pct_w in widths]
    scale = w / sum(col_ws)
    col_ws = [cw*scale for cw in col_ws]

    c.setFillColor(WHITE)
    c.rect(x, y-header_h, w, header_h, stroke=0, fill=1)

    c.setFillColor(GOLD_DARK)
    c.setFont("Helvetica-Bold", 6.7)
    xx = x
    for col_name, cw in zip(columns, col_ws):
        wrap_text(c, col_name.upper(), xx + 0.05*inch, y - 0.13*inch, cw - 0.08*inch, "Helvetica-Bold", 6.7, 8, GOLD_DARK)
        xx += cw

    y -= header_h

    c.setStrokeColor(GRID)
    for _, r in df.iterrows():
        c.setFillColor(colors.HexColor("#FBFBFC") if int((_ % 2)) == 0 else colors.white)
        c.rect(x, y-row_h, w, row_h, stroke=0, fill=1)

        values = [
            str(r.get("Instrumento", "")),
            pct(safe_num(r.get("Part. (%)", 0))),
            money(safe_num(r.get("Monto", 0))),
            str(r.get("Emisor", "")),
            str(r.get("Calificación", "")),
            f"{safe_num(r.get('Duración', 0)):.2f} años",
            str(r.get("Tasa / Sobretasa", r.get("Tasa", ""))),
            str(r.get("Periodicidad Cupones", "")),
        ]

        xx = x
        for i, (val, cw) in enumerate(zip(values, col_ws)):
            font = "Helvetica-Bold" if i in [0, 6] else "Helvetica"
            size = 7.2 if i != 4 else 6.5
            color = NAVY if i in [0, 6] else TEXT
            yy = y - 0.18*inch
            wrap_text(c, val, xx + 0.05*inch, yy, cw - 0.10*inch, font, size, 8, color)
            c.setStrokeColor(GRID)
            c.line(xx, y, xx, y-row_h)
            xx += cw
        c.line(x+w, y, x+w, y-row_h)
        c.line(x, y-row_h, x+w, y-row_h)
        y -= row_h

    # Subtotal band
    sub_h = 0.26*inch
    c.setFillColor(header_color)
    c.rect(x, y-sub_h, w, sub_h, stroke=0, fill=1)
    c.setFillColor(WHITE)
    c.setFont("Helvetica-Bold", 7.8)
    total_pct = df["Part. (%)"].astype(float).sum() if not df.empty else 0
    total_amount = df["Monto"].astype(float).sum() if not df.empty else 0
    c.drawString(x + 0.12*inch, y - 0.17*inch, f"{subtotal_label}     {pct(total_pct)}   |   {money(total_amount)}")
    c.drawRightString(x + w - 0.12*inch, y - 0.17*inch, f"DURACIÓN PROMEDIO: {duration_avg:.2f} años")

    return y - sub_h


def draw_disclaimer(c, x, y, w, h):
    c.setStrokeColor(GOLD_DARK)
    c.setFillColor(colors.white)
    c.roundRect(x, y-h, w, h, 8, stroke=1, fill=1)
    c.setFillColor(GOLD_DARK)
    c.circle(x+0.30*inch, y-h/2, 0.16*inch, stroke=1, fill=0)
    c.setFont("Helvetica-Bold", 14)
    c.drawCentredString(x+0.30*inch, y-h/2-0.05*inch, "i")
    wrap_text(c, DISCLAIMER, x+0.62*inch, y-0.16*inch, w-0.78*inch, "Helvetica", 6.2, 7.4, TEXT)


def create_pdf(
    client_name,
    adviser_name,
    adviser_role,
    proposal_date,
    strategy,
    total_portfolio,
    gov_df,
    corp_df,
    output_buffer,
):
    c = canvas.Canvas(output_buffer, pagesize=letter)
    width, height = letter

    # Calculations
    gov_pct = gov_df["Part. (%)"].astype(float).sum() if not gov_df.empty else 0
    corp_pct = corp_df["Part. (%)"].astype(float).sum() if not corp_df.empty else 0
    udis_pct = gov_df[gov_df["Instrumento"].str.upper().str.contains("UDI", na=False)]["Part. (%)"].astype(float).sum() if not gov_df.empty else 0
    duration = weighted_duration(gov_df) + weighted_duration(corp_df)
    gov_duration = weighted_duration(gov_df) / (gov_pct/100) if gov_pct else 0
    corp_duration = weighted_duration(corp_df) / (corp_pct/100) if corp_pct else 0
    rate = calculate_weighted_fixed_rate(gov_df, corp_df)

    # Ensure amount from % and total if user has not aligned them
    gov_df = gov_df.copy()
    corp_df = corp_df.copy()
    gov_df["Monto"] = gov_df["Part. (%)"].astype(float) / 100 * total_portfolio
    corp_df["Monto"] = corp_df["Part. (%)"].astype(float) / 100 * total_portfolio

    draw_header(c, width, height, adviser_name, adviser_role, client_name, strategy, proposal_date)
    draw_summary_panel(c, width, height, total_portfolio, gov_pct, corp_pct, rate, duration, udis_pct)
    draw_feature_blocks(c, width, height, gov_pct, corp_pct, udis_pct)

    c.setFillColor(TEXT)
    c.setFont("Helvetica", 7)
    c.drawString(0.22*inch, height*0.515, "* Tasa ponderada calculada sobre instrumentos con tasa visible. Los Udibonos generan inflación (UDI) + sobretasa.")

    x = 0.22*inch
    w = width - 0.44*inch

    # Dynamic row height: keeps one page reasonably well for up to around 5+5 rows
    total_rows = len(gov_df) + len(corp_df)
    row_h = 0.36*inch if total_rows <= 9 else max(0.28*inch, 3.25*inch / max(total_rows, 1))

    y = height*0.495
    y = draw_section_table(
        c,
        "TÍTULOS PÚBLICOS — GOBIERNO FEDERAL",
        f"{pct(gov_pct)} del portafolio  |  {money(total_portfolio*gov_pct/100)}",
        gov_df,
        x, y, w, row_h,
        NAVY,
        ["Instrumento", "Part.", "Monto (MXN)", "Emisor", "Calificación", "Duración", "Tasa / Sobretasa", "Periodicidad\nCupones"],
        "SUBTOTAL PÚBLICOS",
        gov_duration,
    )

    y -= 0.12*inch
    y = draw_section_table(
        c,
        "TÍTULOS CORPORATIVOS",
        f"{pct(corp_pct)} del portafolio  |  {money(total_portfolio*corp_pct/100)}",
        corp_df,
        x, y, w, row_h,
        GOLD_DARK,
        ["Instrumento", "Part.", "Monto (MXN)", "Emisor", "Calificación", "Duración", "Tasa", "Periodicidad\nCupones"],
        "SUBTOTAL CORPORATIVOS",
        corp_duration,
    )

    c.setFillColor(TEXT)
    c.setFont("Helvetica-Bold", 7)
    c.drawString(x + 0.05*inch, y - 0.10*inch, "* TIIE+")

    draw_disclaimer(c, x, 0.62*inch, w, 0.48*inch)

    c.showPage()
    c.save()


# =========================
# STREAMLIT UI
# =========================
st.set_page_config(page_title="AJ | Generador de Propuesta", layout="wide")

st.title("AJ | Generador de Propuesta de Inversión")
st.caption("Genera únicamente la página 1 en PDF con formato AJ.")

with st.sidebar:
    st.header("Datos generales")
    adviser_name = st.text_input("Nombre asesor", "Alberto Jiménez")
    adviser_role = st.text_input("Cargo", "Asesor Financiero Afiliado GBM")
    client_name = st.text_input("Nombre cliente", "Salomón Elnecave")
    strategy = st.text_input("Estrategia", "Renta Fija  |  Títulos Públicos y Corporativos")
    proposal_date = st.text_input("Fecha", "10 JUNIO 2026")
    total_portfolio = st.number_input("Monto total del portafolio", min_value=0.0, value=4_000_000.0, step=100_000.0)

st.subheader("Instrumentos gubernamentales")
gov_df = st.data_editor(
    DEFAULT_GOV,
    num_rows="dynamic",
    use_container_width=True,
    column_config={
        "Part. (%)": st.column_config.NumberColumn(format="%.2f"),
        "Monto": st.column_config.NumberColumn(format="$%d", disabled=True),
        "Duración": st.column_config.NumberColumn(format="%.2f"),
    },
    key="gov_editor",
)

st.subheader("Instrumentos corporativos")
corp_df = st.data_editor(
    DEFAULT_CORP,
    num_rows="dynamic",
    use_container_width=True,
    column_config={
        "Part. (%)": st.column_config.NumberColumn(format="%.2f"),
        "Monto": st.column_config.NumberColumn(format="$%d", disabled=True),
        "Duración": st.column_config.NumberColumn(format="%.2f"),
    },
    key="corp_editor",
)

gov_pct = gov_df["Part. (%)"].astype(float).sum()
corp_pct = corp_df["Part. (%)"].astype(float).sum()
udis_pct = gov_df[gov_df["Instrumento"].str.upper().str.contains("UDI", na=False)]["Part. (%)"].astype(float).sum()
duration = weighted_duration(gov_df) + weighted_duration(corp_df)
rate = calculate_weighted_fixed_rate(gov_df, corp_df)

st.divider()
c1, c2, c3, c4, c5 = st.columns(5)
c1.metric("Gobierno", f"{gov_pct:.1f}%")
c2.metric("Corporativos", f"{corp_pct:.1f}%")
c3.metric("UDIS", f"{udis_pct:.1f}%")
c4.metric("Tasa ponderada", f"{rate:.2f}%")
c5.metric("Duración ponderada", f"{duration:.2f} años")

with st.expander("Ver cálculo de tasa ponderada"):
    fixed_rows = []
    for _, r in gov_df.iterrows():
        tasa = str(r.get("Tasa / Sobretasa", ""))
        if "UDI" not in tasa.upper():
            rate = fixed_rate_from_text(tasa)
            if rate is not None:
                fixed_rows.append([r.get("Instrumento", ""), safe_num(r.get("Part. (%)", 0)), tasa, rate])
    for _, r in corp_df.iterrows():
        tasa = str(r.get("Tasa", ""))
        rate = fixed_rate_from_text(tasa)
        if rate is not None:
            fixed_rows.append([r.get("Instrumento", ""), safe_num(r.get("Part. (%)", 0)), tasa, rate])
    calc_df = pd.DataFrame(fixed_rows, columns=["Instrumento", "Peso %", "Tasa capturada", "Tasa numérica"])
    if not calc_df.empty:
        calc_df["Aporte"] = calc_df["Peso %"] * calc_df["Tasa numérica"]
        st.dataframe(calc_df, use_container_width=True)
        st.write(f"Suma aportes: {calc_df['Aporte'].sum():.4f} | Peso considerado: {calc_df['Peso %'].sum():.2f}%")
        st.write(f"Tasa ponderada = {calc_df['Aporte'].sum():.4f} / {calc_df['Peso %'].sum():.2f} = {rate:.2f}%")
    else:
        st.warning("No hay tasas numéricas capturadas. Revisa que la columna de tasa tenga valores como 8.30%, 9.20%, etc.")

if abs((gov_pct + corp_pct) - 100) > 0.01:
    st.warning(f"La suma de participaciones es {gov_pct + corp_pct:.2f}%. Idealmente debe sumar 100%.")

buffer = io.BytesIO()
create_pdf(
    client_name=client_name,
    adviser_name=adviser_name,
    adviser_role=adviser_role,
    proposal_date=proposal_date,
    strategy=strategy,
    total_portfolio=total_portfolio,
    gov_df=gov_df,
    corp_df=corp_df,
    output_buffer=buffer,
)

st.download_button(
    "Descargar PDF - Página 1",
    data=buffer.getvalue(),
    file_name=f"AJ_Propuesta_Pagina_1_{client_name.replace(' ', '_')}.pdf",
    mime="application/pdf",
)

st.info("Tip: edita porcentajes, tasas, duraciones, calificaciones y periodicidad. El monto se recalcula con base en el porcentaje y el monto total.")
