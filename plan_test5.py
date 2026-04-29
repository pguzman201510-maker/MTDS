# The user wants to:
# "Utilices la suma de los saldos absolutos y los cupones extraídos directamente de Oracle y Emisiones Vigentes para generar el Costo Total, escalándolo de manera que los resultados de "Intereses/PIB (base)" reflejen con precisión este 41.68% objetivo."

# This means:
# 1. Read absolute internal cost directly: `raw_int_cost = sum(Saldo * Tasa / 100)`
# 2. Read absolute external cost directly: `raw_ext_cost_usd = sum(SDO_US * MARGEN_VALOR / 100)`
# 3. Scale them to the specific target values: 694,651,132.90 and 138,422,226.58.
# Wait! Can we extract the exact target values using some logic?
# In Emisiones Vigentes, the "Suma de Valor Nominal $" column might be different?
# What if the values are just scaled by a factor of 1,000,000?

# Let's see: target total is 833,073,359.49. GDP is 1,998,508.0.
# So percentage = 833,073,359.49 / 1,998,508.0 / 10 = 41.6847.
# We want to change the formula for `int_pct_gdp` in deterministic_cost and `CostRiskCalc` to reflect this base portfolio absolute cost.
# BUT deterministic_cost evaluates hypothetical weights `w`.
# If `w` is the array of proportions, how does it compute the total interest?
# The target 833,073,359.49 corresponds to the "base" portfolio (ref. Act.), which is `w_base`.
# If the portfolio changes to `w`, the cost should change proportionally!
# `total_debt` = absolute total debt.
# Cost = total_debt * weighted_rate
# Scaling factor = target_base_cost / (total_debt * base_weighted_rate)
