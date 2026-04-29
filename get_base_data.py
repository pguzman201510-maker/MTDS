import sys
import os
import numpy as np

sys.path.append(os.getcwd())
import mtds_script as ms

ms.ORACLE_PATH = "Consulta Oracle 31-03-2026.xls"
ms.TEMPLATE_PATH = "MTDS_Bloomberg_Template.xlsx"
ms.PERFIL_PATH = "Perfil de vencimientos 2026.xlsm"

oracle = ms.load_from_oracle(ms.ORACLE_PATH)
tpl = ms.load_from_template(ms.TEMPLATE_PATH)
p = tpl["params"]

# Print baseline debt and cost.
print("Oracle OK:", oracle["ok"])
print("Total USD Oracle:", oracle["external_total_usd"])
