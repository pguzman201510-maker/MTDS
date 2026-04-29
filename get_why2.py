import mtds_script as ms

ms.ORACLE_PATH = "Consulta Oracle 31-03-2026.xls"
ms.TEMPLATE_PATH = "MTDS_Bloomberg_Template.xlsx"
ms.PERFIL_PATH = "Perfil de vencimientos 2026.xlsm"

import pandas as pd
df_oracle = pd.read_csv(ms.ORACLE_PATH, sep='\t', encoding='utf-8')
df_oracle['SDO_US'] = pd.to_numeric(df_oracle['SDO_US'], errors='coerce').fillna(0)
df_oracle['MARGEN_VALOR'] = pd.to_numeric(df_oracle['MARGEN_VALOR'], errors='coerce').fillna(0)
total_oracle_saldo_usd = df_oracle['SDO_US'].sum()
raw_ext_cost_usd = (df_oracle['SDO_US'] * (df_oracle['MARGEN_VALOR'] / 100)).sum()

print("Oracle raw cost:", raw_ext_cost_usd)
