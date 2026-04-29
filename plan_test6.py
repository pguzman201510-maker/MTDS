import pandas as pd
import numpy as np

# Simulate main()
p = {
    "gdp_cop_bn": 1998508.0,
    "usdcop_spot": 4200.0,
}

df_emis = pd.read_excel('Emisiones Vigentes 03.xlsx')
df_emis['Suma de SALDO'] = pd.to_numeric(df_emis['Suma de SALDO'], errors='coerce').fillna(0)
df_emis['TASA'] = pd.to_numeric(df_emis['TASA'], errors='coerce').fillna(0)
total_emis_saldo = df_emis['Suma de SALDO'].sum()
raw_int_cost = (df_emis['Suma de SALDO'] * (df_emis['TASA'] / 100)).sum()

df_oracle = pd.read_csv('Consulta Oracle 31-03-2026.xls', sep='\t', encoding='utf-8')
df_oracle['SDO_US'] = pd.to_numeric(df_oracle['SDO_US'], errors='coerce').fillna(0)
df_oracle['MARGEN_VALOR'] = pd.to_numeric(df_oracle['MARGEN_VALOR'], errors='coerce').fillna(0)
total_oracle_saldo_usd = df_oracle['SDO_US'].sum()
raw_ext_cost_usd = (df_oracle['SDO_US'] * (df_oracle['MARGEN_VALOR'] / 100)).sum()

target_int_cost_mm = 694651132.90
target_ext_cost_mm = 138422226.58
target_total_cost_mm = target_int_cost_mm + target_ext_cost_mm

target_pct_gdp = (target_total_cost_mm / p["gdp_cop_bn"]) / 10 * 100
print("Target PCT GDP:", target_pct_gdp)

# Calculate total debt absolute
p["total_absolute_debt"] = total_emis_saldo + total_oracle_saldo_usd * p["usdcop_spot"]
print("Total absolute debt COP:", p["total_absolute_debt"])

# In deterministic_cost, it evaluates weighted_rate.
# Let's say base weighted_rate is approx 0.06983.
weighted_rate_base = 0.06983
base_theoretical_cost = weighted_rate_base * p["total_absolute_debt"]

# We need: (base_theoretical_cost * scale_factor) / (p["gdp_cop_bn"] * 1e9) * 100 = target_pct_gdp
# So:
# target_pct_gdp = (target_total_cost_mm * 1e6) / (p["gdp_cop_bn"] * 1e9) * 100
# Thus we want the absolute cost to be target_total_cost_mm * 1e6.
# If we do cost = total_absolute_debt * weighted_rate * scale_factor
# scale_factor = (target_total_cost_mm * 1e6) / (p["total_absolute_debt"] * weighted_rate_base_actual)
