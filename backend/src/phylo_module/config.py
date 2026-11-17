"""Pipeline knobs in code (credentials stay in .env). Comment only non-obvious values."""

# --- Request limits ---

# Placeholder cap; tune after local MAFFT/FastTree benchmarks
MAX_SEQUENCES = 1000

# Build still runs; warn when below this tip count
MIN_TREE_SEQUENCES = 4

# --- Sequence quality (length-based completeness) ---

# Length tiers, not GenBank is_complete
WHOLE_GENOME_MIN_LENGTH = 10000   # "complete genomes only" tier
MIN_SEQUENCE_LENGTH = 3000        # "any length" floor; shorter sequences are unusable

# --- Job watcher ---

WATCHER_POLL_SECONDS = 5

# --- Cache identity ---

# Bump to invalidate cached trees after tool upgrades
PIPELINE_CACHE_VERSION = 1

# --- Inference ---

# Fallback when job row has no inference_method
INFERENCE_METHOD = "FastTree"

# --- Entrez (GenBank) FASTA fetch ---

ENTREZ_BATCH_SIZE = 50
ENTREZ_SLEEP_SECONDS = 0.1

# --- External CLI tools (must be on PATH; installed via bioconda, not pip) ---

MAFFT_BIN = "mafft"
MAFFT_ALGORITHM_FLAG = "--auto"   # lets MAFFT pick a strategy for the input size
FASTTREE_BIN = "FastTree"
FASTTREE_NT_FLAG = "-nt"           # nucleotide alignment input

# Hard failure on hang; tune after local benchmarks
MAFFT_TIMEOUT_SECONDS = 3600       # 1 h; guide-tree step scales ~O(N^2)
FASTTREE_TIMEOUT_SECONDS = 3600    # 1 h

# --- IQ-TREE (ML inference; alternative engine to FastTree) ---

IQTREE_BIN = "iqtree2"
IQTREE_SUBST_TYPE = "DNA"           # -st: nucleotide alignments
IQTREE_MODEL = "MFP"                # -m MFP: ModelFinder Plus picks the model per alignment

# Branch-support defaults (the standard profile).
IQTREE_UFBOOT_ENABLED = True        # -B: ultrafast bootstrap
IQTREE_UFBOOT_REPLICATES = 1000
IQTREE_SHALRT_ENABLED = True        # -alrt: SH-aLRT test
IQTREE_SHALRT_REPLICATES = 1000
# -bnni only with UFBoot; opt-in (enhanced profile)
IQTREE_BNNI_ENABLED = False

# Fixed seed for reproducible reruns
IQTREE_SEED = 12345

# Threading and memory. -T AUTO lets IQ-TREE pick a core count up to -ntmax.
IQTREE_THREAD_MODE = "AUTO"         # -T
IQTREE_NTMAX = 8                    # -ntmax: upper bound on auto-detected threads
IQTREE_MEMORY_LIMIT = "8G"          # -mem: hard RAM ceiling; empty/None disables the flag

# On timeout leave tree.ckp.gz for manual resume
IQTREE_TIMEOUT_SECONDS = 3600       # 1 h

# Server-side clamps on per-job overrides
IQTREE_MAX_UFBOOT_REPLICATES = 10000
IQTREE_MAX_SHALRT_REPLICATES = 10000
IQTREE_MAX_NTMAX = 16

# --- TreeTime (temporal / molecular-clock stage) ---

TREETIME_ENABLED = True
TREETIME_BIN = "treetime"

TREETIME_REROOT = "least-squares"

# Clock-filter IQR threshold; 0 disables
TREETIME_CLOCK_FILTER = 4
TREETIME_CLOCK_FILTER_METHOD = "residual"

TREETIME_BRANCH_LENGTH_MODE = "auto"

# Keep polytomies; do not invent topology from dates
TREETIME_KEEP_POLYTOMIES = True

# Fixed seed for reproducible reruns
TREETIME_SEED = 12345

TREETIME_TIMEOUT_SECONDS = 3600

# Min temporal signal before dating (vs substitution-tree tips)
TREETIME_MIN_DATED_SEQUENCES = 10
TREETIME_MIN_DATED_FRACTION = 0.5
