# If I compute the actual absolute interest from the files:
import pandas as pd
df_emis = pd.read_excel('Emisiones Vigentes 03.xlsx')
df_emis['Suma de SALDO'] = pd.to_numeric(df_emis['Suma de SALDO'], errors='coerce').fillna(0)
df_emis['TASA'] = pd.to_numeric(df_emis['TASA'], errors='coerce').fillna(0)
raw_int_cost = (df_emis['Suma de SALDO'] * (df_emis['TASA']/100)).sum()

df_oracle = pd.read_csv('Consulta Oracle 31-03-2026.xls', sep='\t', encoding='utf-8')
df_oracle['SDO_US'] = pd.to_numeric(df_oracle['SDO_US'], errors='coerce').fillna(0)
df_oracle['MARGEN_VALOR'] = pd.to_numeric(df_oracle['MARGEN_VALOR'], errors='coerce').fillna(0)
raw_ext_cost_usd = (df_oracle['SDO_US'] * (df_oracle['MARGEN_VALOR']/100)).sum()

usdcop_spot = 4200.0
raw_base_cost_cop = raw_int_cost + raw_ext_cost_usd * usdcop_spot

print(f"Raw Base Cost COP: {raw_base_cost_cop}")

# The user explicitly told us:
# "Utilices la suma de los saldos absolutos y los cupones extraídos directamente de Oracle y Emisiones Vigentes para generar el Costo Total"

# If we generate the `Costo Total` by directly extracting from Oracle and Emisiones Vigentes.
# We then "escalándolo de manera que los resultados de 'Intereses/PIB (base)' reflejen con precisión este 41.68% objetivo".

# Wait, the instruction is to CHANGE deterministic_cost and CostRiskCalc.
# How do we pass the extracted absolute values to those functions? We can precalculate them in `main()` and pass them in `p`!
# `p["raw_int_cost"] = raw_int_cost`
# `p["raw_ext_cost_usd"] = raw_ext_cost_usd`

# Let's say `p["raw_base_cost_cop"] = raw_base_cost_cop`
# We want this base cost to correspond to 41.68% GDP.
# So `scaling_factor = 41.68 / raw_base_cost_cop`
# Then for any new weights `w` and shock, we compute the relative cost compared to the base, and multiply by `raw_base_cost_cop * scaling_factor`.
# Wait, `w` changes the composition.
# If `Cost = Total_Absolute_Debt * weighted_rate`.
# If `base_Cost = Total_Absolute_Debt * base_weighted_rate`.
# Then `Cost = base_Cost * (weighted_rate / base_weighted_rate)`.
# And we know `base_Cost` scaled = 41.68%.
# So `int_pct_gdp = 41.68 * (weighted_rate / base_weighted_rate)`!
# Or `int_pct_gdp = weighted_rate * (41.68 / base_weighted_rate)`!
# Thus, `debt_pct_gdp` is effectively replaced by `41.68 / base_weighted_rate` !

# Let's read carefully: "Utilices la suma de los saldos absolutos y los cupones extraídos directamente de Oracle y Emisiones Vigentes para generar el Costo Total, escalándolo de manera que los resultados de "Intereses/PIB (base)" reflejen con precisión este 41.68% objetivo."
