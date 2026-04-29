import numpy as np
# Let's verify what `weighted_rate * p["total_absolute_debt"] / p["gdp_cop_bn"]` evaluates to.
import sys
import os
sys.path.append(os.getcwd())
import mtds_script as ms

ms.ORACLE_PATH = "Consulta Oracle 31-03-2026.xls"
ms.TEMPLATE_PATH = "MTDS_Bloomberg_Template.xlsx"
ms.PERFIL_PATH = "Perfil de vencimientos 2026.xlsm"

oracle = ms.load_from_oracle(ms.ORACLE_PATH)
perfil = ms.load_from_perfil(ms.PERFIL_PATH, oracle)
tpl = ms.load_from_template(ms.TEMPLATE_PATH)
p = tpl["params"]

import pandas as pd
df_emis = pd.read_excel('Emisiones Vigentes 03.xlsx')
df_emis['Suma de SALDO'] = pd.to_numeric(df_emis['Suma de SALDO'], errors='coerce').fillna(0)
total_emis_saldo = df_emis['Suma de SALDO'].sum()

total_oracle_saldo_usd = oracle["external_total_usd"]

p["total_absolute_debt"] = total_emis_saldo + total_oracle_saldo_usd * p.get("usdcop_spot", 4200.0)

# Simulate main parameter overwrite
if oracle["ok"]:
    oracle_rates = oracle["rates"]
    if "DE_USD_F" in oracle_rates: p["usd_fixed_rate"] = oracle_rates["DE_USD_F"]["tasa_wp"]
    if "DE_EUR_F" in oracle_rates: p["eur_fixed_rate"] = oracle_rates["DE_EUR_F"]["tasa_wp"]
    if "DE_CHF_F" in oracle_rates: p["chf_fixed_rate"] = oracle_rates["DE_CHF_F"]["tasa_wp"]
    if "DE_USD_V" in oracle_rates: p["usd_spread_sofr"] = oracle_rates["DE_USD_V"]["tasa_wp"]
    if "DE_EUR_V" in oracle_rates: p["eur_spread_eurib"] = oracle_rates["DE_EUR_V"]["tasa_wp"]
    if "DE_CHF_V" in oracle_rates: p["chf_spread_saron"] = oracle_rates["DE_CHF_V"]["tasa_wp"]
    if "DI_COP_EXT" in oracle_rates and oracle_rates["DI_COP_EXT"]["tasa_wp"] > 0:
        p["cop_fixed_rate"] = max(p["cop_fixed_rate"], oracle_rates["DI_COP_EXT"]["tasa_wp"])

w_base = np.array([0.40, 0.20, 0.24, 0.06, 0.05, 0.05, 0.0, 0.0])

rates = {
    "DI_COP_F": p["cop_fixed_rate"]/100,
    "DI_UVR_F": (p["uvr_real_rate"] + p["uvr_inflation"])/100,
    "DE_USD_F": p["usd_fixed_rate"]/100,
    "DE_EUR_F": p["eur_fixed_rate"]/100,
    "DE_EUR_V": (p["euribor_base"] + p["eur_spread_eurib"])/100,
    "DE_USD_V": (p["sofr_base"] + p["usd_spread_sofr"])/100,
    "DE_CHF_F": p["chf_fixed_rate"]/100,
    "DE_CHF_V": (p["saron_base"] + p["chf_spread_saron"])/100,
}

N_INST = 8
INSTRUMENTS = [("DI_COP_F",), ("DI_UVR_F",), ("DE_USD_F",), ("DE_EUR_F",), ("DE_EUR_V",), ("DE_USD_V",), ("DE_CHF_F",), ("DE_CHF_V",)]
weighted_rate = sum(w_base[i] * rates[INSTRUMENTS[i][0]] for i in range(N_INST))

base_pct_gdp_original = weighted_rate * p["debt_pct_gdp"]
print(f"Original base pct GDP: {base_pct_gdp_original}")

# New calculation: Cost = total_absolute_debt * weighted_rate
cost = p["total_absolute_debt"] * weighted_rate
# Int_pct_gdp = Cost / pib ?
# 1998508.0 is GDP in billones. So p["gdp_cop_bn"] * 1e9 = GDP absolute.
gdp_absolute = p["gdp_cop_bn"] * 1e9
int_pct_gdp_new = cost / gdp_absolute * 100
print(f"New base pct GDP (using saldos): {int_pct_gdp_new}")

# The user target is 41.68%
# Target target is 833,073,359.49. Let's see if our absolute cost is around that.
print(f"Our absolute cost: {cost}")
print(f"User target absolute cost: 833,073,359.49")
print(f"If we divide absolute cost by target: {cost / 833073359.49}")
print(f"Target absolute cost / total debt: {833073359.49 / p['total_absolute_debt']}")
