"""
══════════════════════════════════════════════════════════════════════════════
  HERRAMIENTA MTDS 2026  —  Ministerio de Hacienda y Crédito Público
  Metodología:  BM-FMI "Formulación de una EDMP" (2018)
  Análisis:     Monte Carlo (1,000 esc.) + Pruebas de Estrés Deterministas
  Indicadores:  Apéndice III — Costos, Riesgos y Estadísticas de Cartera
  Pasos:        1-8 del marco EDMP (Nota de Orientación BM-FMI, oct. 2018)
══════════════════════════════════════════════════════════════════════════════

INDICADORES BM-FMI IMPLEMENTADOS
─────────────────────────────────
Costo:
  · Pago de intereses / PIB (%)
  · Pago de intereses / Ingresos (%)
  · Tasa de interés promedio ponderada (%)

Riesgo de mercado (tasa de interés):
  · TPR — Tiempo Promedio hasta la Refijación (años)
  · % deuda a tasa variable (refijación < 1 año)
  · Δcosto bajo shock de tasas (+200 pbs)

Riesgo de refinanciamiento:
  · TPV — Tiempo Promedio hasta el Vencimiento (años)
  · % deuda que vence en año 1
  · Perfil de amortización (años 1-5)

Riesgo cambiario:
  · % deuda en moneda extranjera
  · Δcosto bajo shock cambiario (depreciación 30%)
  · Composición por monedas

Análisis estocástico:
  · E[costo] — esperanza matemática (% PIB)
  · σ[costo] — desviación estándar
  · CVaR 95% — condicional value-at-risk
"""

import numpy as np
import pandas as pd
from scipy.optimize import minimize
from openpyxl import Workbook, load_workbook
from openpyxl.styles import (Font, PatternFill, Alignment, Border, Side)
from openpyxl.utils import get_column_letter
import warnings, shutil, os
from fpdf import FPDF
from datetime import datetime
import yfinance as yf
from pmdarima import auto_arima
from sklearn.metrics import root_mean_squared_error, mean_absolute_error
from sklearn.ensemble import RandomForestRegressor, GradientBoostingRegressor
from sklearn.linear_model import LinearRegression
import matplotlib.pyplot as plt

warnings.filterwarnings("ignore")
np.random.seed(42)

# ══════════════════════════════════════════════════════════════════════════════
# 1. DEFINICIÓN DE INSTRUMENTOS  (8 instrumentos)
# ══════════════════════════════════════════════════════════════════════════════
INSTRUMENTS = [
    # id            mercado           moneda  tasa        ATM   ATR  FX?   Var?
    ("DI_COP_F", "Deuda Interna", "COP", "Fija",      9.0, 9.0, False, False),
    ("DI_UVR_F", "Deuda Interna", "UVR", "Fija",     12.0,12.0, False, False),
    ("DE_USD_F", "Deuda Externa", "USD", "Fija",     10.0,10.0, True,  False),
    ("DE_EUR_F", "Deuda Externa", "EUR", "Fija",     10.0,10.0, True,  False),
    ("DE_EUR_V", "Deuda Externa", "EUR", "Variable",  5.0, 0.25,True,  True ),
    ("DE_USD_V", "Deuda Externa", "USD", "Variable",  5.0, 0.25,True,  True ),
    ("DE_CHF_F", "Deuda Externa", "CHF", "Fija",      8.0, 8.0, True,  False),
    ("DE_CHF_V", "Deuda Externa", "CHF", "Variable",  5.0, 0.25,True,  True ),
]
N_INST = len(INSTRUMENTS)

# Ruta de la plantilla Bloomberg
# El script busca en este orden:
#   1. Carpeta del script (si ejecutas localmente)
#   2. /mnt/user-data/outputs/ (carpeta de outputs de la herramienta)
#   3. Directorio de trabajo actual
def _find_template() -> str:
    candidates = [
        os.path.join(os.path.dirname(os.path.abspath(__file__)),
                     "MTDS_Bloomberg_Template.xlsx"),
        "MTDS_Bloomberg_Template.xlsx",
        os.path.join(os.getcwd(), "MTDS_Bloomberg_Template.xlsx"),
    ]
    for p in candidates:
        if os.path.exists(p):
            return p
    return candidates[1]   # fallback: outputs folder

TEMPLATE_PATH = _find_template()

def _find_data_file(filename: str) -> str:
    """Search for a data file in common locations."""
    candidates = [
        os.path.join(os.path.dirname(os.path.abspath(__file__)), filename),
        os.path.join("/mnt/user-data/uploads", filename),
        os.path.join("/mnt/user-data/outputs", filename),
        os.path.join(os.getcwd(), filename),
    ]
    for p in candidates:
        if os.path.exists(p):
            return p
    return candidates[1]   # fallback: uploads folder

ORACLE_PATH = _find_data_file("Consulta Oracle 31-03-2026.xls")  # TSV tab-separado con extensión .xls
PERFIL_PATH = _find_data_file("Perfil de vencimientos 2026.xlsm")

# Tipos de tasa fija según Oracle (CLASE_INT)
FIXED_TYPES   = {"FIJA", "SINI", "FUFI", "FI19"}
VARIABLE_TYPES_KNOWN = {
    "FUL3": "SOFR/LIBOR USD 3M",  "LUS3": "LIBOR USD 3M",
    "EUL6": "EURIBOR 6M",         "EUL3": "EURIBOR 3M",
    "UBIR": "IBOR USD",           "EBIR": "IBOR EUR",
    "TSO6": "SOFR 6M",            "TSOR": "SOFR",
    "ISOR": "SOFR",               "IBRO": "IBOR",
    "LB6":  "SDR 6M",             "FIDB": "Tasa fija DB",
}

# Mapeo: Bloomberg ticker → clave en PARAMS
# Prioridad: Parametros_Modelo > Tasas_y_Mercado (tickers)
TICKER_TO_PARAM = {
    # Tasas COP / UVR
    "COGR10YR Index":  "cop_fixed_rate",
    "COUVR10Y Index":  "uvr_real_rate",
    "COCPIYOY Index":  "uvr_inflation",
    # Tasas USD
    "SOFR Index":      "sofr_base",
    # Tasas EUR
    "EUR003M Index":   "euribor_base",
    # Tasas CHF
    "SRON Index":      "saron_base",
    # FX spots
    "COP Curncy":      "usdcop_spot",
    "EURCOP Curncy":   "eurcop_spot",
    "CHFCOP Curncy":   "chfcop_spot",
}

# Referencia MFMP 2025 (punto de partida)
REF_MFMP25 = {
    "DI_COP_F": 0.40, "DI_UVR_F": 0.20,
    "DE_USD_F": 0.24, "DE_EUR_F": 0.06,
    "DE_EUR_V": 0.05, "DE_USD_V": 0.05,
    "DE_CHF_F": 0.00, "DE_CHF_V": 0.00,
}

# ══════════════════════════════════════════════════════════════════════════════
# 2. PARÁMETROS  (calibrar con datos Bloomberg)
# ══════════════════════════════════════════════════════════════════════════════
PARAMS = {
    # ── TASAS BASE (nueva emisión, %) ──────────────────────────────────────
    "cop_fixed_rate":    9.50,   # TES COP 10Y       — COGR10YR Index
    "uvr_real_rate":     4.50,   # TES UVR real       — COUVR10Y Index
    "uvr_inflation":     5.00,   # Inflación COP      — COCPIYOY Index
    "usd_fixed_rate":    6.00,   # UST + spread       — GT10 Govt + spread
    "eur_fixed_rate":    4.00,   # Bund + spread      — GDBR10 Govt + spread
    "chf_fixed_rate":    2.00,   # Swiss + spread     — GSWISS10 Govt + spread

    # ── TASAS VARIABLES (spread + índice base, %) ──────────────────────────
    "sofr_base":         4.50,   # SOFR               — SOFR Index
    "usd_spread_sofr":   1.20,   # Spread sobre SOFR
    "euribor_base":      3.00,   # EURIBOR 3M         — EUR003M Index
    "eur_spread_eurib":  0.90,   # Spread sobre EURIBOR
    "saron_base":        1.20,   # SARON              — SRON Index
    "chf_spread_saron":  0.60,   # Spread sobre SARON

    # ── VOLATILIDADES ANUALIZADAS (%) ──────────────────────────────────────
    "vol_cop_rate":      1.80,   "vol_uvr_inf":      1.20,
    "vol_usd_rate":      0.90,   "vol_eur_rate":     0.70,
    "vol_chf_rate":      0.50,   "vol_sofr":         0.80,
    "vol_euribor":       0.65,   "vol_saron":        0.40,

    # ── TIPOS DE CAMBIO (GBM) ─────────────────────────────────────────────
    "usdcop_spot":       3563.71,   "usdcop_drift":     4.0,  "vol_usdcop":  9.0,
    "eurcop_spot":       4178.10,   "eurcop_drift":     3.0,  "vol_eurcop":  8.5,
    "chfcop_spot":       4537.91,   "chfcop_drift":     2.5,  "vol_chfcop":  7.5,

    # ── MACRO / FISCAL ────────────────────────────────────────────────────
    "gdp_cop_bn":        1998.508,  # PIB COP billones   — COGDPNAC Index
    "debt_pct_gdp":       55.13,  # Deuda / PIB (%)
    "revenues_pct_gdp":   18.2,  # Ingresos Gob. / PIB (%)
    "gfn_pct_gdp":         9.7,  # Necesidades brutas financiamiento
}

# ══════════════════════════════════════════════════════════════════════════════
# 3. LECTOR DE DATOS ORACLE  (deuda externa — xlsx o csv tab-separado)
# ══════════════════════════════════════════════════════════════════════════════
def load_from_oracle(oracle_path: str) -> dict:
    """
    Lee la consulta Oracle de deuda externa.
    Acepta: xlsx/xls  (pandas read_excel)  o  csv/txt tab-separado.

    Columnas requeridas:
      MDA_TR        — moneda (USD, EUR, CHF, COP, DEG...)
      CLASE_INT     — tipo de tasa: FIJA={FIJA,SINI,FUFI,FI19}; VARIABLE=resto
      MARGEN_VALOR  — spread (variable) o tasa nominal anual (fija)  en %
      SDO_US        — saldo en USD (para ponderación)
      ULT_PAGO      — fecha último pago (para calcular TPV)

    Reglas:
      · DEG/SDR → fusionado con USD (cesta SDR dominada ~43% USD)
      · MARGEN_VALOR = tasa nominal si FIJA, spread sobre índice si VARIABLE
    """
    result = {
        "ok": False, "log": [], "rates": {}, "oracle_weights": {},
        "currencies_present": [],
        "external_total_usd": 0.0,
        "report": "",
    }

    if not os.path.exists(oracle_path):
        result["log"].append(f"⚠  Oracle no encontrado: '{oracle_path}'")
        result["log"].append("   Proporcione: Consulta_Oracle.xlsx con cols "
                             "MDA_TR, CLASE_INT, MARGEN_VALOR, SDO_US, ULT_PAGO")
        return result

    # ── Leer según extensión ──────────────────────────────────────────────
    ext = os.path.splitext(oracle_path)[1].lower()
    try:
        # Detect if file is actually a TSV (Oracle exports .xls as tab-separated text)
        with open(oracle_path, 'rb') as ftest:
            header_bytes = ftest.read(8)
        is_real_excel = header_bytes[:4] in (b'\xd0\xcf\x11\xe0', b'PK\x03\x04')

        if is_real_excel and ext in ('.xlsx', '.xlsm'):
            df = pd.read_excel(oracle_path, engine='openpyxl')
        elif is_real_excel and ext == '.xls':
            df = pd.read_excel(oracle_path, engine='xlrd')
        else:   # TSV / CSV (Oracle suele exportar así)
            for enc in ('utf-8', 'latin-1', 'cp1252'):
                try:
                    df = pd.read_csv(oracle_path, sep='\t', encoding=enc)
                    break
                except UnicodeDecodeError:
                    continue
        result["log"].append(
            f"✔  Oracle leído: {len(df):,} registros | cols: {list(df.columns)}"
        )
    except Exception as e:
        result["log"].append(f"⚠  Error leyendo Oracle: {e}")
        return result

    # ── Verificar columnas mínimas ────────────────────────────────────────
    req = {"MDA_TR", "CLASE_INT", "MARGEN_VALOR", "SDO_US"}
    missing = req - set(df.columns)
    if missing:
        result["log"].append(f"⚠  Columnas faltantes en Oracle: {missing}")
        return result

    # ── Limpieza ──────────────────────────────────────────────────────────
    df = df.copy()
    df["CLASE_INT"]    = df["CLASE_INT"].astype(str).str.strip().str.upper()
    df["MDA_TR"]       = df["MDA_TR"].astype(str).str.strip().str.upper()
    df["SDO_US"]       = pd.to_numeric(df["SDO_US"], errors="coerce").fillna(0)
    df["MARGEN_VALOR"] = pd.to_numeric(df["MARGEN_VALOR"], errors="coerce").fillna(0)
    df = df[df["SDO_US"] > 0].copy()

    # ── Clasificación FIJA vs VARIABLE ────────────────────────────────────
    df["TIPO_CAT"] = df["CLASE_INT"].apply(
        lambda x: "FIJA" if x in FIXED_TYPES else "VARIABLE"
    )

    fijas     = sorted(df[df["TIPO_CAT"] == "FIJA"   ]["CLASE_INT"].unique())
    variables = sorted(df[df["TIPO_CAT"] == "VARIABLE"]["CLASE_INT"].unique())

    report_lines = []
    report_lines.append("\n  ┌─ CLASIFICACIÓN CLASE_INT (Oracle) ────────────────────────────")
    report_lines.append(f"  │  FIJA     ({len(fijas):>2} tipos): {', '.join(fijas)}")
    report_lines.append(f"  │  VARIABLE ({len(variables):>2} tipos):")
    for v in variables:
        desc = VARIABLE_TYPES_KNOWN.get(v, "—índice no mapeado—")
        report_lines.append(f"  │     {v:<8} → {desc}")
    report_lines.append("  │")
    report_lines.append("  │  Regla: FIJA={FIJA,SINI,FUFI,FI19}")
    report_lines.append("  │         MARGEN_VALOR=tasa nominal anual (fija) | spread (variable)")
    report_lines.append("  └───────────────────────────────────────────────────────────────")

    # ── DEG / SDR → USD ──────────────────────────────────────────────────
    deg_count = (df["MDA_TR"] == "DEG").sum()
    if deg_count > 0:
        report_lines.append(f"  ⓘ  DEG (SDR): {deg_count} préstamos reclasificados → USD")
    df["MDA_TR_adj"] = df["MDA_TR"].replace({"DEG": "USD", "SDR": "USD"})

    # ── TPV ──────────────────────────────────────────────────────────────
    ref_date = pd.Timestamp("2026-03-31")
    if "ULT_PAGO" in df.columns:
        df["ULT_PAGO"] = pd.to_datetime(df["ULT_PAGO"], errors="coerce")
        df["ATM_YEARS"] = (df["ULT_PAGO"] - ref_date).dt.days / 365.25
        df = df[df["ATM_YEARS"] > 0].copy()
    else:
        df["ATM_YEARS"] = 8.0   # fallback si no hay fecha

    # ── Monedas presentes (solo las que existen en Oracle) ───────────────
    currencies_raw = sorted(df["MDA_TR_adj"].unique())
    # Excluir monedas que no mapeamos a instrumentos MTDS
    valid_fx = {"USD", "EUR", "CHF", "GBP", "JPY"}
    currencies = [c for c in currencies_raw if c in valid_fx]
    result["currencies_present"] = currencies

    # ── Mapeo moneda×tipo → instrumento MTDS ────────────────────────────
    inst_map = {}
    for ccy in currencies:
        inst_map[(ccy, "FIJA")]     = f"DE_{ccy}_F"
        inst_map[(ccy, "VARIABLE")] = f"DE_{ccy}_V"
    inst_map[("COP", "FIJA")]     = "DI_COP_EXT"
    inst_map[("COP", "VARIABLE")] = "DI_COP_EXT"

    total_ext = df["SDO_US"].sum()
    result["external_total_usd"] = total_ext

    report_lines.append("\n  ┌─ PORTAFOLIO EXTERNO (Oracle, DEG→USD) ────────────────────────")
    report_lines.append(f"  │  {'Instrumento':<16} {'Moneda':>6} {'Tipo':>9}  "
          f"{'Saldo USD M':>12}  {'Part%':>7}  {'Tasa/Spread WP (MARGEN_VALOR)':>32}  {'TPV':>6}")
    report_lines.append(f"  │  {'-'*90}")

    for (mda, tipo), grp in df.groupby(["MDA_TR_adj", "TIPO_CAT"]):
        inst_id = inst_map.get((mda, tipo), f"{mda}_{tipo[:3]}")
        saldo   = grp["SDO_US"].sum()
        part    = saldo / total_ext * 100
        # Tasa/spread ponderado por saldo
        tasa_wp = (grp["MARGEN_VALOR"] * grp["SDO_US"]).sum() / saldo
        tpv     = (grp["ATM_YEARS"]    * grp["SDO_US"]).sum() / saldo

        result["rates"][inst_id] = {
            "tipo": tipo, "moneda": mda,
            "tasa_wp": round(tasa_wp, 4),
            "tpv":     round(tpv, 2),
            "saldo_usd": saldo,
        }
        if inst_id in [i[0] for i in INSTRUMENTS]:
            result["oracle_weights"][inst_id] = saldo / total_ext

        tipo_lbl = "Variable" if tipo == "VARIABLE" else "Fija"
        tasa_lbl = (f"{tasa_wp:.3f}% (spread s/índice)"
                    if tipo == "VARIABLE" else f"{tasa_wp:.3f}% (nominal anual)")
        report_lines.append(f"  │  {inst_id:<16} {mda:>6} {tipo_lbl:>9}  "
              f"{saldo/1e6:>11.1f}M  {part:>6.2f}%  {tasa_lbl:>39}  {tpv:>5.2f}y")

    report_lines.append(f"  │  {'-'*90}")
    report_lines.append(f"  │  TOTAL EXTERNO: ${total_ext/1e6:.1f}M USD")
    report_lines.append(f"  │  Monedas en portafolio: {', '.join(currencies)}")
    report_lines.append(f"  └───────────────────────────────────────────────────────────────")

    for line in report_lines:
        print(line)
    result["report"] = "\n".join(report_lines)

    # Normalizar pesos
    w_sum = sum(result["oracle_weights"].values())
    if w_sum > 0:
        result["oracle_weights"] = {k: v/w_sum
                                    for k, v in result["oracle_weights"].items()}
    result["ok"] = True
    return result

