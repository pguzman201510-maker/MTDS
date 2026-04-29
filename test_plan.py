import pandas as pd
import numpy as np

def load_emisiones():
    df = pd.read_excel('Emisiones Vigentes 03.xlsx')
    df['Suma de SALDO'] = pd.to_numeric(df['Suma de SALDO'], errors='coerce').fillna(0)
    df['TASA'] = pd.to_numeric(df['TASA'], errors='coerce').fillna(0)
    total_saldo = df['Suma de SALDO'].sum()
    total_interest = (df['Suma de SALDO'] * (df['TASA'] / 100)).sum()
    return total_saldo, total_interest

def load_oracle():
    df = pd.read_csv('Consulta Oracle 31-03-2026.xls', sep='\t', encoding='utf-8')
    df['MARGEN_VALOR'] = pd.to_numeric(df['MARGEN_VALOR'], errors='coerce').fillna(0)
    df['SDO_US'] = pd.to_numeric(df['SDO_US'], errors='coerce').fillna(0)
    total_saldo = df['SDO_US'].sum()
    total_interest = (df['SDO_US'] * (df['MARGEN_VALOR'] / 100)).sum()
    return total_saldo, total_interest

int_saldo, int_interest = load_emisiones()
ext_saldo, ext_interest = load_oracle()

print(f"Internal: Saldo={int_saldo}, Interest={int_interest}")
print(f"External: Saldo={ext_saldo}, Interest={ext_interest}")

# We want internal interest to map to 694651132.90
# external interest to map to 138422226.58
# So we can calculate scaling factors:
scale_int = 694651132.90 / int_interest
scale_ext = 138422226.58 / ext_interest

print(f"Scale Internal: {scale_int}")
print(f"Scale External: {scale_ext}")
