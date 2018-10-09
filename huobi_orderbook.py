from websocket import create_connection
from orderbook_base import OrderbookBase
from threading import Thread
import gzip
import time
import json

class HuobiOrderbook(OrderbookBase):
    pairs_dict = {'BTC-USD': 'btcusdt', 'BCH-USD': 'bchusdt'}

    def __init__(self, asset_pairs, fees, **kwargs):
        super().__init__(asset_pairs, fees)
        self._listener_threads = []
        self._listener_ws = None
        self._is_running = False
        self._current_orderbook = {}

    def _start(self):
        print('start huobi exchange')
        while(True):
            try:
                self._listener_ws = create_connection("wss://api.huobipro.com/ws")
                break
            except:
                print('connect ws error,retry...') 
                time.sleep(5)
        print('successfully connected to ws')
        for asset_pair in self._asset_pairs:
            if asset_pair in HuobiOrderbook.pairs_dict.keys():
                pair = HuobiOrderbook.pairs_dict.get(asset_pair)
                self._listener_ws.send("""{"sub": "market.""" + pair + """.depth.step0", "id": "id10"}""")
                self._listener_threads.append(Thread(target=self.handle_data,kwargs={'asset_pair':asset_pair}, daemon=True, name='Listen to Huobi queue ' + asset_pair ))  
                self._listener_threads[len(self._listener_threads) - 1].start()

    def _stop(self):
        print('Stop Huobi excange')
        self._is_running = False
        for listener_thread in self._listener_threads:
            listener_thread.stop()

    def handle_data(self, asset_pair):
        print('handle data function')
        print(asset_pair + ' ' + str(self._listener_ws))
        self._is_running = True
        while(self._is_running):
            compressData = self._listener_ws.recv()
            result = gzip.decompress(compressData).decode('utf-8')
            if result[:7] == '{"ping"':
                ts=result[8:21]
                pong='{"pong":'+ts+'}'
                self._listener_ws.send(pong)
                self._listener_ws.send("""{"sub": "market.""" + HuobiOrderbook.pairs_dict.get(asset_pair) + """.depth.step0", "id": "id10"}""")
            else:
                self._current_orderbook.update({asset_pair: self.normalize_orderbook(result)})

    def normalize_orderbook(self, message):
        message = json.loads(message)
        orderbook = message.get('tick')
        if orderbook is not None:
            ts = message.get('ts')
            normalized_bids = [{'price': bid[0], 'size': bid[1]} for bid in orderbook['bids']]
            normalized_asks = [{'price': ask[0], 'size': ask[1]} for ask in orderbook['asks']]
            return {'time': ts, 'bids': normalized_bids, 'asks': normalized_asks}

    def _get_orderbook_from_exchange(self, asset_pair, size):
        try:
            orderbook = self._current_orderbook.get(asset_pair)
            orderbook.update({'bids': orderbook.get('bids')[:size], 'asks': orderbook.get('asks')[:size]})
            return orderbook
        except:
            return {'bids': [], 'asks': []}



# if __name__ == '__main__':
#     print ('start process')
#     huobiOrderbook = HuobiOrderbook(['BTC-USD', 'BCH-USD'], 5);
#     huobiOrderbook._start()
#     time.sleep(5)
#     print(huobiOrderbook._get_orderbook_from_exchange('BTC-USD', 3))
#     print(huobiOrderbook._get_orderbook_from_exchange('BCH-USD', 3))
    




# -*- coding: utf-8 -*-
#author: 半熟的韭菜

# from websocket import create_connection
# import gzip
# import time

# if __name__ == '__main__':
#     while(1):
#         try:
#             ws = create_connection("wss://api.huobipro.com/ws")
#             break
#         except:
#             print('connect ws error,retry...')
#             time.sleep(5)

#     # 订阅 KLine 数据
#     # tradeStr="""{"sub": "market.ethusdt.kline.1min","id": "id10"}"""

#     # 请求 KLine 数据
#     # tradeStr="""{"req": "market.ethusdt.kline.1min","id": "id10", "from": 1513391453, "to": 1513392453}"""

#     #订阅 Market Depth 数据
#     # tradeStr="""{"sub": "market.ethusdt.detail", "id": "id10"}"""

#     #请求 Market Depth 数据
#     tradeStr="""{"sub": "market.btcusdt.depth.step3", "id": "id10"}"""

#     #订阅 Trade Detail 数据
#     # tradeStr="""{"sub": "market.ethusdt.trade.detail", "id": "id10"}"""

#     #请求 Trade Detail 数据
#     # tradeStr="""{"req": "market.ethusdt.trade.detail", "id": "id10"}"""

#     #请求 Market Detail 数据
#     # tradeStr="""{"req": "market.ethusdt.detail", "id": "id12"}"""

#     ws.send(tradeStr)
#     while(1):
#         compressData=ws.recv()
#         result=gzip.decompress(compressData).decode('utf-8')
#         if result[:7] == '{"ping"':
#             ts=result[8:21]
#             pong='{"pong":'+ts+'}'
#             ws.send(pong)
#             ws.send(tradeStr)
#         else:
#             print(result)        
        