# ══════════════════════════════════════════════════════════════════════════════
# 4. LECTOR DE PERFIL DE VENCIMIENTOS  (xlsm)
# ══════════════════════════════════════════════════════════════════════════════
def load_from_perfil(perfil_path: str, oracle_result: dict = None) -> dict:
    """
    Lee el libro 'Perfil de Vencimientos MHCP' y extrae:
      - Amortizaciones anuales (COP millones) por instrumento
      - TPV ponderado por saldo para instrumentos internos
      - % que vence en año 1
      - Pesos de referencia desde el stock actual

    Mapeo de columnas (TOTAL PESOS COP section, cols 13-19):
      col 13 = TES pesos    → DI_COP_F
      col 14 = TES UVR      → DI_UVR_F
      col 15 = Otros Interna → añadido a DI_COP_F
      col 16 = Bonos Externos → externo (repartido por Oracle)
      col 17 = TRS           → externo
      col 18 = Multi         → externo
      col 19 = TOTAL
    """
    result = {
        "ok": False, "log": [], "tpv": {}, "amort_profile": {},
        "pct_amort_yr1": {}, "ref_year": 2026,
        "stock_cop_mm": {}, "pesos_ref": {}, "report": ""
    }

    if not os.path.exists(perfil_path):
        result["log"].append(f"⚠  Perfil no encontrado: '{perfil_path}'")
        return result

    sheets = pd.ExcelFile(perfil_path, engine="openpyxl").sheet_names
    latest = sheets[-1]
    df_raw = pd.read_excel(perfil_path, sheet_name=latest,
                            engine="openpyxl", header=None)
    result["log"].append(
        f"✔  Perfil leído: hoja '{latest}' "
        f"({df_raw.shape[0]} filas × {df_raw.shape[1]} cols)"
    )

    # ── Tipo de cambio de referencia ──────────────────────────────────────
    trm = 3670.0
    try:
        row2 = df_raw.iloc[2]
        tc_idx = [j for j, v in enumerate(row2)
                  if str(v) == "Tasa de cambio"]
        if tc_idx:
            trm = float(row2.iloc[tc_idx[0] + 1])
    except Exception:
        pass
    result["log"].append(f"  TRM referencia: {trm:,.2f} COP/USD")

    # ── Extraer datos de amortización (filas año 2026-2070) ───────────────
    REF_YEAR = 2026
    amort_data = {}   # {año: {col: valor}}

    for i in range(7, df_raw.shape[0]):
        ano_val = df_raw.iloc[i].iloc[0]
        try:
            ano = int(float(str(ano_val)))
            if 2026 <= ano <= 2075:
                row_dict = {}
                for col in [13, 14, 15, 16, 17, 18, 19]:
                    v = df_raw.iloc[i].iloc[col]
                    row_dict[col] = float(v) if (v and str(v) not in ("nan","None")) else 0.0
                amort_data[ano] = row_dict
        except Exception:
            continue

    if not amort_data:
        result["log"].append("⚠  No se encontraron filas de datos en el Perfil.")
        return result

    años = sorted(amort_data.keys())
    t    = np.array([yr - REF_YEAR + 0.5 for yr in años])   # mid-year

    # ── Arrays de amortización por instrumento ────────────────────────────
    tes_cop    = np.array([amort_data[yr][13] for yr in años])
    tes_uvr    = np.array([amort_data[yr][14] for yr in años])
    otros_int  = np.array([amort_data[yr][15] for yr in años])
    bonos_ext  = np.array([amort_data[yr][16] for yr in años])
    trs        = np.array([amort_data[yr][17] for yr in años])
    multi      = np.array([amort_data[yr][18] for yr in años])
    total_arr  = np.array([amort_data[yr][19] for yr in años])

    cop_amorts = tes_cop + otros_int     # DI_COP_F (TES pesos + Otros Interna)
    uvr_amorts = tes_uvr                 # DI_UVR_F
    ext_amorts = bonos_ext + trs + multi # total externo COP mm

    # ── Stock total (suma de todas las amortizaciones) ────────────────────
    stock = {
        "DI_COP_F": cop_amorts.sum(),
        "DI_UVR_F": uvr_amorts.sum(),
        "EXT_TOTAL": ext_amorts.sum(),
        "TOTAL":     total_arr.sum(),
    }
    result["stock_cop_mm"] = stock

    # ── Pesos de referencia desde el stock ────────────────────────────────
    if stock["TOTAL"] > 0:
        result["pesos_ref"]["DI_COP_F"] = stock["DI_COP_F"] / stock["TOTAL"]
        result["pesos_ref"]["DI_UVR_F"] = stock["DI_UVR_F"] / stock["TOTAL"]
        result["pesos_ref"]["EXT"]      = stock["EXT_TOTAL"] / stock["TOTAL"]

    # ── TPV (tiempo promedio al vencimiento) ──────────────────────────────
    def wtd_tpv(amorts, t_arr):
        s = amorts.sum()
        return float((amorts * t_arr).sum() / s) if s > 0 else 0.0

    tpv_cop = wtd_tpv(cop_amorts, t)
    tpv_uvr = wtd_tpv(uvr_amorts, t)
    tpv_ext = wtd_tpv(ext_amorts, t)
    result["tpv"]["DI_COP_F"] = round(tpv_cop, 2)
    result["tpv"]["DI_UVR_F"] = round(tpv_uvr, 2)
    result["tpv"]["EXT_AGG"]  = round(tpv_ext, 2)

    # TPV externos por instrumento desde Oracle
    if oracle_result and oracle_result.get("ok"):
        for inst_id, rd in oracle_result["rates"].items():
            if inst_id.startswith("DE_"):
                result["tpv"][inst_id] = rd["tpv"]

    # ── % amortización año 1 ──────────────────────────────────────────────
    for inst_id, amorts in [("DI_COP_F", cop_amorts), ("DI_UVR_F", uvr_amorts)]:
        s = amorts.sum()
        yr1 = amorts[t <= 1.0].sum()
        result["pct_amort_yr1"][inst_id] = round(yr1/s*100, 2) if s > 0 else 0.0

    # ── Perfil dict ───────────────────────────────────────────────────────
    result["amort_profile"]["DI_COP_F"] = {yr: cop_amorts[i] for i, yr in enumerate(años)}
    result["amort_profile"]["DI_UVR_F"] = {yr: uvr_amorts[i] for i, yr in enumerate(años)}
    result["amort_profile"]["EXT_TOTAL"] = {yr: ext_amorts[i] for i, yr in enumerate(años)}

    # ── Print resumen ─────────────────────────────────────────────────────
    report_lines = []
    total_cop_mm = stock["TOTAL"]
    report_lines.append(f"\n  ┌─ PERFIL DE VENCIMIENTOS (hoja: {latest}) ──────────────────────")
    report_lines.append(f"  │  Stock total: {total_cop_mm/1e6:,.1f} billones COP")
    report_lines.append(f"  │  {'Instrumento':<18} {'Stock COP Mm':>14} {'Part%':>7} "
          f"{'TPV':>6} {'%Vto Yr1':>10}")
    report_lines.append(f"  │  {'-'*60}")
    rows_pv = [
        ("DI_COP_F (TES+Otros)", stock["DI_COP_F"], tpv_cop,
         result["pct_amort_yr1"]["DI_COP_F"]),
        ("DI_UVR_F (TES UVR)",   stock["DI_UVR_F"], tpv_uvr,
         result["pct_amort_yr1"]["DI_UVR_F"]),
        ("Externo (Bonos+TRS+Multi)", stock["EXT_TOTAL"], tpv_ext, None),
    ]
    for name, stk, tpv_v, pct1 in rows_pv:
        pct = stk/total_cop_mm*100 if total_cop_mm > 0 else 0
        pct1_str = f"{pct1:.1f}%" if pct1 is not None else "—"
        report_lines.append(f"  │  {name:<22} {stk:>14,.0f} {pct:>6.1f}% {tpv_v:>5.2f}y {pct1_str:>9}")

    # ── Primeros años del perfil ──────────────────────────────────────────
    report_lines.append(f"  │  {'-'*60}")
    report_lines.append(f"  │  Amortizaciones (COP Millones, primeros 8 años):")
    report_lines.append(f"  │  {'Año':<6} {'TES COP':>12} {'TES UVR':>12} "
          f"{'Otros Int':>11} {'Ext Total':>12}")
    report_lines.append(f"  │  {'-'*60}")
    for i, yr in enumerate(años[:8]):
        report_lines.append(f"  │  {yr:<6} {tes_cop[i]:>12,.0f} {tes_uvr[i]:>12,.0f} "
              f"{otros_int[i]:>11,.0f} {ext_amorts[i]:>12,.0f}")
    report_lines.append(f"  └───────────────────────────────────────────────────────────────")

    for line in report_lines:
        print(line)
    result["report"] = "\n".join(report_lines)

    result["ok"] = True
    result["ref_year"] = REF_YEAR
    return result



