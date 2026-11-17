import unittest

from utils.phylo.precheck import evaluate_phylo_eligibility


# Thresholds mirroring config (kept local so the test is independent of deployment config).
WHOLE_GENOME_MIN = 10000
MIN_LENGTH = 3000
MIN_TIPS = 4
MAX_SEQUENCES = 200


class EvaluatePhyloEligibilityTest(unittest.TestCase):

    def evaluate(self, lengths):
        return evaluate_phylo_eligibility(
            lengths,
            whole_genome_min=WHOLE_GENOME_MIN,
            min_length=MIN_LENGTH,
            min_tips=MIN_TIPS,
            max_sequences=MAX_SEQUENCES,
        )

    def test_counts_split_by_length_tier(self):
        # Two whole genomes, four of any usable length, one below the minimum.
        result = self.evaluate([11000, 10500, 5000, 4000, 2000])
        self.assertEqual(result["n_selected"], 5)
        self.assertEqual(result["n_whole_genome"], 2)
        self.assertEqual(result["n_any_length"], 4)
        self.assertTrue(result["can_generate"])

    def test_too_few_usable_sequences_blocks_tree(self):
        result = self.evaluate([11000, 10500, 4000])
        self.assertFalse(result["can_generate"])
        self.assertIn("At least 4 sequences", result["reason"])

    def test_too_many_sequences_blocks_tree(self):
        result = self.evaluate([5000] * (MAX_SEQUENCES + 1))
        self.assertFalse(result["can_generate"])
        self.assertIn(f"limit {MAX_SEQUENCES}", result["reason"])

    def test_non_numeric_lengths_are_ignored(self):
        # Coercion drops unparseable lengths rather than raising.
        result = self.evaluate([11000, "n/a", 4000, 3500, 3200])
        self.assertEqual(result["n_selected"], 5)
        self.assertEqual(result["n_any_length"], 4)


if __name__ == "__main__":
    unittest.main()
