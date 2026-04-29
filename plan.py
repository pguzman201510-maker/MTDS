# Look at "Tasa/Spread WP (MARGEN_VALOR)"
# CHF Fija: 1.252%
# EUR Fija: 4.026%
# USD Fija: 4.868%
# And variables...
# So the Oracle actually calculates `tasa_wp` which is used in `p`.

# In `main`, it sets:
# p["usd_fixed_rate"] = oracle_rates["DE_USD_F"]["tasa_wp"]
# And same for spreads...
# So `deterministic_cost` computes the exact weighted rate using the ACTUAL rates from Oracle!

# If `weighted_rate` is the EXACT weighted rate, then:
# "int_pct_gdp = weighted_rate * p['debt_pct_gdp']"
# The problem is `p['debt_pct_gdp']` is a hardcoded generic proportion, like 55.0.

# The user explicitly states:
# "Elimines los factores 'hardcodeados' y el uso de proporciones genéricas (como el 55.0% de debt_pct_gdp) en la fórmula final. Utilices la suma de los saldos absolutos y los cupones extraídos directamente de Oracle y Emisiones Vigentes para generar el Costo Total, escalándolo de manera que los resultados de 'Intereses/PIB (base)' reflejen con precisión este 41.68% objetivo."

# If we change `int_pct_gdp` computation in `deterministic_cost`:
# Instead of `weighted_rate * p["debt_pct_gdp"]`, we can use `weighted_rate * p["total_absolute_debt"] / p["gdp_cop_bn"]`.
# Or maybe the actual formula is just `weighted_rate * p["total_absolute_debt"] / p["gdp_cop_bn"]` scaled so the base is 41.68%.