def load_from_template(template_path: str) -> dict:
    """
    Lee TODOS los parámetros del modelo desde MTDS_Bloomberg_Template.xlsx.

    Fuentes de datos (en orden de prioridad):
      1. Hoja 'Parametros_Modelo'  → col B (ID) + col D (Valor Calibrado)
      2. Hoja 'Tasas_y_Mercado'    → col C (Ticker) + col E (Valor Actual)
         usando TICKER_TO_PARAM si el param no estaba en Parametros_Modelo
      3. Hoja 'Portafolio_Actual'  → saldos, cupones, TPV/TPR por instrumento

    Retorna dict con:
      'params'       → dict PARAMS actualizado con valores del template
      'portfolio'    → dict {inst_id: {saldo, cupon, tpv, tpr, amorts...}}
      'market_rates' → dict {ticker: valor} (todas las tasas de mercado)
      'ref_weights'  → np.array pesos MFMP 25 (desde saldos o defaults)
      'log'          → lista de mensajes de carga
    """
    out = {
        "params":       PARAMS.copy(),
        "portfolio":    {},
        "market_rates": {},
        "ref_weights":  np.array([REF_MFMP25[i[0]] for i in INSTRUMENTS]),
        "log":          [],
    }
    skip_col_b = {None, "", "ID Variable"}
    inst_ids   = {i[0] for i in INSTRUMENTS}

    # ── Intentar abrir el template ────────────────────────────────────────
    if not os.path.exists(template_path):
        out["log"].append(f"⚠  Plantilla no encontrada: '{template_path}'")
        out["log"].append("   Usando parámetros por defecto (PARAMS).")
        return out

    try:
        wb = load_workbook(template_path, data_only=True)
    except Exception as e:
        out["log"].append(f"⚠  Error al abrir plantilla: {e}")
        return out

    loaded_params = set()   # IDs ya cargados (para respetar prioridades)

    # ── FUENTE 1: Parametros_Modelo ───────────────────────────────────────
    if "Parametros_Modelo" in wb.sheetnames:
        ws = wb["Parametros_Modelo"]
        for row in ws.iter_rows(min_row=2, values_only=True):
            param_id = row[1]                       # col B = ID Variable
            value    = row[3]                       # col D = Valor Calibrado
            if param_id in skip_col_b or value is None:
                continue
            try:
                v = float(str(value).replace("%", "").strip())
                out["params"][str(param_id)] = v
                loaded_params.add(str(param_id))
            except (TypeError, ValueError):
                pass
        out["log"].append(
            f"✔  Parametros_Modelo: {len(loaded_params)} parámetros leídos"
        )

    # ── FUENTE 2: Tasas_y_Mercado (via TICKER_TO_PARAM) ──────────────────
    tasas_loaded = 0
    if "Tasas_y_Mercado" in wb.sheetnames:
        ws = wb["Tasas_y_Mercado"]
        for row in ws.iter_rows(min_row=3, values_only=True):
            ticker = row[2]                         # col C = Bloomberg Ticker
            value  = row[4]                         # col E = Valor Actual
            if not ticker or value is None:
                continue
            ticker = str(ticker).strip()
            try:
                v = float(str(value).replace("%", "").strip())
                out["market_rates"][ticker] = v
                # Actualiza PARAMS solo si el ticker tiene mapeo Y
                # el parámetro no fue ya cargado desde Parametros_Modelo
                if ticker in TICKER_TO_PARAM:
                    pkey = TICKER_TO_PARAM[ticker]
                    if pkey not in loaded_params:
                        out["params"][pkey] = v
                        loaded_params.add(pkey)
                        tasas_loaded += 1
            except (TypeError, ValueError):
                pass
        mr_total = len(out["market_rates"])
        out["log"].append(
            f"✔  Tasas_y_Mercado: {mr_total} tasas de mercado leídas"
            + (f", {tasas_loaded} actualizaron PARAMS" if tasas_loaded else
               " (todos los params ya estaban en Parametros_Modelo)")
        )

    # ── FUENTE 3: Portafolio_Actual ───────────────────────────────────────
    if "Portafolio_Actual" in wb.sheetnames:
        ws = wb["Portafolio_Actual"]
        saldos, cupones_leidos = {}, 0

        for row in ws.iter_rows(min_row=3, values_only=True):
            inst_id = row[0]                        # col A = ID
            if not inst_id or str(inst_id) not in inst_ids:
                continue
            iid = str(inst_id)

            def safe_float(x):
                if x is None:
                    return None
                try:
                    return float(str(x).replace("%", "").replace(",", "").strip())
                except (ValueError, TypeError):
                    return None

            saldo  = safe_float(row[4])             # col E — Saldo COP Bn
            cupon  = safe_float(row[6])             # col G — Cupón/Tasa %
            tpv    = safe_float(row[7])             # col H — TPV años
            tpr    = safe_float(row[8])             # col I — TPR años
            pct1   = safe_float(row[9])             # col J — % Vto Año 1
            am1    = safe_float(row[10])            # col K — Amort Año 1
            am2    = safe_float(row[11])            # col L — Amort Año 2
            am3    = safe_float(row[12])            # col M — Amort Año 3
            am45   = safe_float(row[13])            # col N — Amort Año 4-5

            # Participación desde col F ("40%") como fallback si no hay saldo
            part_str = row[5]
            part_pct = safe_float(part_str)         # puede ser "40%" → 40.0

            out["portfolio"][iid] = {
                "saldo_cop_bn":  saldo,
                "part_pct":      part_pct,
                "cupon_pct":     cupon,
                "tpv_anos":      tpv,
                "tpr_anos":      tpr,
                "pct_vto_1":     pct1,
                "amort_1":       am1,
                "amort_2":       am2,
                "amort_3":       am3,
                "amort_45":      am45,
            }
            if saldo is not None:
                saldos[iid] = saldo
            if cupon is not None:
                cupones_leidos += 1

        # Pesos de referencia desde saldos (si el usuario los ingresó)
        if len(saldos) >= 2:
            total = sum(saldos.values())
            if total > 0:
                out["ref_weights"] = np.array([
                    saldos.get(i[0], 0.0) / total for i in INSTRUMENTS
                ])
                out["log"].append(
                    f"✔  Portafolio_Actual: pesos de referencia calculados "
                    f"desde saldos ({len(saldos)} instrumentos, "
                    f"COP {total:,.1f} Bn)"
                )
        else:
            # Pesos desde col F (participación %)
            parts = {}
            for iid, d in out["portfolio"].items():
                if d["part_pct"] is not None:
                    parts[iid] = d["part_pct"]
            if parts:
                total_p = sum(parts.values())
                if total_p > 0:
                    out["ref_weights"] = np.array([
                        parts.get(i[0], 0.0) / total_p for i in INSTRUMENTS
                    ])
                    out["log"].append(
                        f"✔  Portafolio_Actual: pesos de referencia desde "
                        f"participaciones (col F)"
                    )

        inst_con_tpv = sum(
            1 for d in out["portfolio"].values() if d["tpv_anos"] is not None
        )
        out["log"].append(
            f"✔  Portafolio_Actual: {len(out['portfolio'])} instrumentos | "
            f"{cupones_leidos} cupones | "
            f"{inst_con_tpv} instrumentos con TPV/TPR"
        )

    # ── Usar cupones del portafolio para afinar tasas base ────────────────
    # Si el usuario ingresó el cupón real del instrumento, se usa como
    # tasa base para ese instrumento (sobreescribe params globales)
    cupon_map = {
        "DI_COP_F": "cop_fixed_rate",
        "DI_UVR_F": "uvr_real_rate",
        "DE_USD_F": "usd_fixed_rate",
        "DE_EUR_F": "eur_fixed_rate",
        "DE_CHF_F": "chf_fixed_rate",
    }
    for iid, pkey in cupon_map.items():
        d = out["portfolio"].get(iid, {})
        if d.get("cupon_pct") is not None and iid not in ("DI_UVR_F",):
            # Solo sobreescribe si no fue ya definido explícitamente en
            # Parametros_Modelo por el usuario
            pass   # Respeta Parametros_Modelo; cupón es solo informativo

    out["log"].append(
        f"─── Total parámetros efectivos cargados: {len(loaded_params)}"
    )
    return out



STRESS = {
    "base":        {"rate_shock_bps": 0,   "fx_shock_pct": 0.0},
    "tasa+200":    {"rate_shock_bps": 200, "fx_shock_pct": 0.0},
    "depr30":      {"rate_shock_bps": 0,   "fx_shock_pct": -0.30},
    "combinado":   {"rate_shock_bps": 200, "fx_shock_pct": -0.30},
}

# ══════════════════════════════════════════════════════════════════════════════
# 4. INDICADORES DE CARTERA BM-FMI  (Apéndice III)
# ══════════════════════════════════════════════════════════════════════════════
def portfolio_indicators(w: np.ndarray, portfolio: dict = None) -> dict:
    """
    Calcula TPV, TPR, % FX, % variable, % refijación año 1.
    Si 'portfolio' proviene del template, usa los TPV/TPR reales del portafolio.
    De lo contrario usa los valores por defecto definidos en INSTRUMENTS.
    """
    # ATM y ATR: template tiene prioridad sobre defaults de INSTRUMENTS
    atm_vals = np.array([
        (portfolio.get(inst[0], {}).get("tpv_anos") or inst[4])
        if portfolio else inst[4]
        for inst in INSTRUMENTS
    ])
    atr_vals = np.array([
        (portfolio.get(inst[0], {}).get("tpr_anos") or inst[5])
        if portfolio else inst[5]
        for inst in INSTRUMENTS
    ])

    is_fx  = np.array([inst[6] for inst in INSTRUMENTS], dtype=float)
    is_var = np.array([inst[7] for inst in INSTRUMENTS], dtype=float)

    tpv = float(np.dot(w, atm_vals))
    tpr = float(np.dot(w, atr_vals))
    pct_fx  = float(np.dot(w, is_fx)  * 100)
    pct_var = float(np.dot(w, is_var) * 100)
    pct_refij1 = pct_var   # instrumentos variables rebalancean ≤ 1 año

    # Perfil de amortización: usa amortizaciones reales si están en el template
    amort = {}
    for yr, col_key in enumerate(["amort_1","amort_2","amort_3","amort_45"], 1):
        total_am = 0.0
        for idx, inst in enumerate(INSTRUMENTS):
            d = (portfolio or {}).get(inst[0], {})
            am_inst = d.get(col_key)
            if am_inst is not None:
                # porcentaje del stock total aportado por este instrumento
                total_am += am_inst * w[idx]
            else:
                # fallback: amortización lineal según ATM
                total_am += w[idx] * (1.0 / atm_vals[idx]) * 100
        yr_label = f"Año {yr}" if yr <= 3 else "Años 4-5"
        amort[yr_label] = round(total_am, 2)

    return {
        "TPV_años":            round(tpv, 2),
        "TPR_años":            round(tpr, 2),
        "pct_FX":              round(pct_fx, 2),
        "pct_variable":        round(pct_var, 2),
        "pct_refijacion_año1": round(pct_refij1, 2),
        "pct_COP_UVR":         round((w[0]+w[1])*100, 2),
        "amortizacion":        amort,
    }

# ══════════════════════════════════════════════════════════════════════════════
# 5. CÁLCULO DE COSTO DETERMINISTA  (stress scenarios, BM-FMI estilo)
# ══════════════════════════════════════════════════════════════════════════════
def deterministic_cost(w: np.ndarray, p: dict, shock: dict) -> dict:
    """
    Costo de intereses en escenario determinista (base o stress).
    Retorna: intereses/PIB (%), intereses/Ingresos (%), tasa promedio ponderada.
    """
    rs = shock["rate_shock_bps"] / 10_000   # en decimal
    fx = shock["fx_shock_pct"]              # depreciación (negativo = depreciación)

    # Tasas efectivas (con shock y depreciación de moneda = aumento de costo en COP)
    fx_mult = 1.0 / (1 + fx) if fx < 0 else 1.0   # depreciación COP → costo FX sube

    rates = {
        "DI_COP_F": p["cop_fixed_rate"]/100 + rs,
        "DI_UVR_F": (p["uvr_real_rate"] + p["uvr_inflation"])/100 + rs,
        "DE_USD_F": (p["usd_fixed_rate"]/100 + rs) * fx_mult,
        "DE_EUR_F": (p["eur_fixed_rate"]/100 + rs) * fx_mult,
        "DE_EUR_V": ((p["euribor_base"] + p["eur_spread_eurib"])/100 + rs) * fx_mult,
        "DE_USD_V": ((p["sofr_base"] + p["usd_spread_sofr"])/100 + rs) * fx_mult,
        "DE_CHF_F": (p["chf_fixed_rate"]/100 + rs) * fx_mult,
        "DE_CHF_V": ((p["saron_base"] + p["chf_spread_saron"])/100 + rs) * fx_mult,
    }

    weighted_rate = sum(w[i] * rates[INSTRUMENTS[i][0]] for i in range(N_INST))
    int_pct_gdp   = weighted_rate * p["debt_pct_gdp"]
    int_pct_rev   = int_pct_gdp / p["revenues_pct_gdp"] * 100

    return {
        "tasa_ponderada": round(weighted_rate * 100, 4),
        "int_pct_gdp":    round(int_pct_gdp, 4),
        "int_pct_rev":    round(int_pct_rev, 4),
    }

def stress_analysis(w: np.ndarray, p: dict) -> dict:
    """Ejecuta todos los escenarios de estrés y calcula delta vs. base."""
    results = {}
    base = deterministic_cost(w, p, STRESS["base"])
    for name, shock in STRESS.items():
        r = deterministic_cost(w, p, shock)
        r["delta_pct_gdp"] = round(r["int_pct_gdp"] - base["int_pct_gdp"], 4)
        results[name] = r
    return results

# ══════════════════════════════════════════════════════════════════════════════
# 6. GENERADOR DE ESCENARIOS MONTE CARLO  (1,000 escenarios, 5 años)
# ══════════════════════════════════════════════════════════════════════════════
class ScenarioGenerator:
    """Proceso Vasicek para tasas + GBM correlacionado para FX."""

    _CORR = None   # cache

    @classmethod
    def _get_corr(cls):
        if cls._CORR is None:
            C = np.eye(11)
            pairs = [
                (0,1,0.55),(0,2,0.30),(2,3,0.78),(2,4,0.65),(3,4,0.82),
                (5,6,0.72),(5,7,0.60),(6,7,0.76),(2,5,0.85),(3,6,0.82),
                (4,7,0.80),(8,9,0.62),(8,10,0.52),(9,10,0.70),
                (2,8,-0.28),(0,8,0.35),
            ]
            for i, j, v in pairs:
                C[i,j] = C[j,i] = v
            evals, evecs = np.linalg.eigh(C)
            C = evecs @ np.diag(np.maximum(evals, 1e-8)) @ evecs.T
            cls._CORR = np.linalg.cholesky(C)
        return cls._CORR

    def __init__(self, p: dict, n: int = 1000, T: int = 5):
        self.p, self.n, self.T = p, n, T

    def generate(self) -> dict:
        p, n, T = self.p, self.n, self.T
        L = self._get_corr()
        Z = np.random.randn(n, T, 11) @ L.T

        means = np.array([
            p["cop_fixed_rate"], p["uvr_inflation"],
            p["usd_fixed_rate"], p["eur_fixed_rate"], p["chf_fixed_rate"],
            p["sofr_base"], p["euribor_base"], p["saron_base"]
        ])
        vols = np.array([
            p["vol_cop_rate"], p["vol_uvr_inf"],
            p["vol_usd_rate"], p["vol_eur_rate"], p["vol_chf_rate"],
            p["vol_sofr"], p["vol_euribor"], p["vol_saron"]
        ])
        floors = np.array([1.0, 1.0, 0.5, -0.5, -1.0, 0.5, -0.5, -1.0])

        # Tasas (Vasicek discreto)
        rates = np.zeros((n, T, 8))
        kappa = 0.35
        for t in range(T):
            for k in range(8):
                prev_k = means[k] if t == 0 else rates[:, t-1, k]
                rates[:, t, k] = np.maximum(
                    prev_k + kappa*(means[k]-prev_k) + Z[:,t,k]*vols[k],
                    floors[k]
                )

        # FX (GBM)
        spots  = np.array([p["usdcop_spot"], p["eurcop_spot"], p["chfcop_spot"]])
        drifts = np.array([p["usdcop_drift"], p["eurcop_drift"], p["chfcop_drift"]]) / 100
        vfx    = np.array([p["vol_usdcop"], p["vol_eurcop"], p["vol_chfcop"]]) / 100

        fx = np.zeros((n, T, 3))
        for t in range(T):
            prev_fx = spots if t == 0 else fx[:, t-1, :]
            for k in range(3):
                base_v = spots[k] if t == 0 else fx[:, t-1, k]
                fx[:, t, k] = base_v * np.exp(
                    (drifts[k] - 0.5*vfx[k]**2) + vfx[k]*Z[:, t, 8+k]
                )

        return {"rates": rates, "fx": fx}

