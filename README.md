# ABC Reduction Analysis

This repository contains a Quarto analysis of SSC reductions from `maxABC`
using Alaska groundfish risk table scores.

## Contents

- `abc_reduction_analysis.qmd`: source document
- `index.html`: published GitHub Pages entrypoint
- `.nojekyll`: disables Jekyll processing for the published site

## Publishing

The site is published with GitHub Pages from the `main` branch and the
repository root.

To update the published page after editing the Quarto source:

```sh
quarto render abc_reduction_analysis.qmd
cp abc_reduction_analysis.html index.html
git add abc_reduction_analysis.qmd index.html
git commit -m "Update ABC reduction analysis"
git push
```
