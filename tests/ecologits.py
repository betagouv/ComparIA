from ecologits.tracers.utils import llm_impacts, compute_llm_impacts, electricity_mixes

electricity_mix_zone = "WOR"
electricity_mix = electricity_mixes.find_electricity_mix(
    zone=electricity_mix_zone
)
if_electricity_mix_adpe = electricity_mix.adpe
if_electricity_mix_pe = electricity_mix.pe
if_electricity_mix_gwp = electricity_mix.gwp

impact = compute_llm_impacts(model_active_parameter_count=16,model_total_parameter_count=56,output_token_count=400,
if_electricity_mix_adpe=if_electricity_mix_adpe,    if_electricity_mix_pe=if_electricity_mix_pe,if_electricity_mix_gwp=if_electricity_mix_gwp)
impact.energy.value * 1000