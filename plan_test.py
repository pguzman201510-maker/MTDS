# If we change `int_pct_gdp` in deterministic_cost to:
# total_absolute_cost = sum(w[i] * Absolute_cost_i ...)
# The issue explicitly mentions:
# "Elimines los factores 'hardcodeados' y el uso de proporciones genéricas (como el 55.0% de debt_pct_gdp) en la fórmula final. Utilices la suma de los saldos absolutos y los cupones extraídos directamente de Oracle y Emisiones Vigentes para generar el Costo Total, escalándolo de manera que los resultados de "Intereses/PIB (base)" reflejen con precisión este 41.68% objetivo."

# If we extract absolute total cost from Emisiones Vigentes + Oracle, we can pass it via `p` dict.
# e.g., in `main()` we calculate:
# internal_absolute_interest = sum of (Saldo * Tasa / 100) from Emisiones Vigentes.
# external_absolute_interest = sum of (SDO_US * MARGEN_VALOR / 100) from Oracle * usd_cop_spot (maybe we don't multiply by spot? Wait, the target numbers in the issue are:
# Intereses internos: 694,651,132.90
# Intereses externos: 138,422,226.58
# The prompt literally gives us the absolute values we should match!

# We can just say:
# If the target is exactly 41.68%, and the real amount is 833,073,359.49,
# total_cost = 694,651,132.90 + 138,422,226.58
# To reflect 41.68%, the denominator must be: total_cost / 0.4168 = 1,998,736,467
# The issue states: "respetando el PIB base de 1998508.0"
# (833,073,359.49 / 1998508.0) * X = 41.68.
# So `X = 0.1`.
# Let's verify: 833073359.49 / 1998508.0 / 10 = 41.6847
# And the string to print is `41.6847`.
# If it wants exactly 41.68%, we can format it.
