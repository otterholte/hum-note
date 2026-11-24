10 files, 65 s. RMVPE and SwiftF0 agree within 50 cents on 99.9% of the frames both call voiced.

| model | voiced & within ±50c of consensus | within ±20c | octave off | voiced where both refs unvoiced |
|---|---|---|---|---|
| yin_app | 95.2% | 92.9% | 0.1% | 0.2% |
| yin_tuner | 67.5% | 64.6% | 0.0% | 0.4% |
| crepe_tiny | 94.6% | 90.3% | 1.3% | 4.3% |
| crepe_full | 99.2% | 97.6% | 0.2% | 1.8% |
| swiftf0 | 100.0% | 99.9% | 0.0% | 0.0% |
| pesto | 97.8% | 92.2% | 0.0% | 0.0% |
| rmvpe | 100.0% | 99.9% | 0.0% | 0.0% |
| fcpe | 100.0% | 99.6% | 0.0% | 12.4% |

Per file, app YIN vs consensus (voiced & ±50c):

| file | yin_app | yin_tuner | crepe_full |
|---|---|---|---|
| f1_arpeggios_belt_c_a | 97.9% | 94.6% | 99.2% |
| f2_arpeggios_breathy_a | 99.8% | 66.8% | 98.7% |
| f3_arpeggios_vibrato_a | 99.9% | 99.5% | 99.9% |
| f5_arpeggios_c_fast_forte_a | 92.0% | 62.0% | 98.0% |
| f6_long_pp_a | 98.7% | 97.2% | 99.2% |
| m2_arpeggios_vibrato_a | 83.7% | 65.3% | 99.6% |
| m3_arpeggios_c_slow_piano_a | 99.4% | 6.4% | 99.7% |
| m4_arpeggios_c_fast_forte_a | 67.5% | 48.2% | 94.5% |
| m6_arpeggios_breathy_a | 99.9% | 40.3% | 99.4% |
| m8_arpeggios_straight_a | 94.9% | 90.5% | 99.2% |
