import re

with open("mtds_2026_v2 (1).py", "r") as f:
    code = f.read()

target = """    log_print(f"  Intereses/PIB (base):        {stress['base']['int_pct_gdp']:.3f}%")
    log_print(f"  CVaR 95%:                    {mc['cvar95']:.3f}%")"""

replacement = """    log_print(f"  Intereses absolutos totales: ${p['raw_base_cost_cop']:,.2f} COP")
    log_print(f"  Intereses/PIB (base):        {stress['base']['int_pct_gdp']:.3f}%")
    log_print(f"  CVaR 95%:                    {mc['cvar95']:.3f}%")"""

if target in code:
    code = code.replace(target, replacement)
    with open("mtds_2026_v2 (1).py", "w") as f:
        f.write(code)
    print("Added absolute metrics to PDF logic")
else:
    print("Could not find PDF target")
