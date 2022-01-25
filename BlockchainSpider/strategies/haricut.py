from BlockchainSpider.strategies import PushPopModel


class Haircut(PushPopModel):
    def __init__(self, source, min_weight: float = 1e-3):
        super().__init__(source)
        assert 0 < min_weight < 1
        self.min_weight = min_weight
        self.weight_map = {self.source: 1}
        self._vis = {self.source}

    def push(self, node, edges: list, **kwargs):
        out_sum = 0
        out_edges = list()
        for e in edges:
            if e.get('from') == node:
                out_sum += float(e.get('value', 0))
                out_edges.append(e)

        if out_sum == 0:
            return

        node_weight = self.weight_map.get(node, 0)
        self.weight_map[node] = 0
        for oe in out_edges:
            out_neibor = oe.get('to')
            edge_value = float(oe.get('value'))
            self.weight_map[out_neibor] = self.weight_map.get(out_neibor, 0) + \
                                          node_weight * (edge_value / out_sum)

    def pop(self):
        items = list(self.weight_map.items())
        items.sort(key=lambda x: x[1], reverse=True)
        for node, weight in items:
            if weight < self.min_weight:
                return
            if node not in self._vis:
                self._vis.add(node)
                return dict(node=node, weight=weight)
