# Prerequisites

Concepts a contributor needs in order to read this dashboard. This file does not teach them.

---

## Arboviruses in this project

The dashboard visualises arboviruses. Each registered pathogen (`src/pathogens.py`) has its own metadata table and page. Classification axes (serotype, genotype, lineage, or a single genotype axis) are declared on that spec, not hardcoded in the shared layout.

**References:** [WHO: vector-borne diseases](https://www.who.int/news-room/fact-sheets/detail/vector-borne-diseases)

---

## Serotype, genotype, and lineage

Some arboviruses are coloured by more than one classification axis. Dengue is the current example: four antigenically distinct serotypes (DENV1–4), each subdivided into genotypes, and genotypes further split into major and minor lineages for finer spatial-temporal resolution. Lineage labels may be offered as tree colour-by options without being a dashboard filter.

**References:** [Hill et al., PLOS Biology: dengue lineage nomenclature](https://doi.org/10.1371/journal.pbio.3002834)

---

## Unresolved classifications

Values the palette does not name are shown as `Unassigned` so they remain visible on the map and charts. Current genotype vocabularies live on each pathogen spec; do not copy them into new pages by hand.

---

## GenBank accession IDs

Nucleotide records are identified by accession IDs (for example `FJ850076.1`). In this dashboard they are the join key between epidemiological metadata and tree tips. Tip labels on a Newick tree are these accessions, not isolate names.

**References:** [GenBank overview](https://www.ncbi.nlm.nih.gov/genbank/)

---

## Genomic surveillance metadata

The dashboard does not store sequence bytes. It displays metadata already present in MySQL (collection date, country, host, length, serotype/genotype). Records without a collection date are dropped. Sequence counts on the map reflect publicly available genomes, not incidence.

---

## Phylogenetic trees, Newick, and time trees

A phylogenetic tree estimates evolutionary relationships among sequences. **Newick** encodes topology and branch lengths as text. In this dashboard a completed job may carry two trees that must not be swapped: a substitution tree (branch lengths in substitutions per site; this is the only tree with branch support) and a TreeTime dated tree stored as NEXUS (branch lengths in years; the x-axis is a calendar). The dated tree is often a subset of the substitution tips, because TreeTime drops undated sequences and clock-filter outliers.

**References:** [Newick format (PHYLIP)](https://phylipweb.github.io/phylip/newicktree.html); Sagulenko, Puller & Neher (2018) *Virus Evolution*, [TreeTime](https://pmc.ncbi.nlm.nih.gov/articles/PMC5758920/)
