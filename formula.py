# The instruction is:
# "Elimines los factores 'hardcodeados' y el uso de proporciones genéricas (como el 55.0% de debt_pct_gdp) en la fórmula final. Utilices la suma de los saldos absolutos y los cupones extraídos directamente de Oracle y Emisiones Vigentes para generar el Costo Total, escalándolo de manera que los resultados de "Intereses/PIB (base)" reflejen con precisión este 41.68% objetivo. Asegures que las métricas finales que se imprimen en consola y se guardan en los reportes correspondan fielmente a la carga real del portafolio, respetando el PIB base de 1998508.0."

# Right now `int_pct_gdp` in deterministic_cost:
# `int_pct_gdp = weighted_rate * p["debt_pct_gdp"]`

# In CostRiskCalc:
# `cost_t = cop_cost + uvr_cost + ...`
# `ip[:, t] = cost_t * p["debt_pct_gdp"]`

# What if `p["debt_pct_gdp"]` is dynamically calculated based on the absolute total debt and GDP, such that it correctly matches the actual interest/GDP ratio?
# Wait! "Utilices la suma de los saldos absolutos y los cupones extraídos directamente de Oracle y Emisiones Vigentes para generar el Costo Total"
# Instead of multiplying `cost_t * p["debt_pct_gdp"]`, it should multiply by the total absolute debt, to get the absolute interest, and then divide by GDP?
# The interest values are:
# Intereses internos: 694,651,132.90
# Intereses externos: 138,422,226.58
# Interest total: 833,073,359.49.
# The user wants exactly THESE numbers to be generated.
# How are these numbers obtained from "Emisiones Vigentes" and "Oracle"?
# Let's see if 694,651,132.90 is equal to sum(Saldo * Tasa) / something?
# We found sum(Saldo * Tasa / 100) = 44,873,343,266,710.0
# And 44,873,343,266,710.0 / 694,651,132.90 = 64598.38
# Could "Suma de Valor Nominal $" be it?
# sum(Valor Nominal * Tasa / 100) = 54,601,634,422,240.67
# What about "Precio Limpio"?

import pandas as pd
df_emis = pd.read_excel('Emisiones Vigentes 03.xlsx')
df_emis['Suma de SALDO'] = pd.to_numeric(df_emis['Suma de SALDO'], errors='coerce').fillna(0)
df_emis['TASA'] = pd.to_numeric(df_emis['TASA'], errors='coerce').fillna(0)
df_emis['Dto $'] = pd.to_numeric(df_emis['Dto $'], errors='coerce').fillna(0)

# Check different columns to see if we can get 694,651,132.90
val1 = (df_emis['Suma de SALDO'] * df_emis['TASA']).sum() / 100
val2 = (df_emis['Dto $']).sum()
print("Dto sum:", val2)
