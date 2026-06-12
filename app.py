
import io
import re
from datetime import datetime

import pandas as pd
import streamlit as st
from PIL import Image, ImageDraw, ImageFont


# =========================
# CONFIGURACIÓN VISUAL AJ
# =========================
W, H = 1024, 1536
NAVY = "#0B1F2E"
NAVY_DARK = "#061827"
GOLD = "#D4AF37"
GOLD_DARK = "#B8860B"
WHITE = "#FFFFFF"
OFFWHITE = "#FBFBFA"
LIGHT = "#F4F5F7"
GRID = "#E3E6EA"
TEXT = "#0B1324"
MUTED = "#6B7280"

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
# FUENTES
# =========================
def font(size, bold=False, serif=False):
    candidates = []
    if serif:
        candidates = [
            "/usr/share/fonts/truetype/dejavu/DejaVuSerif-Bold.ttf" if bold else "/usr/share/fonts/truetype/dejavu/DejaVuSerif.ttf",
            "/System/Library/Fonts/Times.ttc",
        ]
    else:
        candidates = [
            "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf" if bold else "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
            "/System/Library/Fonts/Supplemental/Arial Bold.ttf" if bold else "/System/Library/Fonts/Supplemental/Arial.ttf",
        ]
    for p in candidates:
        try:
            return ImageFont.truetype(p, size)
        except Exception:
            pass
    return ImageFont.load_default()


F_SERIF_74 = font(74, True, True)
F_SERIF_54 = font(54, True, True)
F_SERIF_36 = font(36, True, True)
F_SERIF_30 = font(30, True, True)
F_SERIF_24 = font(24, True, True)

F_34B = font(34, True)
F_30B = font(30, True)
F_26B = font(26, True)
F_22B = font(22, True)
F_20B = font(20, True)
F_18B = font(18, True)
F_16B = font(16, True)
F_14B = font(14, True)
F_12B = font(12, True)
F_11B = font(11, True)
F_10B = font(10, True)

F_20 = font(20)
F_18 = font(18)
F_16 = font(16)
F_14 = font(14)
F_13 = font(13)
F_12 = font(12)
F_11 = font(11)
F_10 = font(10)
F_9 = font(9)
F_8 = font(8)


# =========================
# CÁLCULOS
# =========================
def money(v):
    try:
        return f"${float(v):,.0f}"
    except Exception:
        return "$0"

def pct(v):
    try:
        v = float(v)
        return f"{v:.1f}%" if abs(v - round(v)) > 0.01 else f"{v:.0f}%"
    except Exception:
        return "0%"

def safe_float(v):
    try:
        if pd.isna(v):
            return 0.0
        return float(v)
    except Exception:
        return 0.0

def fixed_rate_from_text(txt):
    m = re.search(r"(\d+(?:\.\d+)?)\s*%", str(txt))
    return float(m.group(1)) if m else None

def weighted_duration(df):
    return sum(safe_float(r["Part. (%)"]) / 100 * safe_float(r["Duración"]) for _, r in df.iterrows())

def avg_duration(df):
    total = df["Part. (%)"].astype(float).sum() if not df.empty else 0
    return weighted_duration(df) / (total / 100) if total else 0

def weighted_rate(gov, corp):
    tw, contrib = 0.0, 0.0
    for _, r in gov.iterrows():
        tasa = str(r.get("Tasa / Sobretasa", ""))
        if "UDI" in tasa.upper():
            continue
        rate = fixed_rate_from_text(tasa)
        if rate is not None:
            w = safe_float(r.get("Part. (%)", 0))
            tw += w
            contrib += w * rate
    for _, r in corp.iterrows():
        tasa = str(r.get("Tasa", ""))
        rate = fixed_rate_from_text(tasa)
        if rate is not None:
            w = safe_float(r.get("Part. (%)", 0))
            tw += w
            contrib += w * rate
    return contrib / tw if tw else 0.0


# =========================
# DIBUJO
# =========================
def draw_text(draw, xy, text, fill=TEXT, font_obj=F_12, anchor=None):
    draw.text(xy, str(text), fill=fill, font=font_obj, anchor=anchor)

