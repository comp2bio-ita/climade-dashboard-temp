from utils.phylo.viewer.model import copy_support_from, _tip_names_below
from utils.phylo.viewer.parse import parse_newick


class TestCopySupportFrom:
    def test_support_is_matched_by_descendant_tips(
            self, pipeline_newick, timetree_nexus):
        source = parse_newick(pipeline_newick)
        target = parse_newick(timetree_nexus)

        copy_support_from(source, target)

        assert target.has_support("sh_alrt")
        matched = 0
        for node in target.internal_nodes:
            clade = _tip_names_below(node)
            source_node = next(
                (n for n in source.internal_nodes
                 if _tip_names_below(n) == clade and n.support_sh_alrt is not None),
                None,
            )
            if source_node is None:
                continue
            assert node.support_sh_alrt == source_node.support_sh_alrt
            assert node.support_ufboot == source_node.support_ufboot
            matched += 1
        assert matched > 0

    def test_both_metrics_are_copied(self):
        source = parse_newick("((A:0.1,B:0.2)95/98:0.3,C:0.4);")
        target = parse_newick("((A:0.1,B:0.2):0.3,C:0.4);")
        copy_support_from(source, target)
        ab_node = next(
            n for n in target.internal_nodes if _tip_names_below(n) == frozenset({"A", "B"}))
        assert ab_node.support_sh_alrt == 95.0
        assert ab_node.support_ufboot == 98.0
