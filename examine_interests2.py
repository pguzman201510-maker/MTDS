import pandas as pd

oracle = pd.read_csv('Consulta Oracle 31-03-2026.xls', sep='\t', encoding='utf-8')
oracle['MARGEN_VALOR'] = pd.to_numeric(oracle['MARGEN_VALOR'], errors='coerce').fillna(0)
oracle['SDO_US'] = pd.to_numeric(oracle['SDO_US'], errors='coerce').fillna(0)

# The goal for Intereses externos is: 138,422,226.58
print("External sum SDO_US * MARGEN_VALOR:", (oracle['SDO_US'] * oracle['MARGEN_VALOR']).sum())
print("External sum SDO_US * MARGEN_VALOR/100:", (oracle['SDO_US'] * oracle['MARGEN_VALOR'] / 100).sum())

# The target is 138,422,226.58.
# 3396142298.64 is roughly 24 times 138,422,226.58 ? Wait...
print("Ratio:", 3396142298.64 / 138422226.58)

emis = pd.read_excel('Emisiones Vigentes 03.xlsx')
emis['Suma de SALDO'] = pd.to_numeric(emis['Suma de SALDO'], errors='coerce').fillna(0)
emis['TASA'] = pd.to_numeric(emis['TASA'], errors='coerce').fillna(0)

# The goal for Intereses internos is: 694,651,132.90
# Emis total * TASA / 1e6 is 4487334326.671
print("Internal sum SALDO * TASA:", (emis['Suma de SALDO'] * emis['TASA']).sum())
print("Ratio internal:", (emis['Suma de SALDO'] * emis['TASA']).sum() / 694651132.90)