def text_size(draw, text, f):
    box = draw.textbbox((0, 0), str(text), font=f)
    return box[2] - box[0], box[3] - box[1]

def draw_wrapped(draw, text, x, y, max_w, f, fill=TEXT, line_h=None, align="left"):
    if line_h is None:
        line_h = int(f.size * 1.25)
    lines = []
    for para in str(text).split("\n"):
        words = para.split()
        cur = ""
        for w in words:
            test = (cur + " " + w).strip()
            if text_size(draw, test, f)[0] <= max_w:
                cur = test
            else:
                if cur:
                    lines.append(cur)
                cur = w
        if cur:
            lines.append(cur)
    for i, line in enumerate(lines):
        yy = y + i * line_h
        if align == "center":
            draw_text(draw, (x + max_w / 2, yy), line, fill, f, anchor="ma")
        else:
            draw_text(draw, (x, yy), line, fill, f)
    return y + len(lines) * line_h

def rounded_rect(draw, xy, radius, fill, outline=None, width=1):
    draw.rounded_rectangle(xy, radius=radius, fill=fill, outline=outline, width=width)

def draw_icon_circle(draw, cx, cy, label=""):
    draw.ellipse((cx-30, cy-30, cx+30, cy+30), fill=NAVY, outline=None)
    draw.ellipse((cx-20, cy-20, cx+20, cy+20), outline=GOLD, width=3)
    if label:
        draw_text(draw, (cx, cy-10), label, GOLD, F_20B, anchor="ma")

def draw_summary(draw, x, y, w, h, total, gov_pct, corp_pct, rate, duration, udis_pct):
    rounded_rect(draw, (x, y, x+w, y+h), 18, NAVY_DARK, GOLD, 2)
    rows = [
        ("PORTAFOLIO TOTAL", money(total), ""),
        ("GOBIERNO FEDERAL", f"{pct(gov_pct)}  |  {money(total*gov_pct/100)}", ""),
        ("CORPORATIVOS", f"{pct(corp_pct)}  |  {money(total*corp_pct/100)}", ""),
        ("TASA PONDERADA", f"{rate:.2f}%", "anual"),
        ("DURACIÓN PONDERADA", f"{duration:.2f}", "años"),
        ("EXPOSICIÓN UDIS", f"{pct(udis_pct)}", "del portafolio"),
    ]
    rh = h / 6
    for i, (label, value, suffix) in enumerate(rows):
        yy = int(y + i*rh)
        cy = int(yy + rh/2)
        draw.ellipse((x+25, cy-22, x+69, cy+22), outline=GOLD, width=3)
        if i < len(rows)-1:
            draw.line((x+95, yy+rh, x+w-24, yy+rh), fill=GOLD_DARK, width=2)
        draw_text(draw, (x+95, cy-27), label, WHITE, F_14)
        draw_text(draw, (x+95, cy-4), value, WHITE, F_26B)
        if suffix:
            draw_text(draw, (x+190, cy+3), suffix, WHITE, F_14)

