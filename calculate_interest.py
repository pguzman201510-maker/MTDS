import pandas as pd

# External
oracle = pd.read_csv('Consulta Oracle 31-03-2026.xls', sep='\t', encoding='utf-8')
# Convert MARGEN_VALOR / 100 ? Wait, in percentage?
# SDO_US is in USD? Or in millions?
# Maybe SDO_US is raw USD amount. To convert to COP we need the USD/COP rate? Wait, SDO_US is USD. We need to convert it to COP? Or maybe the interes is sum(SDO_US * MARGEN_VALOR / 100)?
# Let's just print sums to figure it out.
oracle['MARGEN_VALOR'] = pd.to_numeric(oracle['MARGEN_VALOR'], errors='coerce').fillna(0)
oracle['SDO_US'] = pd.to_numeric(oracle['SDO_US'], errors='coerce').fillna(0)

print("Oracle Sum SDO_US * MARGEN_VALOR / 100:", (oracle['SDO_US'] * oracle['MARGEN_VALOR'] / 100).sum())

# Emisiones (Internal)
emis = pd.read_excel('Emisiones Vigentes 03.xlsx')
emis['Suma de SALDO'] = pd.to_numeric(emis['Suma de SALDO'], errors='coerce').fillna(0)
emis['TASA'] = pd.to_numeric(emis['TASA'], errors='coerce').fillna(0)

# Sometimes TASA is in decimals or percentages
print("Emis Sum SALDO * TASA:", (emis['Suma de SALDO'] * emis['TASA']).sum())
print("Emis Sum SALDO * TASA / 100:", (emis['Suma de SALDO'] * emis['TASA'] / 100).sum())
