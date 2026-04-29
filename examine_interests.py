import pandas as pd

pib_base = 1998508.0  # en billones? 1998508.0 bn COP = 1998.508 trillion COP... wait.
# Oh, the issue description says: "respetando el PIB base de 1998508.0."
# Intereses internos: 694,651,132.90
# Intereses externos: 138,422,226.58
# Interés total: 833,073,359.49
# Interés/GDP = 41.68%
# 833073359.49 / 1998508.0 * 100 = 41684.7...
# 833073359.49 / 1998508000.0 = 41.68%. Ah! GDP is 1,998,508,000.0 maybe?
# The issue says: "Asegures que las métricas finales que se imprimen en consola y se guardan en los reportes correspondan fielmente a la carga real del portafolio, respetando el PIB base de 1998508.0"
# Also:
# Intereses internos: 694,651,132.90
# Intereses externos: 138,422,226.58

# Let's check how to get 694,651,132.90 from the internal file.
# and 138,422,226.58 from the external file.
emis = pd.read_excel('Emisiones Vigentes 03.xlsx')
emis['Suma de SALDO'] = pd.to_numeric(emis['Suma de SALDO'], errors='coerce').fillna(0)
emis['TASA'] = pd.to_numeric(emis['TASA'], errors='coerce').fillna(0)

# If we multiply TASA by 100, or something?
print("Emis total * TASA:", (emis['Suma de SALDO'] * emis['TASA']).sum() / 1e6)
# wait, what if SALDO is already in millions or something?
# emis sum(SALDO * TASA) = 4,487,334,326,671,000.0
# what if TASA is in % and we divide by 100 ?
# 44,873,343,266,710.0
# Still doesn't match 694,651,132.90

oracle = pd.read_csv('Consulta Oracle 31-03-2026.xls', sep='\t', encoding='utf-8')
oracle['MARGEN_VALOR'] = pd.to_numeric(oracle['MARGEN_VALOR'], errors='coerce').fillna(0)
oracle['SDO_US'] = pd.to_numeric(oracle['SDO_US'], errors='coerce').fillna(0)

# What if we need to convert to COP?
# TRM from the script is around 4200.
# oracle_usd_interest = 3396142298.64
print("Oracle external USD interest:", 3396142298.64)
print("With TRM 4200:", 3396142298.64 * 4200)