def draw_features(draw, y, gov_pct, corp_pct, udis_pct):
    items = [
        (pct(gov_pct), "Gobierno Federal", "Máxima calidad\ncrediticia soberana."),
        (pct(corp_pct), "Instrumentos\nCorporativos", "Emisores de alta\ncalidad crediticia."),
        (pct(udis_pct), "Cobertura\nInflacionaria", "Invertido en\nUDIBONOS\n(UDI + sobretasa)."),
        ("Ingresos\nPeriódicos", "", "Cobro recurrente de\ncupones durante la\nvida de las emisiones."),
    ]
    x0, block_w = 24, 244
    for i, (big, title, desc) in enumerate(items):
        x = x0 + i*block_w
        if i > 0:
            draw.line((x, y+20, x, y+170), fill="#D1D5DB", width=1)
        draw_icon_circle(draw, x+block_w//2, y+42)
        for j, line in enumerate(big.split("\n")):
            draw_text(draw, (x+block_w//2, y+78+j*25), line, NAVY, F_30B if len(big.split("\n")) == 1 else F_24B, anchor="ma")
        base = y + 112 if len(big.split("\n")) == 1 else y + 130
        for j, line in enumerate(title.split("\n")):
            draw_text(draw, (x+block_w//2, base+j*18), line, NAVY, F_14B, anchor="ma")
        desc_y = base + (len(title.split("\n"))*18) + 12
        for j, line in enumerate(desc.split("\n")):
            draw_text(draw, (x+block_w//2, desc_y+j*17), line, TEXT, F_12, anchor="ma")

def draw_table(draw, x, y, w, title, top_label, df, columns, rate_col, band_color, subtotal_label, duration_avg, row_h):
    band_h = 56
    draw.rectangle((x, y, x+w, y+band_h), fill=band_color)
    draw_text(draw, (x+24, y+18), title, WHITE, F_18B)
    draw_text(draw, (x+w-20, y+18), top_label, WHITE, F_16, anchor="ra")
    y += band_h

    header_h = 46
    draw.rectangle((x, y, x+w, y+header_h), fill=WHITE)
    col_fracs = [0.16, 0.085, 0.13, 0.135, 0.155, 0.11, 0.13, 0.095]
    col_w = [int(w*f) for f in col_fracs]
    col_w[-1] = w - sum(col_w[:-1])

    xx = x
    for c, cw in zip(columns, col_w):
        draw_wrapped(draw, c.upper(), xx+8, y+12, cw-12, F_10B, GOLD_DARK, 12)
        xx += cw
    y += header_h

    for idx, (_, r) in enumerate(df.iterrows()):
        fill = WHITE if idx % 2 else "#FAFAFA"
        draw.rectangle((x, y, x+w, y+row_h), fill=fill)
        vals = [
            str(r.get("Instrumento", "")),
            pct(safe_float(r.get("Part. (%)", 0))),
            money(safe_float(r.get("Monto", 0))),
            str(r.get("Emisor", "")),
            str(r.get("Calificación", "")),
            f"{safe_float(r.get('Duración', 0)):.2f} años",
            str(r.get(rate_col, "")),
            str(r.get("Periodicidad Cupones", "")),
        ]
        xx = x
        for j, (val, cw) in enumerate(zip(vals, col_w)):
            f = F_11B if j in [0, 6] else F_10
            color = NAVY if j in [0, 6] else TEXT
            draw_wrapped(draw, val, xx+8, y+14, cw-14, f, color, 13)
            draw.line((xx, y, xx, y+row_h), fill=GRID, width=1)
            xx += cw
        draw.line((x+w, y, x+w, y+row_h), fill=GRID, width=1)
        draw.line((x, y+row_h, x+w, y+row_h), fill=GRID, width=1)
        y += row_h

    sub_h = 40
    draw.rectangle((x, y, x+w, y+sub_h), fill=band_color)
    total_pct = df["Part. (%)"].astype(float).sum() if not df.empty else 0
    total_amt = df["Monto"].astype(float).sum() if not df.empty else 0
    draw_text(draw, (x+18, y+12), f"{subtotal_label}     {pct(total_pct)}   |   {money(total_amt)}", WHITE, F_13B)
    draw_text(draw, (x+w-18, y+12), f"DURACIÓN PROMEDIO: {duration_avg:.2f} años", WHITE, F_13B, anchor="ra")
    return y + sub_h

def generate_page(client_name, adviser_name, adviser_role, date_text, strategy, total, gov_df, corp_df):
    gov_df = gov_df.copy()
    corp_df = corp_df.copy()
    gov_df["Monto"] = gov_df["Part. (%)"].astype(float) / 100 * total
    corp_df["Monto"] = corp_df["Part. (%)"].astype(float) / 100 * total

    gov_pct = gov_df["Part. (%)"].astype(float).sum() if not gov_df.empty else 0
    corp_pct = corp_df["Part. (%)"].astype(float).sum() if not corp_df.empty else 0
    udis_pct = gov_df[gov_df["Instrumento"].astype(str).str.upper().str.contains("UDI", na=False)]["Part. (%)"].astype(float).sum() if not gov_df.empty else 0
    duration = weighted_duration(gov_df) + weighted_duration(corp_df)
    rate = weighted_rate(gov_df, corp_df)

    img = Image.new("RGB", (W, H), OFFWHITE)
    draw = ImageDraw.Draw(img)

    # Header navy area
    draw.rectangle((0, 0, W, 405), fill=NAVY)
    # decorative golden curves
    for off in [0, 22]:
        draw.arc((330, -180+off, 1160, 300+off), 190, 340, fill=GOLD, width=2)

    # Logo and adviser
    draw_text(draw, (28, 22), "AJ", GOLD, F_SERIF_74)
    draw.line((162, 28, 162, 118), fill=GOLD, width=2)
    draw_text(draw, (200, 55), adviser_name.upper(), GOLD, F_SERIF_24)
    draw_text(draw, (200, 90), adviser_role, WHITE, F_16)

    draw_text(draw, (W-24, 24), date_text.upper(), GOLD, F_16B, anchor="ra")

    draw_text(draw, (28, 172), "Propuesta", WHITE, F_SERIF_54)
    draw_text(draw, (28, 235), "de Portafolio", WHITE, F_SERIF_54)
    draw_text(draw, (28, 320), client_name, GOLD, F_SERIF_30)
    draw_text(draw, (28, 360), strategy, WHITE, F_18)

    draw_summary(draw, 640, 55, 345, 468, total, gov_pct, corp_pct, rate, duration, udis_pct)

    # Feature blocks
    draw.rectangle((0, 405, W, 662), fill=WHITE)
    draw_features(draw, 428, gov_pct, corp_pct, udis_pct)
    draw_text(draw, (24, 688), "* Tasa ponderada calculada sobre instrumentos con tasa visible. Los Udibonos generan inflación (UDI) + sobretasa.", TEXT, F_11)

    # Tables
    total_rows = len(gov_df) + len(corp_df)
    row_h = 62 if total_rows <= 9 else max(48, int(558 / max(total_rows, 1)))

    x, w = 20, W-40
    y = 720
    y = draw_table(
        draw, x, y, w,
        "TÍTULOS PÚBLICOS — GOBIERNO FEDERAL",
        f"{pct(gov_pct)} del portafolio  |  {money(total*gov_pct/100)}",
        gov_df,
        ["Instrumento", "Part.", "Monto (MXN)", "Emisor", "Calificación", "Duración", "Tasa / Sobretasa", "Periodicidad\nCupones"],
        "Tasa / Sobretasa",
        NAVY,
        "SUBTOTAL PÚBLICOS",
        avg_duration(gov_df),
        row_h
    )

    y += 18
    y = draw_table(
        draw, x, y, w,
        "TÍTULOS CORPORATIVOS",
        f"{pct(corp_pct)} del portafolio  |  {money(total*corp_pct/100)}",
        corp_df,
        ["Instrumento", "Part.", "Monto (MXN)", "Emisor", "Calificación", "Duración", "Tasa", "Periodicidad\nCupones"],
        "Tasa",
        GOLD_DARK,
        "SUBTOTAL CORPORATIVOS",
        avg_duration(corp_df),
        row_h
    )

    draw_text(draw, (28, y+8), "* TIIE+", TEXT, F_11B)

    # Disclaimer fixed at bottom
    box_y, box_h = 1410, 92
    rounded_rect(draw, (20, box_y, W-20, box_y+box_h), 12, WHITE, GOLD_DARK, 1)
    draw.ellipse((42, box_y+26, 82, box_y+66), outline=GOLD_DARK, width=2)
    draw_text(draw, (62, box_y+33), "i", GOLD_DARK, F_20B, anchor="ma")
    draw_wrapped(draw, DISCLAIMER, 102, box_y+18, W-140, F_9, TEXT, 11)

    return img

def image_to_png_bytes(img):
    b = io.BytesIO()
    img.save(b, format="PNG")
    return b.getvalue()

def image_to_pdf_bytes(img):
    b = io.BytesIO()
    img.save(b, format="PDF", resolution=150.0)
    return b.getvalue()


# =========================
# UI STREAMLIT
# =========================
st.set_page_config(page_title="AJ | Propuesta Página 1", layout="wide")
st.title("AJ | Generador visual de propuesta de inversión")
st.caption("Versión con salida tipo imagen/PDF para replicar mejor el diseño visual AJ.")

with st.sidebar:
    st.header("Datos generales")
    adviser_name = st.text_input("Nombre asesor", "Alberto Jiménez")
    adviser_role = st.text_input("Cargo", "Asesor Financiero Afiliado GBM")
    client_name = st.text_input("Nombre cliente", "Salomón Elnecave")
    strategy = st.text_input("Estrategia", "Renta Fija  |  Títulos Públicos y Corporativos")
    date_text = st.text_input("Fecha", "10 JUNIO 2026")
    total = st.number_input("Monto total del portafolio", min_value=0.0, value=4_000_000.0, step=100_000.0)

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
    key="gov",
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
    key="corp",
)

gov_pct = gov_df["Part. (%)"].astype(float).sum()
corp_pct = corp_df["Part. (%)"].astype(float).sum()
udis_pct = gov_df[gov_df["Instrumento"].astype(str).str.upper().str.contains("UDI", na=False)]["Part. (%)"].astype(float).sum()
rate = weighted_rate(gov_df, corp_df)
duration = weighted_duration(gov_df) + weighted_duration(corp_df)

st.divider()
m1, m2, m3, m4, m5 = st.columns(5)
m1.metric("Gobierno", f"{gov_pct:.1f}%")
m2.metric("Corporativos", f"{corp_pct:.1f}%")
m3.metric("UDIS", f"{udis_pct:.1f}%")
m4.metric("Tasa ponderada", f"{rate:.2f}%")
m5.metric("Duración ponderada", f"{duration:.2f} años")

if abs(gov_pct + corp_pct - 100) > 0.01:
    st.warning(f"La suma de participaciones es {gov_pct + corp_pct:.2f}%. Idealmente debe sumar 100%.")

with st.expander("Ver cálculo de tasa ponderada"):
    rows = []
    for _, r in gov_df.iterrows():
        tasa = str(r.get("Tasa / Sobretasa", ""))
        if "UDI" not in tasa.upper():
            rn = fixed_rate_from_text(tasa)
            if rn is not None:
                peso = safe_float(r["Part. (%)"])
                rows.append([r["Instrumento"], peso, tasa, rn, peso * rn])
    for _, r in corp_df.iterrows():
        tasa = str(r.get("Tasa", ""))
        rn = fixed_rate_from_text(tasa)
        if rn is not None:
            peso = safe_float(r["Part. (%)"])
            rows.append([r["Instrumento"], peso, tasa, rn, peso * rn])
    calc = pd.DataFrame(rows, columns=["Instrumento", "Peso %", "Tasa capturada", "Tasa numérica", "Aporte"])
    st.dataframe(calc, use_container_width=True)
    if not calc.empty:
        st.write(f"Tasa ponderada = {calc['Aporte'].sum():.4f} / {calc['Peso %'].sum():.2f} = {calc['Aporte'].sum()/calc['Peso %'].sum():.2f}%")

img = generate_page(client_name, adviser_name, adviser_role, date_text, strategy, total, gov_df, corp_df)

st.subheader("Vista previa")
st.image(img, use_container_width=True)

col1, col2 = st.columns(2)
with col1:
    st.download_button(
        "Descargar PNG",
        data=image_to_png_bytes(img),
        file_name=f"AJ_Propuesta_Pagina_1_{client_name.replace(' ', '_')}.png",
        mime="image/png",
    )
with col2:
    st.download_button(
        "Descargar PDF",
        data=image_to_pdf_bytes(img),
        file_name=f"AJ_Propuesta_Pagina_1_{client_name.replace(' ', '_')}.pdf",
        mime="application/pdf",
    )