# ══════════════════════════════════════════════════════════════════════════════
# 7. CALCULADOR DE COSTO-RIESGO ESTOCÁSTICO
# ══════════════════════════════════════════════════════════════════════════════
class CostRiskCalc:
    """
    Calcula el costo de intereses como % del PIB sobre N escenarios.

    AJUSTES DE CALIBRACIÓN (refleja costo económico real):

    UVR: el principal se indexa a la inflación, por lo que el costo en t
         = (tasa_real + inflación_t) × w_UVR × deuda/PIB
         PERO la deuda UVR misma crece con inflación acumulada, elevando
         el costo en COP. Se añade factor de indexación acumulada:
         costo_UVR_t = (real + infl_t) × Π(1+infl_s, s≤t) × w × D/Y

    FX:  el riesgo cambiario captura tanto el cupón como la apreciación
         del principal. Se usa adj_fx = fx_t / fx_0 para el cupón (ya
         implementado). Además se añade un "spread de riesgo de principal"
         proporcional al drift esperado (calibrado por instrumento).
    """

    def __init__(self, scen: dict, p: dict):
        self.scen = scen
        self.p = p

    def _interest_pct_gdp(self, w: np.ndarray) -> np.ndarray:
        """Pago de intereses / PIB por escenario [N_SCEN] (promedio del horizonte)."""
        rates = self.scen["rates"]   # [n, T, 8]
        fx    = self.scen["fx"]      # [n, T, 3]
        p     = self.p
        n, T  = rates.shape[0], rates.shape[1]

        fx0 = np.array([p["usdcop_spot"], p["eurcop_spot"], p["chfcop_spot"]])
        ip  = np.zeros((n, T))

        # Acumuladores de indexación para UVR
        cum_uvr_index = np.ones(n)   # factor Π(1+infl_t)

        for t in range(T):
            adj_usd = fx[:, t, 0] / fx0[0]
            adj_eur = fx[:, t, 1] / fx0[1]
            adj_chf = fx[:, t, 2] / fx0[2]

            infl_t  = rates[:, t, 1] / 100   # inflación COP en t
            cum_uvr_index = cum_uvr_index * (1 + infl_t)  # factor de indexación acumulada

            # ── UVR: incluir indexación del principal ────────────────────
            # costo = (real + infl) × principal_indexado
            # real interest + principal accretion cada periodo
            uvr_total_rate = (rates[:, t, 1] + p["uvr_real_rate"]) / 100
            uvr_cost = w[1] * uvr_total_rate * cum_uvr_index

            # ── COP fija ─────────────────────────────────────────────────
            cop_cost = w[0] * rates[:, t, 0] / 100

            # ── Externos: cupón × factor FX ──────────────────────────────
            usd_f = w[2] * rates[:, t, 2] / 100 * adj_usd
            eur_f = w[3] * rates[:, t, 3] / 100 * adj_eur
            eur_v = w[4] * (rates[:, t, 6] + p["eur_spread_eurib"]) / 100 * adj_eur
            usd_v = w[5] * (rates[:, t, 5] + p["usd_spread_sofr"])  / 100 * adj_usd
            chf_f = w[6] * rates[:, t, 4] / 100 * adj_chf
            chf_v = w[7] * (rates[:, t, 7] + p["chf_spread_saron"]) / 100 * adj_chf

            cost_t = cop_cost + uvr_cost + usd_f + eur_f + eur_v + usd_v + chf_f + chf_v
            ip[:, t] = cost_t * p["debt_pct_gdp"]

        return ip.mean(axis=1)   # promedio del horizonte → [n]

    def metrics(self, w: np.ndarray) -> dict:
        ip  = self._interest_pct_gdp(w)
        p95 = np.percentile(ip, 95)
        return {
            "cost_ev":  float(ip.mean()),
            "cost_std": float(ip.std()),
            "cvar95":   float(ip[ip >= p95].mean()),
            "p5":       float(np.percentile(ip, 5)),
            "p50":      float(np.percentile(ip, 50)),
            "p95":      float(p95),
            "dist":     ip,
        }

    def scenario_dataframe(self, w: np.ndarray, n_scenarios: int = 1000) -> pd.DataFrame:
        """Retorna DataFrame con los N escenarios y sus métricas de costo."""
        rates = self.scen["rates"]
        fx    = self.scen["fx"]
        p     = self.p
        n, T  = rates.shape[0], rates.shape[1]
        fx0   = np.array([p["usdcop_spot"], p["eurcop_spot"], p["chfcop_spot"]])

        rows = []
        cum_uvr = np.ones(n)
        cost_by_t = np.zeros((n, T))
        cum_uvr_t = np.ones((n, T))

        # Compute running index
        for t in range(T):
            infl_t = rates[:, t, 1] / 100
            cum_uvr = cum_uvr * (1 + infl_t)
            cum_uvr_t[:, t] = cum_uvr

        for scen_i in range(min(n, n_scenarios)):
            row = {"Escenario": scen_i + 1}
            costs_yr = []
            cum_idx = 1.0
            for t in range(T):
                infl_t = rates[scen_i, t, 1] / 100
                cum_idx *= (1 + infl_t)
                adj_usd = fx[scen_i, t, 0] / fx0[0]
                adj_eur = fx[scen_i, t, 1] / fx0[1]
                adj_chf = fx[scen_i, t, 2] / fx0[2]
                uvr_r   = (rates[scen_i, t, 1] + p["uvr_real_rate"]) / 100
                c = (
                    w[0]*rates[scen_i,t,0]/100 +
                    w[1]*uvr_r*cum_idx +
                    w[2]*rates[scen_i,t,2]/100*adj_usd +
                    w[3]*rates[scen_i,t,3]/100*adj_eur +
                    w[4]*(rates[scen_i,t,6]+p["eur_spread_eurib"])/100*adj_eur +
                    w[5]*(rates[scen_i,t,5]+p["usd_spread_sofr"])/100*adj_usd +
                    w[6]*rates[scen_i,t,4]/100*adj_chf +
                    w[7]*(rates[scen_i,t,7]+p["chf_spread_saron"])/100*adj_chf
                ) * p["debt_pct_gdp"]
                row[f"Int_PIB_Año{2026+t}"] = round(c, 5)
                costs_yr.append(c)
                # Tasas de mercado en este escenario
                row[f"TES_COP_Año{2026+t}"]  = round(rates[scen_i,t,0], 3)
                row[f"Inflacion_Año{2026+t}"] = round(rates[scen_i,t,1], 3)
                row[f"SOFR_Año{2026+t}"]      = round(rates[scen_i,t,5], 3)
                row[f"USDCOP_Año{2026+t}"]    = round(fx[scen_i,t,0], 1)
                row[f"CHFCOP_Año{2026+t}"]    = round(fx[scen_i,t,2], 1)
            row["Int_PIB_Promedio"] = round(np.mean(costs_yr), 5)
            row["Int_PIB_Max"]      = round(np.max(costs_yr), 5)
            rows.append(row)

        return pd.DataFrame(rows)


# ══════════════════════════════════════════════════════════════════════════════
# 8. OPTIMIZADOR  (SLSQP multi-arranque, restricciones EDMP Colombia)
# ══════════════════════════════════════════════════════════════════════════════
class MTDSOptimizer:
    """
    Función objetivo:  min  E[costo] + λ·σ[costo]
    Restricciones alineadas con lineamientos MHCP / BM-FMI Colombia.
    """

    def __init__(self, calc: CostRiskCalc, lam: float = 1.5, ref_w: np.ndarray = None):
        self.calc = calc
        self.lam  = lam

        # Original default bounds
        self.bounds = [
            (0.05, 0.55),   # DI COP Fija
            (0.05, 0.35),   # DI UVR Fija
            (0.01, 0.35),   # DE USD Fija
            (0.01, 0.20),   # DE EUR Fija
            (0.00, 0.12),   # DE EUR Variable
            (0.00, 0.12),   # DE USD Variable
            (0.00, 0.10),   # DE CHF Fija
            (0.00, 0.06),   # DE CHF Variable
        ]

        # Ajuste de cotas: si el instrumento ya tiene participación (ref_w > 0),
        # asegurar que la cota inferior sea por lo menos 1% (0.01)
        if ref_w is not None:
            for i in range(N_INST):
                if ref_w[i] > 0.001:
                    low, high = self.bounds[i]
                    self.bounds[i] = (max(low, 0.01), high)

    @staticmethod
    def _constraints():
        """
        Restricciones del MTDS 2026:
        ─ Lineamiento principal: moneda local (COP+UVR) ≥ 60 %
        ─ COP (fija): mín. 10 % para mantener mercado interno TES
        ─ UVR ≤ 35 % (cap de indexación)
        ─ Tasa fija ≥ 55 % del total (gestión riesgo de tasa)
        ─ Límites externos por moneda: refleja composición actual Oracle
          · USD ≤ 30 % (67 % del externo × 40 % máx externo ≈ 27 %)
          · EUR ≤ 15 % (15 % del externo × 40 %)
          · CHF ≤ 16 % (15.8 % del externo × 40 %)
        ─ Deuda externa total ≤ 40 % (= 1 - 60 % interno)
        """
        return [
            # Suma = 100 %
            {"type": "eq",   "fun": lambda w: w.sum() - 1.0},
            # ── Lineamiento principal: COP + UVR ≥ 60 % ─────────────────
            {"type": "ineq", "fun": lambda w: (w[0]+w[1]) - 0.60},
            {"type": "ineq", "fun": lambda w: 0.82 - (w[0]+w[1])},   # cap razonable
            # COP fija mínimo 10 %
            {"type": "ineq", "fun": lambda w: w[0] - 0.10},
            # UVR ≤ 35 %
            {"type": "ineq", "fun": lambda w: 0.35 - w[1]},
            # ── Tasa fija ≥ 55 % ─────────────────────────────────────────
            {"type": "ineq", "fun": lambda w: (w[0]+w[1]+w[2]+w[3]+w[6]) - 0.55},
            # ── Deuda externa total ≤ 40 % ────────────────────────────────
            {"type": "ineq", "fun": lambda w: 0.40 - (w[2]+w[3]+w[4]+w[5]+w[6]+w[7])},
            # ── Límites por moneda externa ───────────────────────────────
            {"type": "ineq", "fun": lambda w: 0.30 - (w[2]+w[5])},   # USD ≤ 30 %
            {"type": "ineq", "fun": lambda w: 0.15 - (w[3]+w[4])},   # EUR ≤ 15 %
            {"type": "ineq", "fun": lambda w: 0.16 - (w[6]+w[7])},   # CHF ≤ 16 %
        ]

    def _obj(self, w):
        m = self.calc.metrics(w)
        return m["cost_ev"] + self.lam * m["cost_std"]

    def optimize(self, n_starts: int = 30) -> dict:
        best, best_val = None, np.inf
        for _ in range(n_starts):
            w0 = np.random.dirichlet(np.ones(N_INST))
            try:
                res = minimize(self._obj, w0, method="SLSQP",
                               bounds=self.bounds,
                               constraints=self._constraints(),
                               options={"maxiter": 2000, "ftol": 1e-12})
                if res.success and res.fun < best_val:
                    best_val, best = res.fun, res
            except Exception:
                continue
        if best is None:
            raise RuntimeError("Optimización no convergió.")
        w = np.maximum(best.x, 0); w /= w.sum()
        return {"weights": w, "metrics": self.calc.metrics(w)}

    def efficient_frontier(self, n_pts: int = 40) -> pd.DataFrame:
        records = []
        for lam in np.logspace(-0.5, 1.2, n_pts):
            self.lam = lam
            try:
                r = self.optimize(n_starts=15)
                m = r["metrics"]
                records.append({
                    "Lambda":     round(lam, 4),
                    "Costo_EV":   round(m["cost_ev"],  4),
                    "Riesgo_Std": round(m["cost_std"], 4),
                    "CVaR_95":    round(m["cvar95"],   4),
                    **{f"w_{INSTRUMENTS[i][0]}": round(r["weights"][i], 4)
                       for i in range(N_INST)},
                })
            except Exception:
                continue
        return pd.DataFrame(records)

