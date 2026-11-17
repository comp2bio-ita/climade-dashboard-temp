"""Phylo pre-check from sequence lengths (no Dash/DB)."""

import pandas as pd


def evaluate_phylo_eligibility(
    sequence_lengths,
    whole_genome_min,
    min_length,
    min_tips,
    max_sequences,
):
    # Gate on loosest tier (any length); backend enforces chosen completeness
    lengths = pd.to_numeric(sequence_lengths, errors="coerce")
    n_selected = len(lengths)
    n_whole_genome = int((lengths >= whole_genome_min).sum())
    n_any_length = int((lengths >= min_length).sum())

    eligibility = (
        f"{n_selected} sequence(s) selected; {n_whole_genome} complete genome(s) "
        f"(≥ {whole_genome_min} bp) and {n_any_length} of any usable length "
        f"(≥ {min_length} bp)."
    )

    if n_any_length < min_tips:
        can_generate = False
        reason = (
            f"{eligibility} At least {min_tips} sequences above the minimum length are "
            "needed to build a tree — widen the date range or relax the filters."
        )
    elif n_selected > max_sequences:
        can_generate = False
        reason = (
            f"{eligibility} That is too many to build a tree in the dashboard "
            f"(limit {max_sequences}). Narrow the filter, e.g. fewer countries or a "
            "shorter date range."
        )
    else:
        can_generate = True
        reason = f"{eligibility} Ready to build a tree."

    return {
        "can_generate": can_generate,
        "reason": reason,
        "n_selected": n_selected,
        "n_whole_genome": n_whole_genome,
        "n_any_length": n_any_length,
    }
