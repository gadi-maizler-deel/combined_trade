import bitstamp.client
import client_wrapper_base
import logging

class BitstampClientWrapper(client_wrapper_base.ClientWrapperBase):
    def __init__(self, credentials, orderbook, db_interface):
        super().__init__(orderbook, db_interface)
        self.log = logging.getLogger(__name__)
        self._bitstamp_client = None
        self._signed_in_user = ""
        self.set_credentials(credentials)
        self._fee = 0

    def set_credentials(self, client_credentials):
        username = ''
        key = ''
        secret = ''
        self.cancel_timed_order()
        try:
            if client_credentials is not None and 'username' in client_credentials and \
                    'key' in client_credentials and 'secret' in client_credentials:
                username = client_credentials['username']
                key = client_credentials['key']
                secret = client_credentials['secret']

            if len(username) != 0 and len(username) != 0 and len(username) != 0:
                self._bitstamp_client = bitstamp.client.Trading(username=username, key=key, secret=secret)
                self._bitstamp_client.account_balance()
                self._signed_in_user = username
                self._balance_changed = True
                self._is_client_init = True
            else:
                self._signed_in_user = ''
                self._bitstamp_client = None
        except:
            self._bitstamp_client = None
            self._signed_in_user = ''
            self._balance_changed = False
            self._is_client_init = False

        return self._bitstamp_client is not None

    def get_signed_in_credentials(self):
        signed_in_dict = {True: "True", False: "False"}
        return {'signed_in_user': self._signed_in_user, 'is_user_signed_in': signed_in_dict[self._signed_in_user != ""]}

    def logout(self):
        super().logout()
        return self._bitstamp_client is None

    def _get_balance_from_exchange(self):
        result = {}
        if self._bitstamp_client is not None and self._signed_in_user != "":
            try:
                bitstamp_account_balance = self._bitstamp_client.account_balance(False, False)
                if 'btcusd_fee' in bitstamp_account_balance:
                    self._fee = float(bitstamp_account_balance['btcusd_fee'])
                elif 'fee' in bitstamp_account_balance:
                    self._fee = float(bitstamp_account_balance['fee'])
                for bitstamp_balance_key in bitstamp_account_balance:
                    if bitstamp_balance_key.endswith("_available"):
                        available_balance = float(bitstamp_account_balance[bitstamp_balance_key])
                        balance_key = bitstamp_balance_key.replace("_available", "_balance")
                        balance = 0
                        if balance_key in bitstamp_account_balance:
                            balance = float(bitstamp_account_balance[balance_key])
                        currency = bitstamp_balance_key.replace("_available", "")
                        result[currency.upper()] = {"amount": balance, "available": available_balance}
            except Exception as e:
                self.log.error("%s", str(e))
        return result

    def get_exchange_name(self):
        return "Bitstamp"

    def _execute_immediate_or_cancel(self, exchange_method, size, price, crypto_type):
        self.log.debug("Executing <%s>, size=<%f>, price=<%f>, type=<%s>", exchange_method, size, price, crypto_type)
        execute_result = {'exchange': self.get_exchange_name(), 'order_status': False}
        try:
            if self._bitstamp_client is not None and self._signed_in_user != "":
                limit_order_result = exchange_method(size, price, crypto_type)
                self.log.info("Execution result: <%s>", execute_result)
                order_id = limit_order_result['id']
                execute_result['id'] = order_id
                execute_result['executed_price_usd'] = price
                order_status = self.order_status(order_id)
                self.log.debug("order status <%s>", order_status)

                cancel_status = None
                if order_status is not None and 'status' in order_status and order_status['status'] == 'Finished' and \
                        len(order_status['transactions']) > 0:
                    execute_result['status'] = 'Finished'
                    execute_result['executed_price_usd'] = order_status['transactions'][0]['price']
                    execute_result['order_status'] = True
                elif order_status is None:
                    execute_result['status'] = 'Finished'
                    execute_result['order_status'] = True
                else:
                    self.log.debug("Cancelling order")
                    if order_status is not None:
                        try:
                            cancel_status = self._cancel_order(order_id)
                            if cancel_status:
                                execute_result['status'] = 'Cancelled'
                                self.log.info("Order cancelled: <%s>", cancel_status)
                        except Exception as e:
                            self.log.debug("Exception while cancelling order: <%s>", str(e))

                if cancel_status is None:
                    execute_result['status'] = 'Finished'
                    try:
                        found_transaction = False
                        all_transactions = self.user_transactions()
                        self.log.debug("curr transaction <%d> transactions: <%s>", order_id, all_transactions)
                        for curr_transaction in all_transactions:
                            if curr_transaction['order_id'] == order_id or curr_transaction['order_id'] == int(order_id):
                                execute_result['executed_price_usd'] = curr_transaction['btc_usd']
                                found_transaction = True
                                break
                        if not found_transaction:
                            self.log.warning("Transaction for <%d> not found", order_id)
                        execute_result['order_status'] = True
                    except Exception as e:
                        self.log.error("Exception while getting transactions data: <%s>", str(e))

        except Exception as e:
            self.log.error("%s %s", str(type(exchange_method)), str(e))
            execute_result['status'] = 'Error'
        return execute_result

    def buy_immediate_or_cancel(self, execute_size_coin, price_fiat, crypto_type):
        return self._execute_immediate_or_cancel(self._bitstamp_client.buy_limit_order, execute_size_coin, price_fiat,
                                                 crypto_type)

    def sell_immediate_or_cancel(self, execute_size_coin, price_fiat, crypto_type):
        return self._execute_immediate_or_cancel(self._bitstamp_client.sell_limit_order, execute_size_coin, price_fiat,
                                                 crypto_type)

    def order_status(self, order_id):
        order_status = None
        if self._bitstamp_client is not None and self._signed_in_user != "":
            try:
                order_status = self._bitstamp_client.order_status(order_id)
            except Exception as e:
                self.log.info("can't get order status: %s", str(e))
        return order_status

    def _cancel_order(self, order_id):
        cancel_status = False
        if self._bitstamp_client is not None and self._signed_in_user != "":
            try:
                cancel_status = self._bitstamp_client.cancel_order(order_id)
                self.log.debug("Cancel status: <%s>", cancel_status)
            except Exception as e:
                self.log.error("Cancel exception: %s", str(e))
        return cancel_status

    def transactions(self, transactions_limit):
        transactions = []
        try:
            if self._bitstamp_client is not None and self._signed_in_user != "":
                transactions = self._bitstamp_client.user_transactions()
                if transactions_limit != 0 and len(transactions) > transactions_limit:
                    transactions = transactions[0:transactions_limit]
        except Exception as e:
            self.log.error("%s", str(e))
            transactions = []
        return transactions

    def exchange_fee(self, crypto_type):
        return self._fee