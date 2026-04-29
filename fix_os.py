import re

with open("mtds_2026_v2 (1).py", "r") as f:
    code = f.read()

# Make sure we don't accidentally shadow module os.
# We imported os inside the try block, let's remove it because os is imported globally!

target = """        # Check if the file exists in the same directory as the script instead of PERFIL_PATH
        import os
        # Fallback to local 'Emisiones Vigentes 03.xlsx' since the absolute path isn't guaranteed"""

replacement = """        # Check if the file exists in the same directory as the script instead of PERFIL_PATH
        # Fallback to local 'Emisiones Vigentes 03.xlsx' since the absolute path isn't guaranteed"""

if target in code:
    code = code.replace(target, replacement)

target2 = """        # Load the oracle CSV which is actually tab separated
        import os
        oracle_path_actual = ORACLE_PATH if os.path.exists(ORACLE_PATH) else 'Consulta Oracle 31-03-2026.xls'"""

replacement2 = """        # Load the oracle CSV which is actually tab separated
        oracle_path_actual = ORACLE_PATH if os.path.exists(ORACLE_PATH) else 'Consulta Oracle 31-03-2026.xls'"""

if target2 in code:
    code = code.replace(target2, replacement2)

with open("mtds_2026_v2 (1).py", "w") as f:
    f.write(code)
