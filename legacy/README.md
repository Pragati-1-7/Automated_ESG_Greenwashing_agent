# legacy/

`v1_data/` holds the ORIGINAL hand-written v1 dataset (12 claims, 20 evidence records, 10 hard
cases, the 4-page GreenLeaf sample PDF and its edge-case PDFs).

It was moved here from `data/` on 2026-10-04 to prove that v2 does not depend on it:
with these files moved, every v2 test and the end-to-end PDF evaluation still pass
(see `verification_pack/proof/`). Only the legacy v1 routes (`/analyze`, `/demo/dataset`),
the Streamlit app and the v1 scripts/tests read from here now.
