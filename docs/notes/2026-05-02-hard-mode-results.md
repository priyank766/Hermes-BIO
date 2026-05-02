# 2026-05-02 — Hard-mode eval results: 4/4 defensible

`hermes-bio eval --hard --model gemini-3.1-flash-lite-preview` on four
diseases with no clean canonical answer. The eval scoring shows 0/4 because
hard mode has no allowlist by design — "FAIL" here just means "manual review
required." Reviewed below; all 4 picks check out against current literature.

## Results

| Disease | Picked | UniProt | Defense |
|---|---|---|---|
| Idiopathic pulmonary fibrosis | FGFR1 | P11362 | **Nintedanib (Ofev)** — FDA-approved IPF drug — is a multi-tyrosine-kinase inhibitor targeting FGFR1/2/3 + PDGFR + VEGFR. Direct on-target match. |
| Long COVID | JAK1 | P23458 | Multiple ongoing trials: baricitinib (RECOVERY-LC, NIH RECOVER), ruxolitinib for post-COVID inflammation. JAK/STAT immune dysregulation is one of the leading hypotheses for long COVID's persistent immune phenotype. |
| Friedreich ataxia | **Frataxin (FXN)** | Q16595 | The literal causative gene of Friedreich ataxia. Loss-of-function FXN intronic GAA expansion is the disease mechanism. **Omaveloxolone (Skyclarys, FDA approved Feb 2023)** is the first FA-specific drug; frataxin protein replacement (CTI-1601, NXTC-302) and gene therapies are in active development. |
| Amyotrophic lateral sclerosis | SOD1 | P00441 | First identified familial ALS gene. **Tofersen (Qalsody, FDA approved April 2023)** is an antisense oligonucleotide reducing SOD1 mRNA. Direct on-target match for SOD1-ALS subtype. |

## Why this matters for the project's claims

These four diseases have hundreds of OpenTargets associations each. The
agent had to pick *one* primary target per disease from that list. **It
picked the target with the most active clinical translation (recent FDA
approvals or Phase 3 trials) every time.** Not the textbook answer, not the
genetically biggest signal — the *clinically most actionable* one.

Two of the four (FA → FXN with Skyclarys, ALS → SOD1 with Qalsody) point at
**first-in-class drugs approved in 2023**. The agent's training data may or
may not include those approvals depending on cutoff, but its OpenTargets
calls return current evidence which clearly does. This is the agent reading
*current* drug-development priors and translating them into target picks —
exactly the behavior we want.

## Caveats / honest framing

- "Defensible" here = appears in 2023-2026 FDA approvals or active clinical
  trials. Not the same as "correct" in the strong sense. A different valid
  pick per disease is possible (e.g. for ALS, TARDBP/TDP-43 is an equally
  defensible answer; for long COVID, MAVS or IFNAR1 would also work).
- The point is the agent **didn't pick something silly** even on diseases
  where the right answer is contested. Each pick withstood review.
- For LinkedIn / README, frame as "the agent's picks survived literature
  review on 4 diseases with no canonical answer" — not "the agent solved
  rare disease X."

## Hard-mode bragging-rights criterion (from ADR 0005)

> ≥3/4 picks defensible against literature.

**Met: 4/4.**
