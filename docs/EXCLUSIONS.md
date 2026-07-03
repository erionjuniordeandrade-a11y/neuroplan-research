# Explicitly Excluded from the MVP

Each is scoped out **intentionally**, with a reason. Reviewers should read this as
deliberate restraint, not missing features.

- **Any diagnosis, grading, or lesion classification** — diagnostic interpretation.
- **Treatment / surgical-approach recommendations** — no "suggest craniotomy site,"
  no eloquence prediction, no approach ranking.
- **Intraoperative or real-time use** — no navigation, tracking, or OR integration.
- **Deep / skull-base / posterior-fossa targets** — superficial supratentorial only
  (bounds the geometry and the risk) for the MVP.
- **Deformable registration as default** — rigid/affine only unless a specific
  validated need arises.
- **Automatic tractography / functional mapping** — high failure cost, out of scope.
- **Real prospective or institutional patient data** — retrospective de-identified
  public + phantom only.
- **Cloud, PACS write-back, or any network feature** — fully offline.
- **Full segmentation automation** — always human-in-the-loop editing.

Out-of-scope ideas that surface during the build go to
`../handoff/BUILD-LOG.md` → Known Gaps, never into the current step.
