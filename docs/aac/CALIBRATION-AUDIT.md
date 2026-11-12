# W4W calibration audit

Population audit of the simplified Woodlot-for-Windows calibration. The published AAC is the target; the all-VRI model solves for one multiplicative THLB factor.

- Built instances audited: **798**
- Median factor: **0.7554**
- Factor range: **0.0183–21.0925**
- 10th–90th percentile: **0.3582–1.5891**
- Within 80–120% of Proxy THLB: **216**
- Method-check cases (factor <0.4 or >2.0): **157**
- Extreme cases (factor <0.25 or >4.0): **50**

## Decision

**v1 remains the population default.** It is a clearcut/oldest-first replica and is appropriate only while a plan's silviculture system is unknown. **v2 is selected per plan** when the plan documents partial cutting or commercial thinning. The portal flags every factor outside the 0.4–2.0 range as **method check**; the factor is a calibration device, not a statutory THLB.

The unresolved cases are a data problem, not a reason to mass-switch the population to v2. A mass v2 run would require a silviculture assumption for every licence, and W0026 is a documented counter-example where v2 is implausible.

## Class counts

| Class | Count |
|---|---:|
| ok | 641 |
| low | 80 |
| high | 27 |
| extreme-low | 32 |
| extreme-high | 18 |

## Lowest factors

| File | Licence | Factor | Net ha | % Proxy THLB | Class |
|---|---|---:|---:|---:|---|
| W1861 | JAYMIE ATKINSON | 0.0183 | 9.3 | 1.9% | extreme-low |
| W1452 | MABEL LLOYD | 0.0349 | 11.6 | 2.5% | extreme-low |
| W0635 | SAIK'UZ FIRST NATION | 0.0650 | 20.5 | 5.0% | extreme-low |
| W0019 | AHOUSAHT FIRST NATION | 0.1138 | 26.2 | 19.2% | extreme-low |
| W2092 | ATLI RESOURCES LIMITED PARTNERSHIP | 0.1406 | 111.0 | 16.9% | extreme-low |
| W1955 | TYLER KOHNKE | 0.1503 | 221.2 | 18.1% | extreme-low |
| W1805 | AARON HERRICK | 0.1574 | 100.5 | 17.5% | extreme-low |
| W1741 | LEONARD ABLITT | 0.1637 | 129.2 | 21.1% | extreme-low |
| W0636 | 275737 BRITISH COLUMBIA LTD. | 0.1699 | 36.7 | 8.8% | extreme-low |
| W1562 | STARBIRD TIMBER LTD. | 0.1734 | 94.5 | 21.3% | extreme-low |
| W1457 | 1382062 B.C. LTD. | 0.1746 | 102.4 | 21.1% | extreme-low |
| W0550 | LONGWORTH VENTURES LTD. | 0.1783 | 109.6 | 21.1% | extreme-low |
| W1619 | JUSTIN ARMSTRONG | 0.1789 | 84.5 | 16.6% | extreme-low |
| W1766 | 1470812 B.C. LTD. | 0.1980 | 112.0 | 25.0% | extreme-low |
| W1626 | ROSS FREER | 0.2043 | 125.4 | 27.3% | extreme-low |

## Highest factors

| File | Licence | Factor | Net ha | % Proxy THLB | Class |
|---|---|---:|---:|---:|---|
| W1755 | DEREK BLACKWELL | 21.0925 | 1,262.4 | 708.3% | extreme-high |
| W0599 | CLARKE SAUGSTAD | 7.8864 | 1,815.1 | 367.0% | extreme-high |
| W1797 | PINE PLATEAU HOLDINGS LTD. | 6.7285 | 787.6 | 173.1% | extreme-high |
| W0271 | 580521 B.C. LTD. | 6.4013 | 1,010.2 | 241.6% | extreme-high |
| W0700 | LARRY BUFF | 5.7126 | 350.8 | 92.6% | extreme-high |
| W0187 | GARY BLACKWELL | 5.6800 | 475.1 | 171.0% | extreme-high |
| W1531 | LIAM CLOVIS | 5.4363 | 930.4 | 222.4% | extreme-high |
| W1893 | ROBERT MACDOUGALL | 5.4211 | 938.9 | 238.9% | extreme-high |
| W0289 | GAYLON MCKEE | 5.1683 | 989.5 | 218.7% | extreme-high |
| W0027 | 1341316 B.C. LTD. | 5.0571 | 346.7 | 634.6% | extreme-high |
| W1678 | 0928548 B.C. LTD. | 4.9397 | 1,881.8 | 160.6% | extreme-high |
| W1601 | JENNIFER GARTHWAITE | 4.7118 | 723.0 | 151.6% | extreme-high |
| W1710 | NORMAN AVISON | 4.6805 | 1,412.6 | 323.9% | extreme-high |
| W0640 | BENJAMIN HOY | 4.6589 | 622.3 | 156.3% | extreme-high |
| W0649 | PINE MEADOWS CONTRACTING LTD. | 4.6066 | 755.4 | 182.6% | extreme-high |

## v2 cases

| File | Licence | v1 factor | v1 net ha | v2 factor | v2 net ha |
|---|---|---:|---:|---:|---:|
| W0026 | CHINOOK WOODLOTS LTD. | 0.9022 | 660.8 | 3.9313 | 2,879.6 |
| W1832 | WINLAW CREEK WOODLOT LTD. | 0.2156 | 105.3 | 0.8509 | 415.7 |

## Interpretation

- Factors below 0.4 usually mean the clearcut model overestimates sustainable yield for the published AAC, often because the plan uses partial cutting, has a high non-timber constraint, or has a small AAC.
- Factors above 2.0 usually mean the public VRI fragment/yield curve underestimates the local land base or the AAC includes area not in the compiled fragments.
- Do not interpret either tail as a THLB estimate without the local management plan.

Full CSV: [`CALIBRATION-AUDIT.csv`](CALIBRATION-AUDIT.csv).
