import re

with open("mtds_2026_v2 (1).py", "r") as f:
    code = f.read()

target = """    try:
        df_emis = pd.read_excel(PERFIL_PATH.replace('Perfil de vencimientos 2026.xlsm', 'Emisiones Vigentes 03.xlsx'))"""

replacement = """    try:
        # Check if the file exists in the same directory as the script instead of PERFIL_PATH
        import os
        # Fallback to local 'Emisiones Vigentes 03.xlsx' since the absolute path isn't guaranteed
        emis_path = PERFIL_PATH.replace('Perfil de vencimientos 2026.xlsm', 'Emisiones Vigentes 03.xlsx')
        if not os.path.exists(emis_path):
             emis_path = 'Emisiones Vigentes 03.xlsx'
        df_emis = pd.read_excel(emis_path)"""

if target in code:
    code = code.replace(target, replacement)
    with open("mtds_2026_v2 (1).py", "w") as f:
        f.write(code)
    print("Fixed Emisiones Vigentes path")

target_oracle = """    try:
        # Load the oracle CSV which is actually tab separated
        df_oracle = pd.read_csv(ORACLE_PATH, sep='\t', encoding='utf-8')"""

replacement_oracle = """    try:
        # Load the oracle CSV which is actually tab separated
        import os
        oracle_path_actual = ORACLE_PATH if os.path.exists(ORACLE_PATH) else 'Consulta Oracle 31-03-2026.xls'
        df_oracle = pd.read_csv(oracle_path_actual, sep='\t', encoding='utf-8')"""

if target_oracle in code:
    code = code.replace(target_oracle, replacement_oracle)
    with open("mtds_2026_v2 (1).py", "w") as f:
        f.write(code)
    print("Fixed Oracle path")