# ══════════════════════════════════════════════════════════════════════════════
# 9. PLANTILLA BLOOMBERG  (Excel profesional)
# ══════════════════════════════════════════════════════════════════════════════
def build_bloomberg_template(path: str):
    """Genera la plantilla de recolección de datos Bloomberg."""
    wb = Workbook()

    NAVY, BLUE, LBLUE = "1F3864", "2E74B5", "D6E4F0"
    GOLD, GREEN       = "FFC000", "E2EFDA"
    WHITE, GRAY, YLW  = "FFFFFF", "F2F2F2", "FFFF00"

    thin = Side(style="thin", color="BFBFBF")
    BD   = Border(left=thin, right=thin, top=thin, bottom=thin)

    def hcell(ws, r, c, v, bg=NAVY, fg=WHITE, sz=10):
        cell = ws.cell(row=r, column=c, value=v)
        cell.font      = Font(bold=True, color=fg, size=sz, name="Arial")
        cell.fill      = PatternFill("solid", fgColor=bg)
        cell.alignment = Alignment(horizontal="center", vertical="center",
                                   wrap_text=True)
        cell.border    = BD
        return cell

    def dcell(ws, r, c, v="", bg=None, bold=False, color="000000",
              align="left", fmt=None):
        cell = ws.cell(row=r, column=c, value=v)
        cell.font      = Font(bold=bold, color=color, name="Arial", size=10)
        if bg:
            cell.fill  = PatternFill("solid", fgColor=bg)
        cell.alignment = Alignment(horizontal=align, vertical="center")
        if fmt:
            cell.number_format = fmt
        cell.border    = BD
        return cell

    def title_row(ws, row, text, cols=8):
        ws.merge_cells(f"A{row}:{get_column_letter(cols)}{row}")
        c = ws.cell(row=row, column=1, value=text)
        c.font      = Font(bold=True, size=13, color=WHITE, name="Arial")
        c.fill      = PatternFill("solid", fgColor=NAVY)
        c.alignment = Alignment(horizontal="center", vertical="center")
        ws.row_dimensions[row].height = 40

    # ────────────────────────────────────────────────────────────────────────
    # HOJA 1 – Curvas de Rendimiento y Variables de Mercado
    # ────────────────────────────────────────────────────────────────────────
    ws1 = wb.active
    ws1.title = "Tasas_y_Mercado"
    ws1.sheet_view.showGridLines = False

    title_row(ws1, 1, "TASAS DE MERCADO Y VARIABLES MACRO  |  PLANTILLA BLOOMBERG  |  MTDS 2026")
    ws1.row_dimensions[2].height = 35
    for j, h in enumerate(
        ["Categoría", "Variable / Instrumento", "Bloomberg Ticker",
         "Unidad", "Valor Actual", "Fecha", "Fórmula BDP", "Notas"], 1):
        hcell(ws1, 2, j, h, bg=BLUE)

    market_rows = [
        # ── Curva COP ──
        ("COP — Curva Interna", "TES COP 2Y",       "COGR2YR Index",    "%"),
        ("COP — Curva Interna", "TES COP 5Y",        "COGR5YR Index",    "%"),
        ("COP — Curva Interna", "TES COP 10Y",       "COGR10YR Index",   "%"),
        ("COP — Curva Interna", "TES COP 15Y",       "COGR15YR Index",   "%"),
        ("COP — Curva Interna", "TES COP 20Y",       "COGR20YR Index",   "%"),
        # ── Curva UVR ──
        ("UVR — Indexada",      "TES UVR 5Y (real)", "COUVR5Y Index",    "% real"),
        ("UVR — Indexada",      "TES UVR 10Y (real)","COUVR10Y Index",   "% real"),
        ("UVR — Indexada",      "TES UVR 15Y (real)","COUVR15Y Index",   "% real"),
        # ── USD ──
        ("USD — Externa",       "SOFR overnight",    "SOFR Index",       "%"),
        ("USD — Externa",       "US Treasury 5Y",    "GT5 Govt",         "%"),
        ("USD — Externa",       "US Treasury 10Y",   "GT10 Govt",        "%"),
        ("USD — Externa",       "US Treasury 30Y",   "GT30 Govt",        "%"),
        # ── EUR ──
        ("EUR — Externa",       "EURIBOR 3M",        "EUR003M Index",    "%"),
        ("EUR — Externa",       "Bund 5Y",           "GDBR5 Govt",       "%"),
        ("EUR — Externa",       "Bund 10Y",          "GDBR10 Govt",      "%"),
        # ── CHF ──
        ("CHF — Externa",       "SARON overnight",   "SRON Index",       "%"),
        ("CHF — Externa",       "Swiss Govt 5Y",     "GSWISS5 Govt",     "%"),
        ("CHF — Externa",       "Swiss Govt 10Y",    "GSWISS10 Govt",    "%"),
        # ── FX ──
        ("Tipos de Cambio",     "USD/COP spot",      "COP Curncy",       "COP"),
        ("Tipos de Cambio",     "EUR/COP spot",      "EURCOP Curncy",    "COP"),
        ("Tipos de Cambio",     "CHF/COP spot",      "CHFCOP Curncy",    "COP"),
        ("Tipos de Cambio",     "EUR/USD spot",      "EURUSD Curncy",    "USD"),
        ("Tipos de Cambio",     "CHF/USD spot",      "USDCHF Curncy",    "USD"),
        # ── Macro Colombia ──
        ("Macro Colombia",      "Inflación COP YoY", "COCPIYOY Index",   "%"),
        ("Macro Colombia",      "Expectativas inflac 12M","COINFEXP Index","  %"),
        ("Macro Colombia",      "UVR variación diaria","CUVR Index",     "%"),
        ("Macro Colombia",      "PIB Colombia YoY",  "COGDPYOY Index",   "%"),
        ("Macro Colombia",      "CDS Colombia 5Y",   "COLOM CDS USD SR 5Y","bps"),
        ("Macro Colombia",      "Spread EMBI Col",   "COLOM EMBI Index", "bps"),
        ("Macro Colombia",      "Ingresos Gob./PIB", "COFISCREV Index",  "% PIB"),
        ("Macro Colombia",      "Deuda/PIB",         "CODEBT Index",     "% PIB"),
    ]

    alt = False
    for row_idx, (cat, var, ticker, unit) in enumerate(market_rows, 3):
        bg = GRAY if alt else WHITE
        alt = not alt
        dcell(ws1, row_idx, 1, cat,    bg=bg, bold=True,  color=BLUE)
        dcell(ws1, row_idx, 2, var,    bg=bg)
        dcell(ws1, row_idx, 3, ticker, bg=bg, color="7030A0", bold=True)
        dcell(ws1, row_idx, 4, unit,   bg=bg, align="center")
        dcell(ws1, row_idx, 5, None,   bg=YLW)   # ← completar
        dcell(ws1, row_idx, 6, None,   bg=YLW)   # ← fecha
        dcell(ws1, row_idx, 7, f'=BDP("{ticker}","PX_LAST")', bg=GREEN)
        dcell(ws1, row_idx, 8, "", bg=bg)

    # Nota
    nr = len(market_rows) + 4
    ws1.merge_cells(f"A{nr}:H{nr}")
    c = ws1.cell(row=nr, column=1,
         value="▶  INSTRUCCIÓN: Celdas amarillas = ingresar manualmente desde Bloomberg. "
               "Celdas verdes = fórmulas =BDP() que calculan automáticamente. "
               "Para series históricas use: =BDH(C3,\"PX_LAST\",\"20200101\",TODAY())")
    c.font      = Font(bold=True, italic=True, color=BLUE, size=10, name="Arial")
    c.fill      = PatternFill("solid", fgColor=LBLUE)
    c.alignment = Alignment(horizontal="left", vertical="center", wrap_text=True)
    ws1.row_dimensions[nr].height = 30

    ws1.column_dimensions["A"].width = 20
    ws1.column_dimensions["B"].width = 28
    ws1.column_dimensions["C"].width = 28
    ws1.column_dimensions["D"].width = 10
    ws1.column_dimensions["E"].width = 14
    ws1.column_dimensions["F"].width = 14
    ws1.column_dimensions["G"].width = 32
    ws1.column_dimensions["H"].width = 30

    # ────────────────────────────────────────────────────────────────────────
    # HOJA 2 – Portafolio Actual (Stock de Deuda + Perfil Amortizaciones)
    # ────────────────────────────────────────────────────────────────────────
    ws2 = wb.create_sheet("Portafolio_Actual")
    ws2.sheet_view.showGridLines = False
    title_row(ws2, 1, "PORTAFOLIO DEUDA VIGENTE — DICIEMBRE 2025  |  MTDS 2026", cols=14)
    ws2.row_dimensions[2].height = 45

    ph2 = ["ID", "Mercado", "Moneda", "Tasa",
           "Saldo\n(COP Bn)", "Part.\n(%)",
           "Cupón/Tasa\n(%)", "TPV\n(años)", "TPR\n(años)",
           "% Vto\nAño 1", "Amort.\nAño 1", "Amort.\nAño 2",
           "Amort.\nAño 3", "Amort.\nAño 4-5"]

    for j, h in enumerate(ph2, 1):
        hcell(ws2, 2, j, h, bg=BLUE)

    for r_i, inst in enumerate(INSTRUMENTS, 3):
        bg_r = "E8F4FD" if inst[1] == "Deuda Interna" else GREEN
        mkt_c = NAVY if inst[1] == "Deuda Interna" else BLUE
        ref_w = REF_MFMP25[inst[0]]
        dcell(ws2, r_i, 1,  inst[0], bg=bg_r, bold=True, color="7030A0")
        dcell(ws2, r_i, 2,  inst[1], bg=bg_r, bold=True, color=mkt_c)
        dcell(ws2, r_i, 3,  inst[2], bg=bg_r, bold=True)
        dcell(ws2, r_i, 4,  inst[3], bg=bg_r)
        dcell(ws2, r_i, 5,  None, bg=YLW)   # saldo COP Bn
        dcell(ws2, r_i, 6,  f"{ref_w*100:.0f}%", bg=bg_r, align="center")
        for col in range(7, 15):
            dcell(ws2, r_i, col, None, bg=YLW)

    tot_r = len(INSTRUMENTS) + 3
    for j in range(1, 15):
        dcell(ws2, tot_r, j, "", bg=NAVY if j not in [5,6] else NAVY, bold=True, color=WHITE)
    dcell(ws2, tot_r, 1, "TOTAL", bg=NAVY, bold=True, color=WHITE)
    ws2.cell(row=tot_r, column=5).value = f"=SUM(E3:E{tot_r-1})"
    ws2.cell(row=tot_r, column=5).font  = Font(bold=True, color=WHITE, name="Arial")

    widths2 = [14, 18, 10, 12, 14, 10, 12, 10, 10, 10, 14, 14, 14, 14]
    for j, w in enumerate(widths2, 1):
        ws2.column_dimensions[get_column_letter(j)].width = w

    # ────────────────────────────────────────────────────────────────────────
    # HOJA 3 – Parámetros del Modelo (para calibración)
    # ────────────────────────────────────────────────────────────────────────
    ws3 = wb.create_sheet("Parametros_Modelo")
    ws3.sheet_view.showGridLines = False
    title_row(ws3, 1, "PARÁMETROS DE CALIBRACIÓN DEL MODELO  |  MTDS 2026", cols=5)
    ws3.row_dimensions[2].height = 30

    sections_p = [
        ("TASAS FIJAS (nueva emisión, %)",
         [("Tasa COP Fija",          "cop_fixed_rate",   "COGR10YR Index",      9.50),
          ("Tasa Real UVR",          "uvr_real_rate",    "COUVR10Y Index",      4.50),
          ("Inflación COP (UVR)",    "uvr_inflation",    "COCPIYOY Index",      5.00),
          ("Tasa USD Fija",          "usd_fixed_rate",   "GT10 Govt + spread",  6.00),
          ("Tasa EUR Fija",          "eur_fixed_rate",   "GDBR10 Govt + spread",4.00),
          ("Tasa CHF Fija",          "chf_fixed_rate",   "GSWISS10 + spread",   2.00)]),
        ("TASAS VARIABLES — ÍNDICE BASE (%)",
         [("SOFR base",              "sofr_base",        "SOFR Index",          4.50),
          ("Spread USD s/SOFR",      "usd_spread_sofr",  "OTC / Prospecto",     1.20),
          ("EURIBOR 3M base",        "euribor_base",     "EUR003M Index",       3.00),
          ("Spread EUR s/EURIBOR",   "eur_spread_eurib", "OTC / Prospecto",     0.90),
          ("SARON base",             "saron_base",       "SRON Index",          1.20),
          ("Spread CHF s/SARON",     "chf_spread_saron", "OTC / Prospecto",     0.60)]),
        ("VOLATILIDADES ANUALIZADAS (%)",
         [("Vol. TES COP",           "vol_cop_rate",     "Histórico 5Y COGR10YR",1.80),
          ("Vol. inflación COP",     "vol_uvr_inf",      "Histórico 5Y COCPIYOY",1.20),
          ("Vol. tasa USD",          "vol_usd_rate",     "Histórico 5Y GT10",   0.90),
          ("Vol. tasa EUR",          "vol_eur_rate",     "Histórico 5Y GDBR10", 0.70),
          ("Vol. tasa CHF",          "vol_chf_rate",     "Histórico 5Y GSWISS10",0.50),
          ("Vol. SOFR",              "vol_sofr",         "Histórico 5Y SOFR",   0.80),
          ("Vol. EURIBOR",           "vol_euribor",      "Histórico 5Y EUR003M", 0.65),
          ("Vol. SARON",             "vol_saron",        "Histórico 5Y SRON",   0.40)]),
        ("TIPOS DE CAMBIO",
         [("USD/COP Spot",           "usdcop_spot",      "COP Curncy",          4200),
          ("Drift anual USD/COP (%)", "usdcop_drift",    "Expectativa macro",   4.0),
          ("Vol anual USD/COP (%)",  "vol_usdcop",       "Histórico 5Y COP Curncy",9.0),
          ("EUR/COP Spot",           "eurcop_spot",      "EURCOP Curncy",       4620),
          ("Drift anual EUR/COP (%)", "eurcop_drift",    "Expectativa macro",   3.0),
          ("Vol anual EUR/COP (%)",  "vol_eurcop",       "Histórico 5Y EURCOP", 8.5),
          ("CHF/COP Spot",           "chfcop_spot",      "CHFCOP Curncy",       4850),
          ("Drift anual CHF/COP (%)", "chfcop_drift",    "Expectativa macro",   2.5),
          ("Vol anual CHF/COP (%)",  "vol_chfcop",       "Histórico 5Y CHFCOP", 7.5)]),
        ("MACRO / FISCAL",
         [("PIB Colombia (COP Bn)",  "gdp_cop_bn",       "COGDPNAC Index",      1998508.0),
          ("Deuda / PIB (%)",        "debt_pct_gdp",     "CODEBT Index",        55.0),
          ("Ingresos Gob. / PIB (%)","revenues_pct_gdp", "COFISCREV Index",     17.0),
          ("GFN (% PIB)",            "gfn_pct_gdp",      "MHCP Presupuesto",    6.5),
          ("Aversión al riesgo λ",   "risk_aversion",    "Calibrar [0.5 – 3.0]",1.5),
          ("N° escenarios MC",       "n_scenarios",      "Fijo",                1000),
          ("Horizonte (años)",       "horizon",          "Fijo",                   5)]),
    ]

    row3 = 3
    for sect_name, params_list in sections_p:
        ws3.merge_cells(f"A{row3}:E{row3}")
        c3 = ws3.cell(row=row3, column=1, value=sect_name)
        c3.font      = Font(bold=True, size=11, color=WHITE, name="Arial")
        c3.fill      = PatternFill("solid", fgColor=BLUE)
        c3.alignment = Alignment(horizontal="left", vertical="center")
        ws3.row_dimensions[row3].height = 22
        row3 += 1
        for j, h in enumerate(["Parámetro", "ID Variable", "Fuente Bloomberg",
                                "Valor Calibrado", "Notas"], 1):
            hcell(ws3, row3, j, h, bg=LBLUE, fg=NAVY, sz=9)
        row3 += 1
        for pname, pid, ticker, val in params_list:
            bg_r = GRAY if row3 % 2 == 0 else WHITE
            dcell(ws3, row3, 1, pname,  bg=bg_r)
            dcell(ws3, row3, 2, pid,    bg=bg_r, color="7030A0", bold=True)
            dcell(ws3, row3, 3, ticker, bg=bg_r, color="0563C1")
            dcell(ws3, row3, 4, val,    bg=YLW,  bold=True, align="center")
            dcell(ws3, row3, 5, "",     bg=bg_r)
            row3 += 1
        row3 += 1

    ws3.column_dimensions["A"].width = 30
    ws3.column_dimensions["B"].width = 22
    ws3.column_dimensions["C"].width = 35
    ws3.column_dimensions["D"].width = 18
    ws3.column_dimensions["E"].width = 30

    # ────────────────────────────────────────────────────────────────────────
    # HOJA 4 – Escenarios de Estrés (paso 4 BM-FMI)
    # ────────────────────────────────────────────────────────────────────────
    ws4 = wb.create_sheet("Escenarios_Estres")
    ws4.sheet_view.showGridLines = False
    title_row(ws4, 1, "ESCENARIOS DE ESTRÉS DETERMINISTAS  |  BM-FMI Paso 4", cols=5)
    ws4.row_dimensions[2].height = 35

    stress_def = [
        ("Base",     "Proyecciones macro de referencia",     "0 pbs",  "0%"),
        ("Tasa+200", "Shock de tasas de interés (+200 pbs)", "+200 pbs","0%"),
        ("Depr. 30%","Shock cambiario (depreciación 30% COP)","0 pbs","−30%"),
        ("Combinado","Shock combinado (tasas + cambiario)",   "+200 pbs","−30%"),
    ]

    for j, h in enumerate(["Escenario", "Descripción", "Shock Tasa",
                             "Shock FX (COP)", "Fundamento BM-FMI"], 1):
        hcell(ws4, 2, j, h, bg=BLUE)

    fundamentos = [
        "Marco macroeconómico base (paso 4)",
        "Apéndice III — Riesgo de tasas de interés",
        "Apéndice III — Riesgo cambiario",
        "ASD — prueba de estrés combinada",
    ]
    for r_i, (esc, desc, st, sfx) in enumerate(stress_def, 3):
        bg_r = GRAY if r_i % 2 == 0 else WHITE
        dcell(ws4, r_i, 1, esc,  bg=bg_r, bold=True, color=NAVY)
        dcell(ws4, r_i, 2, desc, bg=bg_r)
        dcell(ws4, r_i, 3, st,   bg=bg_r, align="center")
        dcell(ws4, r_i, 4, sfx,  bg=bg_r, align="center")
        dcell(ws4, r_i, 5, fundamentos[r_i-3], bg=bg_r)

    for j in range(1, 6):
        ws4.column_dimensions[get_column_letter(j)].width = [18, 45, 14, 16, 38][j-1]


