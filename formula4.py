import sys
import os
sys.path.append(os.getcwd())

import mtds_script as ms

ms.ORACLE_PATH = "Consulta Oracle 31-03-2026.xls"
ms.TEMPLATE_PATH = "MTDS_Bloomberg_Template.xlsx"
ms.PERFIL_PATH = "Perfil de vencimientos 2026.xlsm"

oracle = ms.load_from_oracle(ms.ORACLE_PATH)
tpl = ms.load_from_template(ms.TEMPLATE_PATH)
p = tpl["params"]

print("Original base Int/GDP:")
# Currently, deterministic_cost in `main` produces "Intereses/PIB (base): 3.912%"
# And in the prompt, the user complains:
# "el cálculo de 'Intereses/PIB (base)' en el script mtds_2026_v2 (1).py está retornando un valor cercano al 3.841%. Sin embargo, según los flujos proyectados y los saldos reales, el monto absoluto de los intereses es:
# Intereses internos: 694,651,132.90
# Intereses externos: 138,422,226.58
# Interés total: 833,073,359.49"
