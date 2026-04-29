import pandas as pd
import numpy as np

p = {
    "usdcop_spot": 4200.0,
    "gdp_cop_bn": 1998508.0
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

p["total_absolute_debt"] = total_emis_saldo + total_oracle_saldo_usd * p["usdcop_spot"]
p["raw_base_cost_cop"] = raw_int_cost + raw_ext_cost_usd * p["usdcop_spot"]
p["target_int_pct_gdp"] = 833073359.49 / p["gdp_cop_bn"] / 10

print("total_absolute_debt:", p["total_absolute_debt"])
print("raw_base_cost_cop:", p["raw_base_cost_cop"])
print("target_int_pct_gdp:", p["target_int_pct_gdp"])

# Wait, `raw_base_cost_cop` is 59137140921001.42
# `target_int_pct_gdp` is 41.6847
# So `target_int_pct_gdp / raw_base_cost_cop` is very small:
# 41.68 / 59137140921001.42 = 7e-13.
# But `absolute_cost` = weighted_rate * `total_absolute_debt`.
# weighted_rate is ~ 0.07.
# 0.07 * 2471753084491324.0 = 173022715914392.
# Then 173022715914392. * (41.68 / 59137140921001.42) = 121.
# But `int_pct_gdp` is outputting 210526.709% !!! Why?