# ══════════════════════════════════════════════════════════════════════════════
# 10. GUARDAR RESULTADOS  (Excel BM-FMI completo)
# ══════════════════════════════════════════════════════════════════════════════
def save_results(w: np.ndarray, mc_metrics: dict, stress: dict,
                 port: dict, frontier: pd.DataFrame, path: str, df_scenarios: pd.DataFrame = None, p_dict: dict = None):

    wb = Workbook()
    NAVY, BLUE, LBLUE = "1F3864", "2E74B5", "D6E4F0"
    GREEN, GRAY = "E2EFDA", "F2F2F2"
    WHITE, YLW  = "FFFFFF", "FFF2CC"
    RED         = "C00000"

    thin = Side(style="thin", color="BFBFBF")
    BD   = Border(left=thin, right=thin, top=thin, bottom=thin)

    def hc(ws, r, c, v, bg=NAVY, fg=WHITE, sz=11):
        cell = ws.cell(row=r, column=c, value=v)
        cell.font      = Font(bold=True, color=fg, size=sz, name="Arial")
        cell.fill      = PatternFill("solid", fgColor=bg)
        cell.alignment = Alignment(horizontal="center", vertical="center",
                                   wrap_text=True)
        cell.border    = BD
        return cell

    def dc(ws, r, c, v="", bg=None, bold=False, color="000000",
           align="left", sz=10):
        cell = ws.cell(row=r, column=c, value=v)
        cell.font      = Font(bold=bold, color=color, name="Arial", size=sz)
        if bg:
            cell.fill  = PatternFill("solid", fgColor=bg)
        cell.alignment = Alignment(horizontal=align, vertical="center")
        cell.border    = BD
        return cell

    def title_row(ws, row, text, cols=6):
        ws.merge_cells(f"A{row}:{get_column_letter(cols)}{row}")
        c = ws.cell(row=row, column=1, value=text)
        c.font      = Font(bold=True, size=13, color=WHITE, name="Arial")
        c.fill      = PatternFill("solid", fgColor=NAVY)
        c.alignment = Alignment(horizontal="center", vertical="center")
        ws.row_dimensions[row].height = 40

    # ── Hoja 1: Estrategia MFMP 2026 (formato solicitado) ────────────────
    ws1 = wb.active
    ws1.title = "MTDS_2026"
    ws1.sheet_view.showGridLines = False
    title_row(ws1, 1, "ESTRATEGIA GESTIÓN DE DEUDA A MEDIANO PLAZO — MFMP 2026", 6)

    for j, h in enumerate(["Mercado", "Moneda", "Tasa",
                             "MFMP 26 (%)", "MFMP 25 (ref.)", "Δ vs 2025"], 1):
        hc(ws1, 2, j, h, bg=BLUE)
    ws1.row_dimensions[2].height = 30

    prev_mkt = ""
    for i, inst in enumerate(INSTRUMENTS):
        r_i = i + 3
        pct26 = round(w[i] * 100, 1)
        pct25 = round(REF_MFMP25[inst[0]] * 100, 1)
        delta = round(pct26 - pct25, 1)
        bg_r  = "E8F4FD" if inst[1] == "Deuda Interna" else GREEN

        if inst[1] != prev_mkt:
            mkt_bg = NAVY if inst[1] == "Deuda Interna" else BLUE
            dc(ws1, r_i, 1, inst[1], bg=mkt_bg, bold=True, color=WHITE, align="center")
            prev_mkt = inst[1]
        else:
            dc(ws1, r_i, 1, "", bg=bg_r)

        dc(ws1, r_i, 2, inst[2], bg=bg_r, bold=True)
        dc(ws1, r_i, 3, inst[3], bg=bg_r)
        dc(ws1, r_i, 4, f"{pct26:.1f}%", bg=bg_r, bold=True, color=NAVY, align="center")
        dc(ws1, r_i, 5, f"{pct25:.1f}%" if pct25>0 else "—", bg=GRAY, align="center")

        d_col = RED if delta < 0 else ("1F3864" if delta > 0 else "7F7F7F")
        dc(ws1, r_i, 6, f"{'+' if delta>0 else ''}{delta:.1f}pp",
           bg=bg_r, color=d_col, align="center", bold=True)

    tot = len(INSTRUMENTS) + 3
    for j in range(1, 7):
        dc(ws1, tot, j, "", bg=NAVY, bold=True, color=WHITE)
    ws1.cell(row=tot, column=1).value = "TOTAL"
    ws1.cell(row=tot, column=4).value = "100.0%"
    ws1.cell(row=tot, column=5).value = "100.0%"
    for j in [1, 4, 5]:
        ws1.cell(row=tot, column=j).font = Font(bold=True, color=WHITE, name="Arial")

    for j, w_ in enumerate([20, 10, 12, 14, 14, 12], 1):
        ws1.column_dimensions[get_column_letter(j)].width = w_

    # ── Hoja 2: Métricas BM-FMI (indicadores Apéndice III) ───────────────
    ws2 = wb.create_sheet("Metricas_BMFMI")
    ws2.sheet_view.showGridLines = False
    title_row(ws2, 1, "MÉTRICAS BM-FMI  |  Apéndice III  —  Costos, Riesgos y Estadísticas de Cartera", 3)

    sections_m = [
        ("INDICADORES DE COSTO (escenario base)",
         [("Pago intereses / PIB (%)",      f"{stress['base']['int_pct_gdp']:.3f}%",
           "Principal métrica BM-FMI de costo"),
          ("Pago intereses / Ingresos (%)", f"{stress['base']['int_pct_rev']:.3f}%",
           "Métrica de carga fiscal BM-FMI"),
          ("Tasa promedio ponderada (%)",   f"{stress['base']['tasa_ponderada']:.3f}%",
           "Costo efectivo del portafolio"),]),
        ("RIESGO DE TASAS DE INTERÉS (Apéndice III)",
         [("TPR — Tiempo Prom. Refijación (años)", f"{port['TPR_años']:.2f}",
           "Menor TPR = mayor exposición a tasas"),
          ("% Deuda tasa variable",         f"{port['pct_variable']:.1f}%",
           "Refija en < 1 año"),
          ("Δ int/PIB — shock +200 pbs",   f"+{stress['tasa+200']['delta_pct_gdp']:.3f}%",
           "Riesgo tasa de interés BM-FMI"),]),
        ("RIESGO DE REFINANCIAMIENTO (Apéndice III)",
         [("TPV — Tiempo Prom. Vencimiento (años)", f"{port['TPV_años']:.2f}",
           "Mayor TPV = menor riesgo refinanciamiento"),
          ("% Deuda vence en año 1",        f"{port['pct_refijacion_año1']:.1f}%",
           "Indicador de riesgo de renovación"),
          ("Amortizaciones año 1 (% stock)", f"{list(port['amortizacion'].values())[0]:.2f}%",
           "Perfil de amortización BM-FMI"),]),
        ("RIESGO CAMBIARIO (Apéndice III)",
         [("% Deuda en moneda extranjera",  f"{port['pct_FX']:.1f}%",
           "Principal indicador riesgo FX"),
          ("% Deuda en COP + UVR",          f"{port['pct_COP_UVR']:.1f}%",
           "Cobertura natural"),
          ("Δ int/PIB — depr. 30% COP",    f"+{stress['depr30']['delta_pct_gdp']:.3f}%",
           "Riesgo cambiario BM-FMI"),]),
        ("ESCENARIO COMBINADO (stress test BM-FMI)",
         [("int/PIB — escenario base",      f"{stress['base']['int_pct_gdp']:.3f}%", ""),
          ("int/PIB — shock combinado",     f"{stress['combinado']['int_pct_gdp']:.3f}%",
           "Tasas +200 pbs + Depr. 30%"),
          ("Δ vs. base (pp de PIB)",        f"+{stress['combinado']['delta_pct_gdp']:.3f}%",
           "Capacidad de absorción de shocks"),]),
        ("ANÁLISIS ESTOCÁSTICO Y SELECCIÓN DE CANASTA",
         [("Función Objetivo Optimizador", "E[Costo] + λ × σ[Costo]",
           "Criterio de selección de la combinación óptima"),
          ("Aversión al Riesgo (λ)", f"{p_dict.get('risk_aversion', 1.5) if p_dict else 1.5}",
           "Parámetro de aversión en la optimización"),
          ("E[int/PIB] — Costo Esperado", f"{mc_metrics['cost_ev']:.3f}%",
           "Promedio sobre 1,000 trayectorias"),
          ("σ[int/PIB] — Riesgo (Std Dev)",  f"{mc_metrics['cost_std']:.3f}%",
           "Dispersión del costo"),
          ("Valor Función Objetivo", f"{(mc_metrics['cost_ev'] + (p_dict.get('risk_aversion', 1.5) if p_dict else 1.5) * mc_metrics['cost_std']):.3f}%",
           "Métrica de riesgo total minimizada"),
          ("CVaR 95% (% PIB)",                  f"{mc_metrics['cvar95']:.3f}%",
           "Expected shortfall escenarios adversos"),]),
    ]

    r2 = 3
    for sect_n, rows_m in sections_m:
        ws2.merge_cells(f"A{r2}:C{r2}")
        c2 = ws2.cell(row=r2, column=1, value=sect_n)
        c2.font      = Font(bold=True, size=11, color=WHITE, name="Arial")
        c2.fill      = PatternFill("solid", fgColor=BLUE)
        c2.alignment = Alignment(horizontal="left", vertical="center")
        ws2.row_dimensions[r2].height = 22
        r2 += 1
        for metric, val, note in rows_m:
            bg_r = GRAY if r2 % 2 == 0 else "FFFFFF"
            dc(ws2, r2, 1, metric, bg=bg_r, bold=True)
            dc(ws2, r2, 2, val,    bg=bg_r, bold=True, color=NAVY, align="center",sz=11)
            dc(ws2, r2, 3, note,   bg=bg_r)
            r2 += 1
        r2 += 1

    ws2.column_dimensions["A"].width = 40
    ws2.column_dimensions["B"].width = 22
    ws2.column_dimensions["C"].width = 48

    # ── Hoja 3: Frontera Eficiente ────────────────────────────────────────
    ws3 = wb.create_sheet("Frontera_Eficiente")
    ws3.sheet_view.showGridLines = False
    title_row(ws3, 1, "FRONTERA EFICIENTE COSTO-RIESGO  |  BM-FMI Paso 6  |  40 Puntos (λ Variable)",
              cols=len(frontier.columns))
    for j, h in enumerate(frontier.columns, 1):
        hc(ws3, 2, j, h, bg=BLUE, sz=9)
    for r_i, row_f in enumerate(frontier.itertuples(index=False), 3):
        bg_r = GRAY if r_i % 2 == 0 else "FFFFFF"
        for j, val in enumerate(row_f, 1):
            dc(ws3, r_i, j, val, bg=bg_r, align="center")
    for j in range(1, len(frontier.columns)+1):
        ws3.column_dimensions[get_column_letter(j)].width = 13

    # ── Hoja 4: Distribución Escenarios ──────────────────────────────────
    ws4 = wb.create_sheet("Distribucion_MC")
    ws4.sheet_view.showGridLines = False
    title_row(ws4, 1, "DISTRIBUCIÓN DE COSTOS  |  1,000 Escenarios Monte Carlo (% PIB)", 2)
    hc(ws4, 2, 1, "Escenario #", bg=BLUE)
    hc(ws4, 2, 2, "Int/PIB (% prom. 5 años)", bg=BLUE)
    dist = mc_metrics["dist"]
    for r_i, val in enumerate(dist, 3):
        bg_r = GRAY if r_i % 2 == 0 else "FFFFFF"
        dc(ws4, r_i, 1, r_i - 2, bg=bg_r, align="center")
        dc(ws4, r_i, 2, round(float(val), 5), bg=bg_r, align="center")
    ws4.column_dimensions["A"].width = 14
    ws4.column_dimensions["B"].width = 26

    # ── Hoja 5: 1,000 Escenarios Completos ────────────────────────────────
    if df_scenarios is not None:
        ws5 = wb.create_sheet("Escenarios_1000")
        ws5.sheet_view.showGridLines = False
        title_row(ws5, 1, "1,000 ESCENARIOS MONTE CARLO Y MÉTRICAS CALCULADAS", cols=len(df_scenarios.columns))
        for j, col_name in enumerate(df_scenarios.columns, 1):
            hc(ws5, 2, j, col_name, bg=BLUE, sz=9)
            ws5.column_dimensions[get_column_letter(j)].width = 16
        for r_i, row_data in enumerate(df_scenarios.itertuples(index=False), 3):
            bg_r = GRAY if r_i % 2 == 0 else "FFFFFF"
            for j, val in enumerate(row_data, 1):
                dc(ws5, r_i, j, val, bg=bg_r, align="center")

    wb.save(path)

class MTDSPDF(FPDF):
    def header(self):
        self.set_font("Arial", "B", 12)
        self.cell(0, 10, "REPORTE EJECUTIVO MTDS 2026 - MHCP", border=False, ln=1, align="C")
        self.set_font("Arial", "", 9)
        self.cell(0, 5, f"Fecha de generación: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}", ln=1, align="C")
        self.ln(10)

    def chapter_title(self, title):
        self.set_font("Arial", "B", 11)
        self.set_fill_color(31, 56, 100) # Navy MHCP
        self.set_text_color(255, 255, 255)
        self.cell(0, 8, title, ln=1, align="L", fill=True)
        self.set_text_color(0, 0, 0)
        self.ln(4)

    def add_terminal_text(self, text):
        self.set_font("Courier", "", 8)
        # Reemplazar caracteres que rompen el encoding latin-1
        clean_text = text.replace("—", "-").replace("–", "-")
        clean_text = clean_text.replace("┌", "+").replace("┐", "+")
        clean_text = clean_text.replace("└", "+").replace("┘", "+")
        clean_text = clean_text.replace("│", "|").replace("─", "-")
        clean_text = clean_text.replace("⚠", "!!!").replace("✔", "OK")
        clean_text = clean_text.replace("ⓘ", "i")
        
        # El ignore evita que el script se detenga si aparece otro caracter extraño
        clean_text = clean_text.encode('latin-1', 'ignore').decode('latin-1')
        
        self.multi_cell(0, 5, clean_text)
        self.ln(5)
