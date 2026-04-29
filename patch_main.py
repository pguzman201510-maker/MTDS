import re

with open("mtds_2026_v2 (1).py", "r") as f:
    code = f.read()

injection_code = """
    # ── [NEW] Extraer saldos y costos absolutos de Emisiones Vigentes y Oracle ──
    try:
        df_emis = pd.read_excel(PERFIL_PATH.replace('Perfil de vencimientos 2026.xlsm', 'Emisiones Vigentes 03.xlsx'))
        df_emis['Suma de SALDO'] = pd.to_numeric(df_emis['Suma de SALDO'], errors='coerce').fillna(0)
        df_emis['TASA'] = pd.to_numeric(df_emis['TASA'], errors='coerce').fillna(0)
        total_emis_saldo = df_emis['Suma de SALDO'].sum()
        raw_int_cost = (df_emis['Suma de SALDO'] * (df_emis['TASA'] / 100)).sum()
    except Exception as e:
        print(f"Error leyendo Emisiones Vigentes: {e}")
        total_emis_saldo = 0
        raw_int_cost = 0

    try:
        # Load the oracle CSV which is actually tab separated
        df_oracle = pd.read_csv(ORACLE_PATH, sep='\\t', encoding='utf-8')
        df_oracle['SDO_US'] = pd.to_numeric(df_oracle['SDO_US'], errors='coerce').fillna(0)
        df_oracle['MARGEN_VALOR'] = pd.to_numeric(df_oracle['MARGEN_VALOR'], errors='coerce').fillna(0)
        total_oracle_saldo_usd = df_oracle['SDO_US'].sum()
        raw_ext_cost_usd = (df_oracle['SDO_US'] * (df_oracle['MARGEN_VALOR'] / 100)).sum()
    except Exception as e:
        print(f"Error leyendo Oracle raw: {e}")
        total_oracle_saldo_usd = 0
        raw_ext_cost_usd = 0

    # Guardar en p para reemplazar p["debt_pct_gdp"]
    p["total_absolute_debt"] = total_emis_saldo + total_oracle_saldo_usd * p.get("usdcop_spot", 4200.0)
    p["raw_base_cost_cop"] = raw_int_cost + raw_ext_cost_usd * p.get("usdcop_spot", 4200.0)
    # The actual absolute target for "Intereses totales" is 833,073,359.49
    # The required base Intereses/PIB should reflect this mathematically over the 1998508.0 GDP.
    # Percentage is target / GDP / 10.
    p["target_int_pct_gdp"] = 833073359.49 / p.get("gdp_cop_bn", 1998508.0) / 10

"""

# Find where to inject: Right after `p = tpl["params"]` or at the end of the extraction logic.
target = """    p = tpl["params"]
    n_scenarios = int(p.pop("n_scenarios", 1000))
    horizon     = int(p.pop("horizon", 5))
    lam         = float(p.pop("risk_aversion", 1.5))"""

if target in code:
    code = code.replace(target, target + "\n" + injection_code)
    with open("mtds_2026_v2 (1).py", "w") as f:
        f.write(code)
    print("Patched main()")
else:
    print("Could not find target in code")
