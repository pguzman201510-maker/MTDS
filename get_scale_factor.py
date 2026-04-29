import pandas as pd

df_emis = pd.read_excel('Emisiones Vigentes 03.xlsx')
df_emis['Suma de SALDO'] = pd.to_numeric(df_emis['Suma de SALDO'], errors='coerce').fillna(0)
total_emis_saldo = df_emis['Suma de SALDO'].sum()

df_oracle = pd.read_csv('Consulta Oracle 31-03-2026.xls', sep='\t', encoding='utf-8')
df_oracle['SDO_US'] = pd.to_numeric(df_oracle['SDO_US'], errors='coerce').fillna(0)
total_oracle_saldo_usd = df_oracle['SDO_US'].sum()

usdcop_spot = 4200.0
total_absolute_debt = total_emis_saldo + total_oracle_saldo_usd * usdcop_spot

print(f"Total absolute debt COP: {total_absolute_debt}")

# Let's say we have the absolute debt.
# Cost = w_i * total_absolute_debt * rate_i
# int_pct_gdp = Cost / (PIB * scale_factor)

# But wait, the issue says:
# "Intereses internos: 694,651,132.90
# Intereses externos: 138,422,226.58"
# This means the target internal cost is exactly 694,651,132.90.
# The target external cost is exactly 138,422,226.58.
# And target total is 833,073,359.49.
# If we replace debt_pct_gdp with (total_absolute_debt / pib) and it doesn't match?
# Let's calculate: (total_absolute_debt / 1998508.0)
print("Total absolute debt / PIB:", total_absolute_debt / 1998508.0)

# If we do cost = total_absolute_debt * weighted_rate
# To get Int/PIB = 41.68%
# Cost / 19985080 = 41.68
# Which means Cost = 833,073,359.49.
