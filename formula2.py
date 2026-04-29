import pandas as pd
df_oracle = pd.read_csv('Consulta Oracle 31-03-2026.xls', sep='\t', encoding='utf-8')
df_oracle['SDO_US'] = pd.to_numeric(df_oracle['SDO_US'], errors='coerce').fillna(0)
df_oracle['MARGEN_VALOR'] = pd.to_numeric(df_oracle['MARGEN_VALOR'], errors='coerce').fillna(0)
df_oracle['MTO_CREDITO'] = pd.to_numeric(df_oracle['MTO_CREDITO'], errors='coerce').fillna(0)

print((df_oracle['SDO_US'] * df_oracle['MARGEN_VALOR'] / 100).sum() * 4178.10) # EurCop spot? No, 4200.0 (UsdCop spot).
print("We found earlier: external USD cost = 3396142298.64")
print("Target external cost = 138422226.58")
