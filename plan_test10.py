# Let's write down the exact changes for CostRiskCalc and deterministic_cost.

# Change 1: In `main()`, load the absolute values.
import pandas as pd
df_emis = pd.read_excel('Emisiones Vigentes 03.xlsx')
df_emis['Suma de SALDO'] = pd.to_numeric(df_emis['Suma de SALDO'], errors='coerce').fillna(0)
df_emis['TASA'] = pd.to_numeric(df_emis['TASA'], errors='coerce').fillna(0)
raw_int_cost = (df_emis['Suma de SALDO'] * (df_emis['TASA']/100)).sum()
total_emis_saldo = df_emis['Suma de SALDO'].sum()

df_oracle = pd.read_csv('Consulta Oracle 31-03-2026.xls', sep='\t', encoding='utf-8')
df_oracle['SDO_US'] = pd.to_numeric(df_oracle['SDO_US'], errors='coerce').fillna(0)
df_oracle['MARGEN_VALOR'] = pd.to_numeric(df_oracle['MARGEN_VALOR'], errors='coerce').fillna(0)
raw_ext_cost_usd = (df_oracle['SDO_US'] * (df_oracle['MARGEN_VALOR']/100)).sum()
total_oracle_saldo_usd = df_oracle['SDO_US'].sum()

# Change 2: In `main()`, pass them to `p`.
# p["total_absolute_debt"] = total_emis_saldo + total_oracle_saldo_usd * p["usdcop_spot"]
# p["raw_base_cost_cop"] = raw_int_cost + raw_ext_cost_usd * p["usdcop_spot"]

# And we have the target 41.68%
# p["target_int_pct_gdp"] = 41.6847648  # from 833,073,359.49

# Or we can compute it inside `main()`:
# p["cost_scale_factor"] = (833073359.49 / p["gdp_cop_bn"] / 10) / (p["raw_base_cost_cop"] / p["total_absolute_debt"])
# No, "escalándolo de manera que los resultados de 'Intereses/PIB (base)' reflejen con precisión este 41.68% objetivo."

# Change 3: In `deterministic_cost`:
# Instead of: `int_pct_gdp = weighted_rate * p["debt_pct_gdp"]`
# We use:
# absolute_cost = weighted_rate * p["total_absolute_debt"]
# int_pct_gdp = absolute_cost * (p["target_int_pct_gdp"] / p["raw_base_cost_cop"])
# Wait, if `weighted_rate * p["total_absolute_debt"]` is the new absolute cost...
# For the base portfolio, `weighted_rate_base * p["total_absolute_debt"]` SHOULD roughly equal `p["raw_base_cost_cop"]`.
# So multiplying by `(p["target_int_pct_gdp"] / p["raw_base_cost_cop"])` perfectly scales it to 41.68%!
