import pandas as pd

df_oracle = pd.read_csv('Consulta Oracle 31-03-2026.xls', sep='\t', encoding='utf-8')
df_oracle['MARGEN_VALOR'] = pd.to_numeric(df_oracle['MARGEN_VALOR'], errors='coerce').fillna(0)
df_oracle['SDO_US'] = pd.to_numeric(df_oracle['SDO_US'], errors='coerce').fillna(0)

# What if it's SDO_US * MARGEN_VALOR / TRM?
# Let's check how the external_interest 138,422,226.58 relates to external USD interest sum: 3396142298.64
print("Ratio:", 3396142298.64 / 138422226.58)

emis = pd.read_excel('Emisiones Vigentes 03.xlsx')
emis['Suma de SALDO'] = pd.to_numeric(emis['Suma de SALDO'], errors='coerce').fillna(0)
emis['TASA'] = pd.to_numeric(emis['TASA'], errors='coerce').fillna(0)
internal_interest = (emis['Suma de SALDO'] * emis['TASA']).sum()
print("Internal interest sum:", internal_interest)

# Target internal: 694,651,132.90
print("Ratio internal:", internal_interest / 694651132.90)
