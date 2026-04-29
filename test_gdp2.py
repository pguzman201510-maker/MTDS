import pandas as pd
import numpy as np

oracle_usd_interest = 3396142298.64
usd_cop_spot = 4200.0

print("Oracle USD * spot:", oracle_usd_interest * usd_cop_spot)
# Wait, 138,422,226.58 is the target external interest.
print("Target external:", 138422226.58)

# "Intereses internos: 694,651,132.90"
# "Intereses externos: 138,422,226.58"

# Maybe the sums are given in MILLIONS and PIB is in BILLIONS (billones = million millions).
# Intereses = 833,073,359.49. Let's assume these are thousands of something?

# The prompt asks: "Requiero que modifiques las funciones deterministic_cost y la clase CostRiskCalc (o el lugar adecuado en el código) para que:
# Elimines los factores "hardcodeados" y el uso de proporciones genéricas (como el 55.0% de debt_pct_gdp) en la fórmula final.
# Utilices la suma de los saldos absolutos y los cupones extraídos directamente de Oracle y Emisiones Vigentes para generar el Costo Total, escalándolo de manera que los resultados de "Intereses/PIB (base)" reflejen con precisión este 41.68% objetivo."

# If we extract them from the data:
df_oracle = pd.read_csv('Consulta Oracle 31-03-2026.xls', sep='\t', encoding='utf-8')
df_oracle['MARGEN_VALOR'] = pd.to_numeric(df_oracle['MARGEN_VALOR'], errors='coerce').fillna(0)
df_oracle['SDO_US'] = pd.to_numeric(df_oracle['SDO_US'], errors='coerce').fillna(0)
# Summing SDO_US * MARGEN_VALOR / 100 ? Wait, interest = balance * rate.
external_interest = (df_oracle['SDO_US'] * (df_oracle['MARGEN_VALOR']/100)).sum()
# Convert to COP? What if we don't convert to COP?
print("external USD interest sum:", external_interest)

# What if MARGEN_VALOR is not percentage?
# What if the values are directly given by the prompt and we should just HARDCODE these values?
# "Utilices la suma de los saldos absolutos y los cupones extraídos directamente de Oracle y Emisiones Vigentes para generar el Costo Total, escalándolo de manera que los resultados de "Intereses/PIB (base)" reflejen con precisión este 41.68% objetivo."
