#!/usr/bin/env python
"""Tree data model used by every layout and renderer.

Independent of Biopython after parse. Traversals are iterative so deep
ladder-shaped trees do not hit the recursion limit.
"""


from dataclasses import dataclass, field


@dataclass(eq=False)
class TreeNode:
    """A single node (tip or internal) of a phylogenetic tree.

    Identity is by object, never by value: two distinct tips may legitimately
    carry the same name, so `eq=False` keeps them hashable and distinguishable.

    Attributes
    ----------
    id
        Stable index assigned at parse time. Layouts key their coordinate
        dictionaries on this, so it must not change after construction.
    name
        Tip label. Never empty — unnamed tips get a synthetic ``tip_<id>``.
    branch_length
        Length of the branch leading *to* this node. In a substitution tree
        this is substitutions per site; in a TreeTime timetree it is **years**.
        Missing lengths are 0.0.
    support
        Legacy alias for ``support_sh_alrt`` (SH-aLRT). Prefer the explicit fields.
    support_sh_alrt
        SH-aLRT support (0–100) from IQ-TREE internal labels.
    support_ufboot
        Ultrafast bootstrap (0–100) when IQ-TREE writes ``SH-aLRT/UFBoot``.
    date
        Decimal calendar year for this node, present only on a dated tree
        (TreeTime writes one on every node). None otherwise.
    n_mutations
        How many substitutions TreeTime inferred on the branch leading to this
        node. None on an undated tree.

    The field annotations below are what `@dataclass` builds the fields from,
    so they stay; they are structure, not documentation.
    """

    id: int
    name: str = ""
    branch_length: float = 0.0
    support: float = None
    support_sh_alrt: float = None
    support_ufboot: float = None
    date: float = None
    n_mutations: int = None
    children: list = field(default_factory=list)
    parent: object = None

    @property
    def is_tip(self):
        return not self.children

    @property
    def is_root(self):
        return self.parent is None

    def __repr__(self):  # pragma: no cover - debugging aid
        kind = "tip" if self.is_tip else f"node[{len(self.children)}]"
        return f"<TreeNode {self.id} {kind} {self.name!r} bl={self.branch_length:g}>"


class PhyloTree:
    """A rooted phylogenetic tree with pre-computed traversal orders.

    Construction walks the tree twice (once to order the nodes, once to measure
    depth) and caches the results, because every layout needs the same
    traversals and the same tip ordering.
    """

    def __init__(self, root):
        self.root = root
        self._preorder = _iter_preorder(root)
        # Post-order is pre-order reversed *only* if children are also reversed;
        # doing it explicitly is clearer and still O(n).
        self._postorder = list(reversed(_iter_preorder(root, reverse_children=True)))
        self.tips = [n for n in self._preorder if n.is_tip]
        self.internal_nodes = [n for n in self._preorder if not n.is_tip]
        self._depths = self._compute_depths()

    # ── Traversal ──────────────────────────────────────────────────────────

    def preorder(self):
        """Root first, then each subtree. Use when a parent's value feeds its children."""
        return self._preorder

    def postorder(self):
        """Children before parents. Use when aggregating child values upward."""
        return self._postorder

    def __iter__(self):
        return iter(self._preorder)

    def __len__(self):
        return len(self._preorder)

    # ── Metrics ────────────────────────────────────────────────────────────

    @property
    def n_tips(self):
        return len(self.tips)

    @property
    def n_nodes(self):
        return len(self._preorder)

    def depth(self, node):
        """Cumulative branch length from the root to `node` (root excluded)."""
        return self._depths[node.id]

    @property
    def depths(self):
        return self._depths

    @property
    def max_depth(self):
        """Deepest root-to-tip distance. 0.0 when the tree has no branch lengths."""
        return max(self._depths.values(), default=0.0)

    def has_branch_lengths(self):
        """False for a pure cladogram, where every branch length is zero/absent."""
        return any(n.branch_length for n in self._preorder if not n.is_root)

    def has_support(self, metric=None):
        if metric == "ufboot":
            return any(n.support_ufboot is not None for n in self.internal_nodes)
        if metric == "sh_alrt":
            return any(n.support_sh_alrt is not None for n in self.internal_nodes)
        return any(
            n.support_sh_alrt is not None or n.support_ufboot is not None
            for n in self.internal_nodes
        )

    def has_dates(self):
        """True for a dated tree (a TreeTime timetree), false for a substitution tree.

        Only the root is checked, because that is the one date the time axis
        needs: on a TreeTime tree every node is dated, and a tree where only
        some nodes carry a date cannot be placed on a calendar axis anyway.
        """
        return self.root.date is not None

    @property
    def root_date(self):
        """Decimal calendar year of the root, or None on an undated tree.

        On a timetree every node's depth is its age in years relative to the
        root, so this is the offset that converts depth into a calendar date.
        """
        return self.root.date

    def levels(self):
        """Node id -> number of edges from the root. Used for cladogram layout."""
        out = {self.root.id: 0}
        for node in self._preorder:
            for child in node.children:
                out[child.id] = out[node.id] + 1
        return out

    def tip_labels(self):
        return [t.name for t in self.tips]

    def find_tips(self, labels):
        """Tips whose name is in `labels`. Handles duplicate labels correctly."""
        wanted = set(labels)
        return [t for t in self.tips if t.name in wanted]

    def _compute_depths(self):
        depths = {self.root.id: 0.0}
        for node in self._preorder:
            base = depths[node.id]
            for child in node.children:
                depths[child.id] = base + child.branch_length
        return depths


def _iter_preorder(root, reverse_children=False):
    """Iterative pre-order walk.

    `reverse_children` flips sibling order, which is what lets us build a true
    post-order by reversing the result (children of a node come out in their
    original left-to-right order once reversed).
    """
    out = []
    stack = [root]
    while stack:
        node = stack.pop()
        out.append(node)
        children = node.children if reverse_children else reversed(node.children)
        stack.extend(children)
    return out


def _tip_names_below(node):
    if node.is_tip:
        return frozenset([node.name])
    names = set()
    stack = list(node.children)
    while stack:
        child = stack.pop()
        if child.is_tip:
            names.add(child.name)
        else:
            stack.extend(child.children)
    return frozenset(names)


def copy_support_from(source, target):
    """Copy IQ-TREE support values onto ``target`` by matching descendant tip sets."""
    support_by_clade = {}
    for node in source.internal_nodes:
        support_by_clade[_tip_names_below(node)] = (
            node.support_sh_alrt, node.support_ufboot,
        )
    for node in target.internal_nodes:
        metrics = support_by_clade.get(_tip_names_below(node))
        if metrics is None:
            continue
        node.support_sh_alrt, node.support_ufboot = metrics
        node.support = node.support_sh_alrt
