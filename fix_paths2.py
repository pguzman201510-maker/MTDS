import re

with open("mtds_2026_v2 (1).py", "r") as f:
    code = f.read()

target_oracle = """    try:
        # Load the oracle CSV which is actually tab separated
        df_oracle = pd.read_csv(ORACLE_PATH, sep='\\t', encoding='utf-8')"""

replacement_oracle = """    try:
        # Load the oracle CSV which is actually tab separated
        import os
        oracle_path_actual = ORACLE_PATH if os.path.exists(ORACLE_PATH) else 'Consulta Oracle 31-03-2026.xls'
        df_oracle = pd.read_csv(oracle_path_actual, sep='\\t', encoding='utf-8')"""

if target_oracle in code:
    code = code.replace(target_oracle, replacement_oracle)
    with open("mtds_2026_v2 (1).py", "w") as f:
        f.write(code)
    print("Fixed Oracle path")