# ══════════════════════════════════════════════════════════════════════════════
# 10.5 FORECASTING (YAHOO FINANCE + ARIMA)
# ══════════════════════════════════════════════════════════════════════════════
def evaluate_models_and_forecast(ts, steps=1260, lags=10):
    """
    Entrena diferentes modelos de machine learning (y AutoARIMA),
    los evalúa con un split 80/20 out-of-sample, selecciona el mejor,
    y genera el pronóstico hacia el futuro con ruido aleatorio.
    """
    if len(ts.shape) > 1:
        ts = ts.ravel()
    diff_ts = np.diff(ts)
    X, y = [], []
    for i in range(lags, len(diff_ts)):
        X.append(diff_ts[i-lags:i])
        y.append(diff_ts[i])
    X, y = np.array(X), np.array(y)

    split_idx = int(len(ts) * 0.8)
    ts_train, ts_test = ts[:split_idx], ts[split_idx:]

    ml_split = split_idx - lags - 1
    if ml_split < 0: ml_split = int(len(X)*0.8)
    X_train, y_train = X[:ml_split], y[:ml_split]
    X_test, y_test = X[ml_split:], y[ml_split:]

    models = {
        "RandomForest": RandomForestRegressor(n_estimators=50, random_state=42),
        "GradientBoosting": GradientBoostingRegressor(n_estimators=50, random_state=42),
        "LinearRegression": LinearRegression()
    }

    best_name = None
    best_rmse = np.inf
    best_mae = np.inf
    best_model = None

    # 1. Evaluar modelos ML (predeciendo diferencias)
    for name, m in models.items():
        try:
            m.fit(X_train, y_train)
            preds_diff = m.predict(X_test)
            reconstructed = [ts_train[-1]]
            for d in preds_diff:
                reconstructed.append(reconstructed[-1] + d)
            rmse = root_mean_squared_error(ts_test[:len(preds_diff)], reconstructed[1:len(preds_diff)+1])
            if rmse < best_rmse:
                best_rmse = rmse
                best_mae = mean_absolute_error(ts_test[:len(preds_diff)], reconstructed[1:len(preds_diff)+1])
                best_name = name
                best_model = m
        except Exception:
            pass

    # 2. Evaluar AutoARIMA
    try:
        arima_model = auto_arima(ts_train, seasonal=False, suppress_warnings=True, trend='c')
        arima_preds = arima_model.predict(n_periods=len(ts_test))
        arima_rmse = root_mean_squared_error(ts_test, arima_preds)
        if arima_rmse < best_rmse:
            best_rmse = arima_rmse
            best_mae = mean_absolute_error(ts_test, arima_preds)
            best_name = "AutoARIMA"
    except Exception:
        pass

    # 3. Generar pronóstico real a futuro (agregando ruido para volatilidad)
    if best_name == "AutoARIMA":
        model = auto_arima(ts, seasonal=False, suppress_warnings=True, trend='c')
        f_mean = model.predict(n_periods=steps)
        resids = model.resid()
        noise = np.random.choice(resids, size=steps)
        f_simulated = f_mean + noise

        in_sample = model.predict_in_sample()
        rmse_in = root_mean_squared_error(ts[1:], in_sample[1:])
        mae_in = mean_absolute_error(ts[1:], in_sample[1:])
        return np.array(f_simulated), best_name, rmse_in, mae_in
    else:
        best_model.fit(X, y)
        fitted = best_model.predict(X)
        resids = y - fitted

        forecast_diffs = []
        curr_lags = diff_ts[-lags:].tolist()
        noise_std = np.std(resids)

        for _ in range(steps):
            pred_diff = best_model.predict([curr_lags])[0]
            pred_diff += np.random.normal(0, noise_std)
            forecast_diffs.append(pred_diff)
            curr_lags.append(pred_diff)
            curr_lags.pop(0)

        forecast = [ts[-1]]
        for d in forecast_diffs:
            forecast.append(forecast[-1] + d)

        rmse_in = root_mean_squared_error(diff_ts[lags:], fitted) # Proxy in-sample differences
        mae_in = mean_absolute_error(diff_ts[lags:], fitted)
        return np.array(forecast[1:]), best_name, rmse_in, mae_in


def apply_forecasts(p: dict) -> dict:
    """
    Descarga histórico 5Y de USD/COP, EUR/USD, CHF/USD, y US Treasury 10Y.
    Evalúa algoritmos Machine Learning para proyectar trayectorias realistas (no planas).
    """
    print("\n[  *  ] Conectando a Yahoo Finance para extraer histórico 5Y...")
    tickers = ['COP=X', 'EURUSD=X', 'CHFUSD=X', '^TNX']
    data = yf.download(tickers, period="5y", progress=False)["Close"]

    # Calcular cruces directos contra COP
    data["USDCOP"] = data["COP=X"]
    data["EURCOP"] = data["EURUSD=X"] * data["USDCOP"]
    data["CHFCOP"] = data["CHFUSD=X"] * data["USDCOP"]
    data["UST10Y"] = data["^TNX"]

    df = data[["USDCOP", "EURCOP", "CHFCOP", "UST10Y"]].dropna()

    forecasts = {}
    metrics = []

    print("        Evaluando modelos Machine Learning / ARIMA para el mejor pronóstico...")
    plt.figure(figsize=(15, 10))
    for i, col in enumerate(["USDCOP", "EURCOP", "CHFCOP", "UST10Y"]):
        ts = df[col].values

        try:
            # Seleccionar y proyectar 5 años (1260 días)
            f_simulated, best_model_name, rmse, mae = evaluate_models_and_forecast(ts, steps=1260)

            metrics.append({
                "Variable": col, "Modelo": best_model_name,
                "RMSE": rmse, "MAE": mae
            })

            # Graficar
            plt.subplot(2, 2, i+1)
            plt.plot(ts, label="Histórico", color="navy")
            plt.plot(range(len(ts), len(ts)+1260), f_simulated, label=f"Proyección ({best_model_name})", color="red", linestyle="--")
            plt.title(f"{col} - Mejor Modelo: {best_model_name}")
            plt.legend()

            # Actualizar drift a 5 años en los parámetros
            if col == "USDCOP":
                drift_pct = (np.log(f_simulated[-1] / ts[-1]) / 5.0) * 100
                p["usdcop_drift"] = drift_pct
                p["usdcop_spot"] = ts[-1]
            elif col == "EURCOP":
                drift_pct = (np.log(f_simulated[-1] / ts[-1]) / 5.0) * 100
                p["eurcop_drift"] = drift_pct
                p["eurcop_spot"] = ts[-1]
            elif col == "CHFCOP":
                drift_pct = (np.log(f_simulated[-1] / ts[-1]) / 5.0) * 100
                p["chfcop_drift"] = drift_pct
                p["chfcop_spot"] = ts[-1]
            elif col == "UST10Y":
                p["usd_fixed_rate"] = f_simulated[-1]

        except Exception as e:
            print(f"        Error proyectando {col}: {e}")

    plt.tight_layout()
    plot_path = "Forecasts_YahooFinance.png"
    plt.savefig(plot_path)
    plt.close()

    # Crear log para PDF
    log = "\n── PRONÓSTICOS Y SELECCIÓN DE MODELO DE MACHINE LEARNING ──\n"
    for m in metrics:
        log += f"  {m['Variable']:<10} Modelo: {m['Modelo']:<17} RMSE: {m['RMSE']:>10.4f}   MAE: {m['MAE']:>10.4f}\n"
    log += f"  Drift proyectado USDCOP: {p['usdcop_drift']:.2f}%\n"
    log += f"  Drift proyectado EURCOP: {p['eurcop_drift']:.2f}%\n"
    log += f"  Drift proyectado CHFCOP: {p['chfcop_drift']:.2f}%\n"
    log += f"  Tasa USD Fija base proy: {p['usd_fixed_rate']:.2f}%\n"
    log += f"  Gráfico guardado en: {plot_path}\n"

    return {"p": p, "log": log, "plot": plot_path}


