# W0026 — Public AAC documentation dossier

**Woodlot licence:** W0026  
**Licensee:** Chinook Woodlots Ltd.  
**Location:** Trent River, Campbell River Natural Resource District  
**Current public AAC:** **7,311 m³/year**  
**Cut-control period:** 2022–2026; cut-control limit 120%  
**Licence issued:** 1987-08-18

## Bottom line

The public record gives the **number** and the **provincial method**, but I could not find the **W0026-specific calculation and assumptions** in a public document.

The Woodlot Licence Plan (WLP) for W0026 explicitly says the sustainable growth rate is calculated in a separate **Management Plan**. That Management Plan is not linked from the current district page and I could not find a public copy. The current district page's W0026 “Plan” link is also broken (404); an archived copy of WLP #1 is available, but it does not contain the AAC calculation.

The missing W0026-specific documents are therefore:

1. the approved **Woodlot Licence W0026 Management Plan** (the document that proposes the AAC);
2. the **Woodlot for Windows project/report** used to calculate the AAC;
3. the **AAC determination and rationale** issued by the district manager;
4. the **Schedule A / Schedule B area and volume allocation** used in the calculation;
5. any management-plan amendments that changed the AAC.

## What is public and verified

### 1. The AAC is 7,311 m³/year

Two independent public records agree:

- **Cut Control Statement, Year End 2024** (issued 2025-05-31), file `19720-70/W0026`:
  - Licence W0026, Campbell River District
  - Period 2022–2026
  - Cut Control Limit 120%
  - Allowable Annual Cut: **7,311 m³** in each year 2022, 2023, 2024, 2025, 2026
  - WL Issued Date: 1987-08-18
- **Issued tenure AAC report** (`ftarpt_f000_file_status_register_mar2026rpt.xls`), row `A04`:
  - `FOREST_FILE_ID = W0026`
  - `CLIENT_NAME = CHINOOK WOODLOTS LTD.`
  - `AAC_TOTAL = 7,311.0`
  - `AREA_TOTAL = 1,110.0`
  - District: Campbell River Natural Resource District

### 2. The WLP points to a separate Management Plan

The archived **Woodlot Licence Plan #1** (2009, 45 pages) says:

> “This WLP provides results and strategies that are connected to the sustainable growth rate calculation derived within the Management Plan, which meet the VILUP objectives.”

It does not state the AAC or the calculation. The WLP is a Forest and Range Practices Act plan; it is not the AAC rationale.

The **2020 WLP extension approval letter** extends the WLP term from 2019 to 2029. It is a plan-approval letter, not an AAC determination.

### 3. The provincial calculation method is public

The Ministry’s **Woodlot for Windows 4.4 User Guide** and **Woodlot Licence Management Plan Handbook** describe the method used to calculate and propose an AAC.

Key points from the User Guide:

- Woodlot for Windows calculates a **non-declining even flow (flat-line) sustainable harvest rate over a 250-year planning horizon**.
- The calculation is iterative: it adjusts the rate up or down until it converges within **1 m³/year**.
- It uses the **harvest priority and harvest order**, harvest parameters and harvest ages, and forest-cover constraints.
- Constraints include **EXCLUDE**, **AREA netdown**, **must be TALLER than**, and **must be OLDER than**; the order is EXCLUDE → AREA netdown → TALLER → OLDER.
- **LRSY** = culmination MAI × net woodlot area.
- **Net woodlot area** = net area × THLB inclusion factor, and is also reduced by “EXCLUDE” constraints.
- Inputs include current inventory and silviculture data (polygon, net area, age, ownership, natural/managed stand, site index, crown closure, volume adjustment, stocking, FIZ, species) and future management assumptions (regeneration delay, utilization, silviculture system, target harvest age, minimum harvest parameters, natural vs. managed yields).
- The report must include “any assumptions or explanations of how variables were selected” for the district manager.

Key points from the Management Plan Handbook:

- A primary purpose of the management plan is to propose an AAC.
- The management plan must propose an AAC for the **Crown land (Schedule B)** portion; it may also propose an AAC for **private land (Schedule A)**.
- All information from both Crown and private portions should be analyzed with the approved version of **Woodlot for Windows**.
- For cut control, there is **one AAC for the entire woodlot licence**, equal to the Crown AAC plus any private-land AAC.
- The district manager determines the AAC; the model is only a tool. If the district manager does not accept the proposed AAC, the determination should explain why.
- Management plans are **not required to be advertised, publicly reviewed, or referred** to other agencies. That is why the W0026-specific plan is not necessarily on the public district page.

### 4. Legal framework

- **Forest Act, s.45(1)(f)(vi)**: a woodlot licence must require the holder to submit a management plan that “proposes an allowable annual cut for the woodlot licence area.”
- **Forest Act, s.8** is the AAC determination authority for woodlots; s.45.1 addresses transition where an AAC has not been determined under s.8.
- **Cut Control Regulation** governs the cut-control period and the 120% limit.
- **Woodlot Licence Regulation** and the woodlot licence agreement govern the management-plan content and AAC process.

## What the public record does **not** contain

- The approved W0026 Management Plan.
- The AAC proposed by the licensee.
- The Woodlot for Windows project file or report.
- The district manager’s AAC determination rationale.
- The Schedule A/B area and volume split used in the 7,311 m³/year calculation.
- The inventory, yield, silviculture, operability, and constraint assumptions specific to W0026.

Without those, the 7,311 m³/year cannot be reproduced or audited from public sources alone.

## Why the number can look high against our model

