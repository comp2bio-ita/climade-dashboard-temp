"""
Project configuration for the arboviruses dashboard.

Tunable parameters live here (not in .env, which holds credentials only). Group new
values under a section comment; comment a value only when its meaning is not obvious
from the name.
"""

# --- Phylo pre-check (sequence-length completeness tiers) ---
# Completeness is decided by sequence length, not GenBank's is_complete annotation. These mirror
# the authoritative thresholds in the backend (dash_infra .../phylo_module/config.py) and must be
# kept in sync, since the two repos share no code — only the MySQL database.
WHOLE_GENOME_MIN_LENGTH = 10000   # "complete genomes only" tier (dengue genome ~10.7 kb)
MIN_SEQUENCE_LENGTH = 3000        # "any length" floor; shorter sequences are unusable

# Mirrors the backend's MAX_SEQUENCES guard (dash_infra .../phylo_module/config.py)
MAX_SEQUENCES = 1000       # too many tips makes MAFFT/FastTree impractical in the request path

MIN_TREE_TIPS = 4         # below 4 sequences a tree has no meaningful topology

# --- Phylo job polling ---
PHYLO_POLL_MS = 2000      # how often the dashboard polls phylo_tb for a queued job's status
