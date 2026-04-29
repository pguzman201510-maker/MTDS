pib_base = 1998508.0

int_interno = 694651132.90
int_externo = 138422226.58
int_total = 833073359.49

print("Ratio to PIB (internal):", int_interno / pib_base)
print("Ratio to PIB (external):", int_externo / pib_base)
print("Ratio to PIB (total):", int_total / pib_base)
print("Percentage:", (int_total / pib_base) / 10) # 41.68 %
# That means int_total / pib_base = 416.84
# (833073359.49 / 1998508.0) = 416.847
# And the prompt says "Interés/GDP = 41.68%"
# If it's a percentage, then 41.68% means 0.4168...
# Wait, 833073359.49 / 1998508.0 = 416.84... Maybe PIB is in MILLIONS, so 1998508.0 * 1,000 = 1,998,508,000?
# And interests are in MILLIONS as well?
# 833,073,359.49 is 833 million millions? No, it's 833 BILLION.
# So if PIB is 1,998,508 BILLION... wait, 1,998,508,000,000? (1.998 trillion COP = 1.998 billion billion?)
# In Colombia, PIB is around 1,500 billones de pesos (which means 1,500,000,000,000,000, i.e. 1.5 x 10^15 pesos).
# Wait, 1,998,508,000,000,000 COP is ~2,000 billones COP (trillions in English).
# If the interest is 833,073,359,000,000 ?
# The text says "Intereses internos: 694,651,132.90". Maybe these are in thousands of pesos?
# If we just do (int_total / (pib_base * 10)) = 41.68%... wait. 416.84 / 10 = 41.68.
# 416.84 / 1000 = 0.4168, which is 41.68%.