The public AAC is **7,311 m³/year** on an `AREA_TOTAL` of **1,110 ha**, which is **6.59 m³/ha/year** on the AAC area.

That is not directly comparable with our WS4 managed area:

| Basis | Area | AAC intensity |
|---|---:|---:|
| AAC report `AREA_TOTAL` | 1,110 ha | **6.59 m³/ha/yr** |
| FTEN AOI (our clip) | 1,027.92 ha | 7.11 m³/ha/yr |
| Proxy THLB | 667.38 ha | 10.95 m³/ha/yr |
| WS4 factor-weighted managed area | 449.60 ha | 16.26 m³/ha/yr |

The difference is expected if the AAC includes a private-land (Schedule A) contribution, or if the AAC area and the Proxy THLB use different land-base definitions. The Management Plan would state that split. **Do not treat the 16.26 m³/ha/yr figure as the AAC’s MAI** — it is the AAC divided by a much smaller Crown-only managed area.

## Where to request the missing records

**Campbell River Natural Resource District**  
370 S Dogwood Street  
Campbell River, BC V9W 6Y7  
Tel: 250-286-9300  
Email: Forests.CampbellRiverDistrictOffice@gov.bc.ca

The 2020 WLP extension letter names **Thomas Hartz** (250-850-1762) as the contact and is signed by **Gary Gwilt**, Acting District Manager.

Suggested request:

> Please provide, for Woodlot Licence W0026 (Chinook Woodlots Ltd.):
>
> 1. the approved Woodlot Licence Management Plan, including all amendments;
> 2. the AAC determination and the district manager’s rationale for the current 7,311 m³/year;
> 3. the Woodlot for Windows project file and report used to calculate the AAC;
> 4. the Schedule A (private) and Schedule B (Crown) area and volume allocation used in the AAC;
> 5. the inventory, yield, silviculture, operability, and constraint assumptions used in the calculation.
>
> If these records are available publicly, please provide the links. If not, please treat this as a request under the Freedom of Information and Protection of Privacy Act.

The Ministry’s 2019 Management Plan Handbook also lists **Dave Haley, Woodlot Licence Forester, 250-387-8317** and **Woodlot for Windows support, 250-226-7792 / tomb@netidea.com**; confirm current contacts before using them.

## Documents saved in this dossier

| File | What it is |
|---|---|
| `w0026_letter.pdf` | 2020 WLP extension approval letter (not an AAC determination) |
| `w0026_plan_2022.pdf` | Archived WLP #1 (2009; 45 pages); no AAC calculation |
| `w0026_letter_2018.pdf` | Archived 2009 WLP approval letter (3 pages) |
| `coast_2024_wls_cut_control.pdf` | Cut Control Statement, Year End 2024; includes W0026 AAC 7,311 |
| `../provincial/Woodlot4UserGuide.pdf` | Woodlot for Windows 4.4 User Guide; provincial AAC method |
| `../provincial/woodlot_mngmt_plan_handbook.pdf` | Management Plan Handbook; AAC/management-plan requirements |

Source URLs:

- District page: <https://www2.gov.bc.ca/gov/content/industry/forestry/forest-tenures/timber-harvesting-rights/woodlot-licence/district-woodlot-licences>
- Current W0026 plan link (returns 404): <https://www2.gov.bc.ca/assets/download/70B29B7BA17A497D8439F8755AC4A4D9>
- Archived WLP #1: <https://web.archive.org/web/20220625165158if_/https://www2.gov.bc.ca/assets/gov/farming-natural-resources-and-industry/forestry/timber-tenures/woodlots/district-woodlots/w0026_plan.pdf>
- 2020 WLP extension letter: <https://www2.gov.bc.ca/assets/gov/farming-natural-resources-and-industry/forestry/timber-tenures/woodlots/district-woodlots/w0026_letter.pdf>
- Cut Control Statement: <https://www2.gov.bc.ca/assets/gov/farming-natural-resources-and-industry/forestry/timber-tenures/cut-control-statements/coast_area_2024_wls_ccs_up_to_nov_1_2025.pdf>
- AAC report: <https://www2.gov.bc.ca/assets/gov/farming-natural-resources-and-industry/forestry/timber-tenures/apportionment/ftarpt_f000_file_status_register_mar2026rpt.xls>
- Woodlot for Windows page: <https://www2.gov.bc.ca/gov/content/industry/forestry/forest-tenures/timber-harvesting-rights/woodlot-licence/allowable-annual-cut-calculator-tool>
- User Guide: <https://www.for.gov.bc.ca/ftp/HTH/external/!publish/web/timber-tenures/woodlots/woodlot-for-windows/Woodlot4UserGuide.pdf>
- Management Plan Handbook: <https://www2.gov.bc.ca/assets/gov/farming-natural-resources-and-industry/forestry/timber-tenures/woodlots/woodlot_mngmt_plan_handbook.pdf>
- Forest Act: <https://www.bclaws.gov.bc.ca/civix/document/id/complete/statreg/96157_03>
- Woodlot Licence Regulation: <https://www.bclaws.gov.bc.ca/civix/document/id/complete/statreg/68_2006>
- Cut Control Regulation: <https://www.bclaws.gov.bc.ca/civix/document/id/complete/statreg/17_578_2004>

## Verification note

I inspected the AAC workbook, the cut-control statement, the WLP, the 2020 letter, the 2009 letter, the W4W User Guide, and the Management Plan Handbook. I did **not** find a public W0026 Management Plan or AAC rationale. That is the document to request.
