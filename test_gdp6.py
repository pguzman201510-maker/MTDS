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

print(f"Raw internal cost: {raw_int_cost}")
print(f"Raw external cost (COP): {raw_ext_cost_usd * usdcop_spot}")
print(f"Raw total cost (COP): {raw_base_cost_cop}")

# The user gives:
target_int = 694651132.90
target_ext = 138422226.58
target_tot = 833073359.49

scale_int = target_int / raw_int_cost
scale_ext = target_ext / (raw_ext_cost_usd * usdcop_spot)
scale_tot = target_tot / raw_base_cost_cop

print(f"Scale int: {scale_int}")
print(f"Scale ext: {scale_ext}")
print(f"Scale tot: {scale_tot}")

# Is scale_int similar to scale_ext?
