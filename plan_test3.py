import pandas as pd

df_emis = pd.read_excel('Emisiones Vigentes 03.xlsx')
df_emis['Suma de SALDO'] = pd.to_numeric(df_emis['Suma de SALDO'], errors='coerce').fillna(0)
total_emis_saldo = df_emis['Suma de SALDO'].sum()

df_oracle = pd.read_csv('Consulta Oracle 31-03-2026.xls', sep='\t', encoding='utf-8')
df_oracle['SDO_US'] = pd.to_numeric(df_oracle['SDO_US'], errors='coerce').fillna(0)
total_oracle_saldo_usd = df_oracle['SDO_US'].sum()

usdcop_spot = 4200.0
total_absolute_debt = total_emis_saldo + total_oracle_saldo_usd * usdcop_spot

print(f"Total Emis Saldo (COP): {total_emis_saldo}")
print(f"Total Oracle Saldo (USD): {total_oracle_saldo_usd}")
print(f"Total Debt (COP): {total_absolute_debt}")

# If we calculate total absolute interest for a given weighted rate:
# absolute_interest = weighted_rate * total_absolute_debt
# int_pct_gdp = absolute_interest / (1998508.0 * scale_factor)

# But wait, what is the scale factor?
# 44873343266710.0 + 3396142298.64 * 4200 = 59,137,140,921,001.42 (Raw base cost COP)
# To get 833,073,359.49 from that:
# ratio = 833073359.49 / 59137140921001.42 = 1.4087e-5