# ══════════════════════════════════════════════════════════════════════════════
# 11. MAIN
# ══════════════════════════════════════════════════════════════════════════════
def main():
    print("=" * 70)
    print("  HERRAMIENTA MTDS 2026  —  Ministerio de Hacienda y Crédito Público")
    print("  Metodología BM-FMI (2018)  |  Monte Carlo 1,000 esc.  |  SLSQP")
    print("=" * 70)

    # ── [0a] Oracle: deuda externa real ───────────────────────────────────
    print(f"\n[0a/6]  Leyendo Oracle: {os.path.basename(ORACLE_PATH)}")
    oracle = load_from_oracle(ORACLE_PATH)
    for msg in oracle["log"]:
        print(f"        {msg}")

    # ── [0b] Perfil de Vencimientos ────────────────────────────────────────
    print(f"\n[0b/6]  Leyendo Perfil de Vencimientos: {os.path.basename(PERFIL_PATH)}")
    perfil = load_from_perfil(PERFIL_PATH, oracle)

    

    for msg in perfil["log"]:
        print(f"        {msg}")

    # ── [0c] Plantilla Bloomberg ───────────────────────────────────────────
    print(f"\n[0c/6]  Leyendo Plantilla Bloomberg: {os.path.basename(TEMPLATE_PATH)}")
    tpl = load_from_template(TEMPLATE_PATH)
    for msg in tpl["log"]:
        print(f"        {msg}")

    # ── [0d] YAHOO FINANCE FORECASTS ───────────────────────────────────────
    # Prioridad: Oracle (datos reales) > Bloomberg template > PARAMS default
    p = tpl["params"]

    forecast_results = apply_forecasts(p)
    p = forecast_results["p"]
    print(forecast_results["log"])

    n_scenarios = int(p.pop("n_scenarios", 1000))
    horizon     = int(p.pop("horizon", 5))
    lam         = float(p.pop("risk_aversion", 1.5))

    # Sobrescribir tasas/spreads con datos reales de Oracle
    if oracle["ok"]:
        oracle_rates = oracle["rates"]
        # Tasas fijas reales (tasa_wp = tasa nominal anual ponderada por saldo)
        if "DE_USD_F" in oracle_rates:
            p["usd_fixed_rate"] = oracle_rates["DE_USD_F"]["tasa_wp"]
        if "DE_EUR_F" in oracle_rates:
            p["eur_fixed_rate"] = oracle_rates["DE_EUR_F"]["tasa_wp"]
        if "DE_CHF_F" in oracle_rates:
            p["chf_fixed_rate"] = oracle_rates["DE_CHF_F"]["tasa_wp"]
        # Spreads variables reales (margen_valor_wp sobre índice)
        if "DE_USD_V" in oracle_rates:
            p["usd_spread_sofr"] = oracle_rates["DE_USD_V"]["tasa_wp"]
        if "DE_EUR_V" in oracle_rates:
            p["eur_spread_eurib"] = oracle_rates["DE_EUR_V"]["tasa_wp"]
        if "DE_CHF_V" in oracle_rates:
            p["chf_spread_saron"] = oracle_rates["DE_CHF_V"]["tasa_wp"]
        # COP externo como proxy tasa TES COP si disponible
        if "DI_COP_EXT" in oracle_rates and oracle_rates["DI_COP_EXT"]["tasa_wp"] > 0:
            p["cop_fixed_rate"] = max(p["cop_fixed_rate"],
                                      oracle_rates["DI_COP_EXT"]["tasa_wp"])

    print(f"\n       Parámetros activos (tasas/spreads desde Oracle + Bloomberg):")
    key_show = [
        ("cop_fixed_rate",   "TES COP (%)"),
        ("uvr_real_rate",    "TES UVR real (%)"),
        ("usd_fixed_rate",   "USD Fija WP (%)"),
        ("eur_fixed_rate",   "EUR Fija WP (%)"),
        ("chf_fixed_rate",   "CHF Fija WP (%)"),
        ("usd_spread_sofr",  "Spread USD/SOFR (%)"),
        ("eur_spread_eurib", "Spread EUR/EURIBOR (%)"),
        ("chf_spread_saron", "Spread CHF/SARON (%)"),
        ("sofr_base",        "SOFR base (%)"),
        ("euribor_base",     "EURIBOR 3M (%)"),
        ("saron_base",       "SARON (%)"),
        ("usdcop_spot",      "USD/COP spot"),
        ("debt_pct_gdp",     "Deuda/PIB (%)"),
        ("revenues_pct_gdp", "Ingresos/PIB (%)"),
    ]
    for key, label in key_show:
        val = p.get(key, "—")
        src = " [Oracle]" if key in ("usd_fixed_rate","eur_fixed_rate","chf_fixed_rate",
                                      "usd_spread_sofr","eur_spread_eurib","chf_spread_saron") else ""
        print(f"         {label:<28} {val}{src}")

    # ── Construir portfolio dict fusionando Oracle + Perfil ───────────────
    # TPV desde fuentes reales
    portfolio = tpl["portfolio"].copy()   # datos Bloomberg como base
    if perfil["ok"]:
        for inst_id, tpv_val in perfil["tpv"].items():
            if inst_id not in portfolio:
                portfolio[inst_id] = {}
            portfolio[inst_id]["tpv_anos"] = tpv_val
            portfolio[inst_id]["pct_vto_1"] = perfil["pct_amort_yr1"].get(inst_id, None)

    # ── Pesos de referencia: composición actual del portafolio ────────────
    # Construimos ref_weights desde Oracle (externo) + lineamiento interno
    if oracle["ok"] and oracle["oracle_weights"]:
        # Externo: proporciones del Oracle dentro del 40 % externo
        # Interno: 60 % dividido 60/40 COP/UVR (lineamiento actual)
        ext_total = 0.40   # lineamiento nuevo
        int_total = 0.60
        int_cop   = int_total * 0.70   # ~70% del interno en COP
        int_uvr   = int_total * 0.30   # ~30% del interno en UVR
        ow = oracle["oracle_weights"]
        ref_w = np.array([
            int_cop,                              # DI_COP_F
            int_uvr,                              # DI_UVR_F
            ow.get("DE_USD_F", 0.606) * ext_total,# DE_USD_F
            ow.get("DE_EUR_F", 0.126) * ext_total,# DE_EUR_F
            ow.get("DE_EUR_V", 0.027) * ext_total,# DE_EUR_V
            ow.get("DE_USD_V", 0.066) * ext_total,# DE_USD_V
            ow.get("DE_CHF_F", 0.158) * ext_total,# DE_CHF_F
            ow.get("DE_CHF_V", 0.000) * ext_total,# DE_CHF_V
        ])
        ref_w = ref_w / ref_w.sum()   # normalizar
        print(f"\n       Pesos de referencia (60% interno, 40% externo Oracle):")
    else:
        ref_w = tpl["ref_weights"]
        print(f"\n       Pesos de referencia (desde plantilla Bloomberg):")

    prev_m = ""
    for i, inst in enumerate(INSTRUMENTS):
        m_label = inst[1] if inst[1] != prev_m else ""
        print(f"         {m_label:<18} {inst[2]:<5} {inst[3]:<10} {ref_w[i]*100:>6.1f}%")
        prev_m = inst[1]

    # ── [1] Generar / actualizar plantilla Bloomberg ───────────────────────
    print("\n[1/6]  Generando plantilla Bloomberg (5 hojas) …")
    tmpl_out = r"MTDS_Bloomberg_Template.xlsx"
    build_bloomberg_template(tmpl_out)
    print(f"       ✔  {tmpl_out}")

    # ── [2] Escenarios de estrés deterministas (BM-FMI Apéndice III) ──────
    print("\n[2/6]  Calculando escenarios de estrés BM-FMI …")
    stres_ref = stress_analysis(ref_w, p)
    print(f"       Portafolio referencia — Base: "
          f"{stres_ref['base']['int_pct_gdp']:.3f}% PIB  |  "
          f"Combinado: {stres_ref['combinado']['int_pct_gdp']:.3f}% PIB")

    # ── [3] Monte Carlo ────────────────────────────────────────────────────
    print(f"\n[3/6]  Generando {n_scenarios:,} escenarios MC ({horizon} años) …")
    gen  = ScenarioGenerator(p, n=n_scenarios, T=horizon)
    scen = gen.generate()
    print("       ✔  Tasas + FX simulados (11 factores correlacionados)")

    print("\n       Guardando escenarios en base de datos SQLite (MTDS_Escenarios.db) …")
    import sqlite3
    rates = scen["rates"] # shape: [n, T, 8]
    fx = scen["fx"] # shape: [n, T, 3]
    records = []

    # rates order: COP Fija, UVR Infl, USD Fija, EUR Fija, CHF Fija, SOFR, EURIBOR, SARON
    # fx order: USD/COP, EUR/COP, CHF/COP
    for i in range(n_scenarios):
        for t in range(horizon):
            records.append({
                "Escenario": i + 1,
                "Año": 2026 + t,
                "Tasa_COP_Fija": rates[i, t, 0],
                "Inflacion_UVR": rates[i, t, 1],
                "Tasa_USD_Fija": rates[i, t, 2],
                "Tasa_EUR_Fija": rates[i, t, 3],
                "Tasa_CHF_Fija": rates[i, t, 4],
                "SOFR": rates[i, t, 5],
                "EURIBOR": rates[i, t, 6],
                "SARON": rates[i, t, 7],
                "USD_COP": fx[i, t, 0],
                "EUR_COP": fx[i, t, 1],
                "CHF_COP": fx[i, t, 2],
            })

    df_scenarios = pd.DataFrame(records)
    conn = sqlite3.connect("MTDS_Escenarios.db")
    df_scenarios.to_sql("escenarios", conn, if_exists="replace", index=False)
    conn.close()
    print("       ✔  Base de datos guardada: MTDS_Escenarios.db")

    # ── [4] Estrategias Aleatorias y Alternativas ──────────────────────────
    print(f"\n[4/6]  Evaluando 1,000 Estrategias y Alternativas Int/Ext …")
    calc = CostRiskCalc(scen, p)

    # 1. 1,000 Estrategias Aleatorias
    rand_strats = []
    for i in range(1000):
        w_rand = np.random.dirichlet(np.ones(N_INST))
        m_rand = calc.metrics(w_rand)
        rand_strats.append({
            "Estrategia_ID": i + 1,
            "Costo_Esp": m_rand["cost_ev"],
            "Riesgo_Std": m_rand["cost_std"],
            "CVaR_95": m_rand["cvar95"],
            "w_DI_COP_F": w_rand[0], "w_DI_UVR_F": w_rand[1],
            "w_DE_USD_F": w_rand[2], "w_DE_EUR_F": w_rand[3],
            "w_DE_EUR_V": w_rand[4], "w_DE_USD_V": w_rand[5],
            "w_DE_CHF_F": w_rand[6], "w_DE_CHF_V": w_rand[7]
        })
    df_1000_strats = pd.DataFrame(rand_strats)

    # 2. Alternativas Int/Ext (50/50, 60/40, 70/30, 80/20)
    alts = []
    opt  = MTDSOptimizer(calc, lam=lam, ref_w=ref_w)

    # Original boundaries saved
    orig_constraints = opt._constraints

    alt_targets = [0.50, 0.60, 0.70, 0.80]
    for target_int in alt_targets:
        # Override constraints dynamically for this target
        def custom_constraints():
            return [
                {"type": "eq",   "fun": lambda w: w.sum() - 1.0},
                {"type": "eq",   "fun": lambda w: (w[0]+w[1]) - target_int}, # EXACT target int
                {"type": "eq",   "fun": lambda w: (w[2]+w[3]+w[4]+w[5]+w[6]+w[7]) - (1.0 - target_int)},
                {"type": "ineq", "fun": lambda w: w[0] - 0.10},
                {"type": "ineq", "fun": lambda w: 0.35 - w[1]},
                {"type": "ineq", "fun": lambda w: (w[0]+w[1]+w[2]+w[3]+w[6]) - 0.55},
                {"type": "ineq", "fun": lambda w: 0.30 - (w[2]+w[5])},
                {"type": "ineq", "fun": lambda w: 0.15 - (w[3]+w[4])},
                {"type": "ineq", "fun": lambda w: 0.16 - (w[6]+w[7])},
            ]
        opt._constraints = custom_constraints
        try:
            r = opt.optimize(n_starts=10)
            m = r["metrics"]
            alts.append({
                "Alternativa": f"{int(target_int*100)}/{int((1-target_int)*100)}",
                "Costo_Esp": m["cost_ev"],
                "Riesgo_Std": m["cost_std"],
                "CVaR_95": m["cvar95"],
                **{INSTRUMENTS[i][0]: r["weights"][i] for i in range(N_INST)}
            })
        except Exception:
            pass

    df_alts = pd.DataFrame(alts)

    # Restore constraints for main optimization
    opt._constraints = orig_constraints
    res  = opt.optimize(n_starts=30)
    w_opt, mc = res["weights"], res["metrics"]

    port   = portfolio_indicators(w_opt, portfolio)
    stress = stress_analysis(w_opt, p)

    print("\n       Calculando frontera eficiente (40 puntos) …")
    frontier = opt.efficient_frontier(n_pts=40)

    # ── Output consola ─────────────────────────────────────────────────────
    print("\n" + "=" * 70)
    print("  ESTRATEGIA ÓPTIMA  —  MFMP 2026")
    print("=" * 70)
    print(f"  {'Mercado':<20} {'Moneda':<8} {'Tasa':<12}"
          f" {'MFMP 26':>9} {'Ref. Act.':>10}")
    print("  " + "─" * 63)
    prev_m = ""
    for i, inst in enumerate(INSTRUMENTS):
        pct26 = w_opt[i] * 100
        pct25 = ref_w[i] * 100
        m_label = inst[1] if inst[1] != prev_m else ""
        print(f"  {m_label:<20} {inst[2]:<8} {inst[3]:<12}"
              f" {pct26:>8.1f}% {pct25:>9.1f}%")
        prev_m = inst[1]
    print("  " + "─" * 63)
    int_opt = (w_opt[0]+w_opt[1])*100
    int_ref = (ref_w[0]+ref_w[1])*100
    print(f"  {'TOTAL':<42} {'100.0%':>9} {'100.0%':>10}")
    print(f"  {'[Interno COP+UVR]':<42} {int_opt:>8.1f}% {int_ref:>9.1f}%")
    print(f"  {'[Externo FX]':<42} {100-int_opt:>8.1f}% {100-int_ref:>9.1f}%")

    print("\n  ── INDICADORES BM-FMI (Apéndice III) ──────────────────────────")
    print(f"  TPV (años):                  {port['TPV_años']:.2f}")
    print(f"  TPR (años):                  {port['TPR_años']:.2f}")
    print(f"  % Deuda FX (externo):        {port['pct_FX']:.1f}%")
    print(f"  % Deuda variable:            {port['pct_variable']:.1f}%")
    print(f"  Intereses/PIB (base):        {stress['base']['int_pct_gdp']:.3f}%")
    print(f"  Intereses/Ingresos (base):   {stress['base']['int_pct_rev']:.3f}%")
    print(f"  Δ int/PIB shock +200pbs:     +{stress['tasa+200']['delta_pct_gdp']:.3f}%")
    print(f"  Δ int/PIB depr. 30% COP:     +{stress['depr30']['delta_pct_gdp']:.3f}%")
    print(f"  Δ int/PIB shock combinado:   +{stress['combinado']['delta_pct_gdp']:.3f}%")
    print(f"\n  ── ANÁLISIS ESTOCÁSTICO ({n_scenarios:,} escenarios MC) ────────────")
    print(f"  E[int/PIB]:                  {mc['cost_ev']:.3f}%")
    print(f"  σ[int/PIB]:                  {mc['cost_std']:.3f}%")
    print(f"  CVaR 95%:                    {mc['cvar95']:.3f}%")
    print("=" * 70)

    # ── [5] Guardar resultados ─────────────────────────────────────────────
    print("\n[5/6]  Guardando resultados MTDS 2026 …")
    res_path = r"MTDS_2026_Resultados.xlsx"
    # Añadimos de vuelta risk_aversion al dict p para reportes si fue borrado con .pop()
    p["risk_aversion"] = lam
    df_scenarios_1000 = calc.scenario_dataframe(w_opt, n_scenarios=1000)

    # We will temporarily append the new sheets logic directly to the workbook inside save_results context
    # but since save_results saves and closes, we do it after.
    save_results(w_opt, mc, stress, port, frontier, res_path, df_scenarios=df_scenarios_1000, p_dict=p)

    # Append the new sheets 1000_Estrategias and Alternativas_Int_Ext
    from openpyxl.utils.dataframe import dataframe_to_rows
    wb = load_workbook(res_path)

    ws_strats = wb.create_sheet("1000_Estrategias")
    for r in dataframe_to_rows(df_1000_strats, index=False, header=True):
        ws_strats.append(r)

    ws_alts = wb.create_sheet("Alternativas_Int_Ext")
    for r in dataframe_to_rows(df_alts, index=False, header=True):
        ws_alts.append(r)

    wb.save(res_path)
    wb.close()

    print(f"       ✔  {res_path} (Incluyendo 1000 Estrategias y Alternativas Int/Ext)")

    print("\n[6/6]  Copiando script a outputs …")
    shutil.copy(__file__, r"mtds_2026_v2_ejecutado.py")
    print("       ✔  mtds_2026_v2_ejecutado.py")
    print("\n  Proceso MTDS 2026 completado.\n")
    # Variable para capturar logs del PDF
    pdf_content = ""
    
    def log_print(text):
        nonlocal pdf_content
        print(text)
        pdf_content += text + "\n"

    log_print("=" * 70)
    log_print("  HERRAMIENTA MTDS 2026  —  Ministerio de Hacienda y Crédito Público")
    log_print("=" * 70)

    # Aquí un truco: vamos a capturar los indicadores BM-FMI que ya calculaste
    log_print(f"  TPV (años):                  {port['TPV_años']:.2f}")
    log_print(f"  TPR (años):                  {port['TPR_años']:.2f}")
    log_print(f"  % Deuda FX (externo):        {port['pct_FX']:.1f}%")
    log_print(f"  Intereses/PIB (base):        {stress['base']['int_pct_gdp']:.3f}%")
    log_print(f"  CVaR 95%:                    {mc['cvar95']:.3f}%")
    log_print("=" * 70)

    # REGENERACIÓN DEL PDF
    log_print("\n[PDF] Generando Reporte Ejecutivo en PDF …")
    pdf = MTDSPDF()

    pdf.add_page()
    pdf.chapter_title("1. ESTADÍSTICAS CONSULTA ORACLE (DEUDA EXTERNA)")
    if oracle["ok"] and oracle.get("report"):
        pdf.add_terminal_text(oracle["report"])
    else:
        pdf.add_terminal_text("No se pudo cargar el reporte de Oracle.")

    pdf.add_page()
    pdf.chapter_title("2. PERFIL DE VENCIMIENTOS (DEUDA INTERNA Y EXTERNA)")
    if perfil["ok"] and perfil.get("report"):
        pdf.add_terminal_text(perfil["report"])
    else:
        pdf.add_terminal_text("No se pudo cargar el reporte del perfil de vencimientos.")

    pdf.add_page()
    pdf.chapter_title("3. MÉTRICAS CALCULADAS Y ESTRATEGIA OPTIMIZADA")
    metrics_report = []
    metrics_report.append("=" * 70)
    metrics_report.append("  ESTRATEGIA ÓPTIMA  —  MFMP 2026")
    metrics_report.append("=" * 70)
    metrics_report.append(f"  {'Mercado':<20} {'Moneda':<8} {'Tasa':<12}"
          f" {'MFMP 26':>9} {'Ref. Act.':>10}")
    metrics_report.append("  " + "─" * 63)
    prev_m = ""
    for i, inst in enumerate(INSTRUMENTS):
        pct26 = w_opt[i] * 100
        pct25 = ref_w[i] * 100
        m_label = inst[1] if inst[1] != prev_m else ""
        metrics_report.append(f"  {m_label:<20} {inst[2]:<8} {inst[3]:<12}"
              f" {pct26:>8.1f}% {pct25:>9.1f}%")
        prev_m = inst[1]
    metrics_report.append("  " + "─" * 63)
    int_opt = (w_opt[0]+w_opt[1])*100
    int_ref = (ref_w[0]+ref_w[1])*100
    metrics_report.append(f"  {'TOTAL':<42} {'100.0%':>9} {'100.0%':>10}")
    metrics_report.append(f"  {'[Interno COP+UVR]':<42} {int_opt:>8.1f}% {int_ref:>9.1f}%")
    metrics_report.append(f"  {'[Externo FX]':<42} {100-int_opt:>8.1f}% {100-int_ref:>9.1f}%")

    metrics_report.append("\n  ── INDICADORES BM-FMI (Apéndice III) ──────────────────────────")
    metrics_report.append(f"  TPV (años):                  {port['TPV_años']:.2f}")
    metrics_report.append(f"  TPR (años):                  {port['TPR_años']:.2f}")
    metrics_report.append(f"  % Deuda FX (externo):        {port['pct_FX']:.1f}%")
    metrics_report.append(f"  % Deuda variable:            {port['pct_variable']:.1f}%")
    metrics_report.append(f"  Intereses/PIB (base):        {stress['base']['int_pct_gdp']:.3f}%")
    metrics_report.append(f"  Intereses/Ingresos (base):   {stress['base']['int_pct_rev']:.3f}%")
    metrics_report.append(f"  Δ int/PIB shock +200pbs:     +{stress['tasa+200']['delta_pct_gdp']:.3f}%")
    metrics_report.append(f"  Δ int/PIB depr. 30% COP:     +{stress['depr30']['delta_pct_gdp']:.3f}%")
    metrics_report.append(f"  Δ int/PIB shock combinado:   +{stress['combinado']['delta_pct_gdp']:.3f}%")

    metrics_report.append(f"\n  ── CRITERIOS DE SELECCIÓN (Métricas de Riesgo) ───────────────────")
    metrics_report.append(f"  La combinación óptima fue seleccionada minimizando la")
    metrics_report.append(f"  siguiente función objetivo basada en los {n_scenarios:,} escenarios MC:")
    metrics_report.append(f"     Objetivo = E[Costo] + λ × σ[Costo]")
    metrics_report.append(f"  Donde:")
    metrics_report.append(f"  - λ (Aversión al riesgo):    {lam}")
    metrics_report.append(f"  - E[Costo] (Esperado):       {mc['cost_ev']:.3f}% PIB")
    metrics_report.append(f"  - σ[Costo] (Desv. Estándar): {mc['cost_std']:.3f}% PIB")
    metrics_report.append(f"  - Valor Objetivo minimizado: {(mc['cost_ev'] + lam * mc['cost_std']):.3f}%")
    metrics_report.append(f"  - CVaR 95%:                  {mc['cvar95']:.3f}%")
    metrics_report.append("=" * 70)
    pdf.add_terminal_text("\n".join(metrics_report))
    
    # ADD YAHOO FORECAST AND ALTERNATIVES TO PDF
    pdf.add_page()
    pdf.chapter_title("4. PRONÓSTICOS MACRO (YAHOO FINANCE)")
    pdf.add_terminal_text(forecast_results["log"])
    pdf.image(forecast_results["plot"], w=180)

    pdf.add_page()
    pdf.chapter_title("5. ALTERNATIVAS DE COMPOSICIÓN (INT/EXT)")
    alt_text = "Evaluación de diferentes límites de Deuda Interna / Externa:\n\n"
    alt_text += df_alts.to_string(index=False)
    pdf.add_terminal_text(alt_text)

    pdf_path = r"MTDS_2026_Reporte_Ejecutivo.pdf"
    pdf.output(pdf_path)
    print(f"       ✔  Reporte PDF guardado en: {pdf_path}")

    log_print(f"\n[DATOS MACRO] PIB de referencia: {p.get('gdp_cop_bn', 1300):,.0f} mil millones (mil millones = billón COP)")

if __name__ == "__main__":
    main()
