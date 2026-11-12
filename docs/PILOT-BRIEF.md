# Woodlots BC pilot brief

**A free, public-data planning portal for every active BC woodlot licence.**

## What it is

One strategic model and one operational pilot per woodlot, built only from
public data:

```text
845  active woodlot licences catalogued
798  with a public AAC and a built WS4 model
798  with a FHOPS operational pilot and portal page
 47  catalogued while their public AAC is pending
  3  featured woodlots with ten-year tactical–operational plans
  3  featured Tree Lab tree-scale replays
```

## The three featured pilots

| Woodlot | Location | Annual AAC | 10-year tactical plan |
| --- | --- | ---: | ---: |
| W0026 Chinook Woodlots | Campbell River | 7,311 m³/yr | 73,110 m³ · 4 blocks |
| W1548 Fibre Farms | Prince George | 4,000 m³/yr | 40,000 m³ · 2 blocks |
| W2023 Boomer Enterprises | Okanagan | 5,833 m³/yr | 58,330 m³ · 10 blocks |

Each featured pilot has:

- a WS4 strategic model;
- a FHOPS tactical–operational MILP plus ten annual operational seasons;
- a day-by-day 3D harvest studio;
- a tree-scale theatre;
- a Tree Lab replay with synthetic trees inside real block polygons.

## What to try first

1. Open the portal and search for a familiar woodlot.
2. Open the featured W0026 model and check the AAC baseline and land-base
   line.
3. Open the W0026 **10-year plan**, then the **3D block studio**.
4. Open the **Tree Lab** and press play.
5. Read **Sources & methods** and the **How to read this portal** guide.

## What it is not

- Not a statutory timber supply analysis or an AAC determination.
- Not a replacement for a management plan or professional judgment.
- Not a production schedule, cost model, road plan, or silviculture plan.
- The tree lists and machine choreography are illustrative.
- The Proxy THLB is a strategic estimate, not the statutory THLB.

## Access

The pilot is read-only and behind Cloudflare Access:

```text
https://fresh-woodlotsbc.01101.dev
```

Access currently supports OIDC/Globus and email One-time PIN. The OTP email
allowlist is awaiting a Woodlots BC test user.

## Companion documents

- [How to read this portal](HOW-TO-READ.md)
- [10-minute demo script](DEMO-SCRIPT.md)
- [FHOPS pilots](FHOPS.md)
- [Calibration audit](aac/CALIBRATION-AUDIT.md)
- [Tactical validation](TACTICAL-VALIDATION.md)
- [Release notes](RELEASE-NOTES.md)
