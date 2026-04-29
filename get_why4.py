# The target is exactly 41.68%.
# When I replaced `p["model_base_cost"]`, did I compute `p["model_base_cost"]` with the exact same weights used by `stres_ref = stress_analysis(ref_w, p)`?
# In `main`, `ref_w` is the base portfolio.
# Let's check `p["model_base_cost"]` in the code.

with open('mtds_2026_v2 (1).py', 'r') as f:
    text = f.read()

import re
print("Found model base cost setting:")
print(re.findall(r'p\["model_base_cost"\] = .*', text))
