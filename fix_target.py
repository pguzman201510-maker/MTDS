import re

with open("mtds_2026_v2 (1).py", "r") as f:
    code = f.read()

# Ah! p.get("gdp_cop_bn", 1998508.0) returns 1300.0 from the template!!
# Because in template the gdp is 1300.0!
# And it's dividing 833073359.49 / 1300.0 / 10 = 64082.56 !!!
# The instruction says: "respetando el PIB base de 1998508.0."
# So we should just hardcode the target calculation to 1998508.0 !!

target = """    # Percentage is target / GDP / 10.
    p["target_int_pct_gdp"] = 833073359.49 / p.get("gdp_cop_bn", 1998508.0) / 10"""

replacement = """    # Percentage is target / GDP / 10.
    # Instruction specifies to respect base GDP of 1998508.0
    p["target_int_pct_gdp"] = 833073359.49 / 1998508.0 / 10"""

if target in code:
    code = code.replace(target, replacement)
    with open("mtds_2026_v2 (1).py", "w") as f:
        f.write(code)
    print("Fixed target gdp division")
else:
    print("Could not find target")
