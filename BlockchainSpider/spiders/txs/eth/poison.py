import logging
import time

from BlockchainSpider.items import TxItem
from BlockchainSpider.spiders.txs.eth._meta import TxsETHSpider
from BlockchainSpider.strategies import Poison
from BlockchainSpider.tasks import AsyncTask


class TxsETHPoisonSpider(TxsETHSpider):
    name = 'txs.eth.poison'

    def __init__(self, **kwargs):
        super().__init__(**kwargs)

        # task map
        self.task_map = dict()
        self.depth = int(kwargs.get('depth', 2))

    def start_requests(self):
        # load source nodes
        if self.filename is not None:
            infos = self.load_task_info_from_csv(self.filename)
            for i, info in enumerate(infos):
                self.task_map[i] = AsyncTask(
                    strategy=Poison(
                        source=info['source'],
                        depth=info.get('depth', 2),
                    ),
                    **info
                )
            # with open(self.filename, 'r') as f:
            #     for row in csv.reader(f):
            #         source_nodes.add(row[0])
            #         self.task_map[row[0]] = AsyncTask(
            #             strategy=Poison(source=self.source, depth=self.depth),
            #             source=row[0],
            #         )
        elif self.source is not None:
            self.task_map[0] = AsyncTask(
                strategy=Poison(
                    source=self.source,
                    depth=self.depth,
                ),
                **self.info
            )
            # source_nodes.add(self.source)
            # self.task_map[self.source] = AsyncTask(
            #     strategy=Poison(source=self.source, depth=self.depth),
            #     source=self.source,
            # )

        # generate requests
        for tid in self.task_map.keys():
            task = self.task_map[tid]
            for txs_type in task.info['txs_types']:
                now = time.time()
                task.wait(now)
                yield self.txs_req_getter[txs_type](
                    address=task.info['source'],
                    **{
                        'depth': 1,
                        'startblock': task.info['start_blk'],
                        'endblock': task.info['end_blk'],
                        'task_id': tid
                    }
                )
        # for node in source_nodes:
        #     yield from self.gen_txs_requests(node, **{
        #         'source': node,
        #         'depth': 1,
        #     })

    def _parse_txs(self, response, func_next_page_request, **kwargs):
        # reload task id
        tid = kwargs['task_id']
        task = self.task_map[tid]

        # parse data from response
        txs = self.load_txs_from_response(response)
        if txs is None:
            self.log(
                message="On parse: Get error status from:%s" % response.url,
                level=logging.WARNING
            )
            return
        self.log(
            message='On parse: Extend {} from seed of {}, depth {}'.format(
                kwargs['address'], task.info['source'], kwargs['depth']
            ),
            level=logging.INFO
        )

        # save tx
        for tx in txs:
            yield TxItem(source=task.info['source'], tx=tx)

        # push data to task
        task.push(
            node=kwargs['address'],
            edges=txs,
            cur_depth=kwargs['depth'],
        )

        # next address request
        if txs is None or len(txs) < 10000 or task.info['auto_page'] is False:
            for item in task.pop():
                yield from self.gen_txs_requests(
                    address=item['node'],
                    depth=item['depth'],
                    startblock=task.info['start_blk'],
                    endblock=task.info['end_blk'],
                    task_id=tid,
                )
        # next page request
        else:
            now = time.time()
            task.wait(now)
            yield func_next_page_request(
                address=kwargs['address'],
                **{
                    'startblock': self.get_max_blk(txs),
                    'endblock': task.info['end_blk'],
                    'depth': kwargs['depth'],
                    'task_id': kwargs['task_id']
                }
            )

    # def _parse_txs(self, response, **kwargs):
    #     # parse data from response
    #     txs = self.load_txs_from_response(response)
    #     if txs is None:
    #         self.log(
    #             message="On parse: Get error status from:%s" % response.url,
    #             level=logging.WARNING
    #         )
    #         return
    #     self.log(
    #         message='On parse: Extend {} from seed of {}, depth {}'.format(
    #             kwargs['address'], kwargs['source'], kwargs['depth']
    #         ),
    #         level=logging.INFO
    #     )
    #
    #     if isinstance(txs, list):
    #         # save tx
    #         for tx in txs:
    #             yield TxItem(source=kwargs['source'], tx=tx)
    #
    #         # push data to task
    #         self.task_map[kwargs['source']].push(
    #             node=kwargs['address'],
    #             edges=txs,
    #             cur_depth=kwargs['depth'],
    #         )
    #
    #         # next address request
    #         if txs is None or len(txs) < 10000 or self.auto_page is False:
    #             task = self.task_map[kwargs['source']]
    #             for item in task.pop():
    #                 yield from self.gen_txs_requests(
    #                     source=kwargs['source'],
    #                     address=item['node'],
    #                     depth=item['depth']
    #                 )
    #         # next page request
    #         else:
    #             _url = response.url
    #             _url = urllib.parse.urlparse(_url)
    #             query_args = {k: v[0] if len(v) > 0 else None for k, v in urllib.parse.parse_qs(_url.query).items()}
    #             query_args['startblock'] = self.get_max_blk(txs)
    #             _url = '?'.join([
    #                 '%s://%s%s' % (_url.scheme, _url.netloc, _url.path),
    #                 urllib.parse.urlencode(query_args)
    #             ])
    #             yield scrapy.Request(
    #                 url=_url,
    #                 method='GET',
    #                 dont_filter=True,
    #                 cb_kwargs={
    #                     'source': kwargs['source'],
    #                     'address': kwargs['address'],
    #                     'depth': kwargs['depth'],
    #                 },
    #                 callback=self._parse_txs
    #             )

    def parse_external_txs(self, response, **kwargs):
        yield from self._parse_txs(response, self.get_external_txs_request, **kwargs)

    def parse_internal_txs(self, response, **kwargs):
        yield from self._parse_txs(response, self.get_internal_txs_request, **kwargs)

    def parse_erc20_txs(self, response, **kwargs):
        yield from self._parse_txs(response, self.get_erc20_txs_request, **kwargs)

    def parse_erc721_txs(self, response, **kwargs):
        yield from self._parse_txs(response, self.get_erc721_txs_request, **kwargs)
