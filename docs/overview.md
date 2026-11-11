# Overview

The project gives every active BC woodlot licence a public-data planning
workspace. It follows the same reproducible chain as the BCCFA community forest
portal:

1. catalog the public licence boundary and AAC;
2. clip VRI and the Provincial Proxy THLB to the licence;
3. build natural and managed yield curves through FEMIC / VDYP / TIPSY;
4. compile a WS4 dataset;
5. run a non-declining AAC search and baseline simulation;
6. build a first-period FHOPS operational pilot;
7. serve the whole set through a multi-instance portal.

## Current scope

- **845** active woodlot licences catalogued from the public Forest Tenure
  Managed Licence layer.
- **798** have a public AAC in the March 2026 issued-tenure report.
- **47** are catalogued with AAC pending.
- Batch builds, repairs, and FHOPS runs are resumable through the queue in
  `queue/woodlot_build_queue.json`.

## What is in the portal

- province map and searchable licence cards;
- per-licence WS4 Map and Plan tabs;
- three saved scenarios per built instance (baseline, high, conservative);
- FHOPS first-period operational summary;
- Sources & methods, Terms, and Privacy pages.

## Important caveats

The Proxy THLB is a strategic estimate, not the statutory TSR THLB. The public
AAC is a legal/administrative number, not a model output. The WS4 model uses a
factor-weighted `pthlb_fact` split; the AAC may include private-land (Schedule A)
volume that is not represented in the Crown THLB. Do not interpret the portal's
per-hectare harvest as the AAC's MAI.
