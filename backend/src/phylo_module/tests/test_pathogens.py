import unittest

from models.database_models import (
    ChikungunyaMetaEntity,
    DengueMetaEntity,
    ZikaMetaEntity,
)
from phylo_module.pathogens import canonical_pathogen, meta_entity_for


class MetaEntityResolutionTest(unittest.TestCase):
    def test_each_who_abbreviation_resolves_to_its_metadata_table(self):
        self.assertIs(meta_entity_for("DENV"), DengueMetaEntity)
        self.assertIs(meta_entity_for("CHIKV"), ChikungunyaMetaEntity)
        self.assertIs(meta_entity_for("ZIKV"), ZikaMetaEntity)

    def test_rows_written_with_the_full_name_still_resolve(self):
        # phylo_tb holds 16 rows written as "dengue" before the column settled on WHO form;
        # their trees must stay reusable
        self.assertIs(meta_entity_for("dengue"), DengueMetaEntity)
        self.assertIs(meta_entity_for("chikungunya"), ChikungunyaMetaEntity)
        self.assertIs(meta_entity_for("zika"), ZikaMetaEntity)

    def test_case_and_surrounding_space_do_not_matter(self):
        self.assertIs(meta_entity_for("denv"), DengueMetaEntity)
        self.assertIs(meta_entity_for("  Denv "), DengueMetaEntity)
        self.assertIs(meta_entity_for("Dengue"), DengueMetaEntity)

    def test_canonical_form_is_the_who_abbreviation(self):
        self.assertEqual(canonical_pathogen("dengue"), "DENV")
        self.assertEqual(canonical_pathogen("DENV"), "DENV")
        self.assertEqual(canonical_pathogen("chikungunya"), "CHIKV")
        self.assertEqual(canonical_pathogen("zika"), "ZIKV")


class UnregisteredPathogenTest(unittest.TestCase):
    def test_an_unknown_pathogen_names_itself_and_the_registry(self):
        with self.assertRaises(ValueError) as raised:
            meta_entity_for("WNV")
        message = str(raised.exception)
        self.assertIn("WNV", message)
        self.assertIn("pathogens.py", message)

    def test_a_job_without_a_pathogen_says_so(self):
        for missing in (None, "", "   "):
            with self.assertRaises(ValueError) as raised:
                meta_entity_for(missing)
            self.assertIn("pathogen", str(raised.exception))


if __name__ == "__main__":
    unittest.main()
