import argparse
import csv
import json
import os

import networkx as nx


def load_graph_from_csv(fn: str) -> nx.Graph:
    g = nx.Graph()

    with open(fn, 'r', encoding='utf-8') as f:
        reader = csv.reader(f)
        headers = next(reader)
        for row in reader:
            item = {headers[i]: row[i] for i in range(len(row))}
            g.add_edge(item.get('from'), item.get('to'))

    return g


def calc_recall(g: nx.Graph, targets: list) -> float:
    assert len(targets) > 0

    nodes = set(g.nodes)
    target_cnt = 0
    for target in targets:
        if target in nodes:
            target_cnt += 1

    return target_cnt / len(targets)


def calc_size(g: nx.Graph) -> int:
    return g.number_of_nodes()


def calc_depth(g: nx.Graph, source) -> int:
    K = nx.single_source_shortest_path_length(g, source)
    K = list(K.items())
    K.sort(key=lambda x: x[1], reverse=True)
    return K[0][1] if len(K) > 0 else 0


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.description = 'calculate the metrics of cases'
    parser.add_argument(
        '-i', '--input',
        help='input data folder(str)',
        dest='in_dir',
        type=str,
        default=None
    )
    args = parser.parse_args()
    assert args.in_dir is not None

    cases = list()
    cases_path = './test/cases'
    for fn in os.listdir(cases_path):
        fn = os.path.join(cases_path, fn)
        with open(fn, 'r') as f:
            case = json.load(f)
            cases.append(case)

    avg_metrics = dict(
        recall=0,
        size=0,
        depth=0
    )
    for case in cases:
        source = case['source'][0]['address']
        targets = [item['address'] for item in case['target']]

        fn = os.path.join(args.in_dir, '%s.csv' % source)
        assert os.path.exists(fn), '%s does not existed' % fn
        print('processing:', source, end=' ')

        g = load_graph_from_csv(fn)
        g.add_node(source)
        recall = calc_recall(g, targets)
        size = calc_size(g)
        depth = calc_depth(g, source)

        avg_metrics['recall'] += recall
        avg_metrics['size'] += size
        avg_metrics['depth'] += depth

        print(dict(
            recall=recall,
            size=size,
            depth=depth,
            name=case.get('name')
        ))
    avg_metrics = {k: v / len(cases) for k, v in avg_metrics.items()}
    print('average metrics:', avg_metrics)
