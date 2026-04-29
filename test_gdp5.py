import pandas as pd
import sys

def get_interest_from_data():
    emis = pd.read_excel('Emisiones Vigentes 03.xlsx')
    emis['Suma de SALDO'] = pd.to_numeric(emis['Suma de SALDO'], errors='coerce').fillna(0)
    emis['TASA'] = pd.to_numeric(emis['TASA'], errors='coerce').fillna(0)

    # Let's say TASA is percentage, so we divide by 100
    int_internal = (emis['Suma de SALDO'] * emis['TASA'] / 100).sum()

    oracle = pd.read_csv('Consulta Oracle 31-03-2026.xls', sep='\t', encoding='utf-8')
    oracle['MARGEN_VALOR'] = pd.to_numeric(oracle['MARGEN_VALOR'], errors='coerce').fillna(0)
    oracle['SDO_US'] = pd.to_numeric(oracle['SDO_US'], errors='coerce').fillna(0)

    int_external_usd = (oracle['SDO_US'] * oracle['MARGEN_VALOR'] / 100).sum()

    return int_internal, int_external_usd

int_in, int_ex = get_interest_from_data()
print("Internal (raw sum):", int_in)
print("External (raw sum):", int_ex)
