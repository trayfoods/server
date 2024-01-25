import unittest
from unittest.mock import MagicMock
from users.models import Wallet, Transaction, Profile


class WalletTestCase(unittest.TestCase):
    def setUp(self):
        self.wallet = Wallet()
        self.wallet.user = Profile()
        self.wallet.currency = "NGN"
        self.wallet.balance = 100.00
        self.wallet.passcode = None

    def test_set_passcode(self):
        passcode = "1234"
        self.wallet.set_passcode(passcode)
        self.assertIsNotNone(self.wallet.passcode)

    def test_check_passcode_correct(self):
        passcode = "0000"
        self.wallet.set_passcode(passcode)
        result = self.wallet.check_passcode(passcode)
        self.assertTrue(result)

    def test_check_passcode_incorrect(self):
        passcode = "0000"
        self.wallet.set_passcode(passcode)
        result = self.wallet.check_passcode("1111")
        self.assertFalse(result)

    def test_get_unsettled_balance(self):
        transaction1 = MagicMock(amount=50.00)
        transaction2 = MagicMock(amount=75.00)
        Transaction.objects.filter.return_value = [transaction1, transaction2]
        result = self.wallet.get_unsettled_balance()
        self.assertEqual(result, 125.00)

    def test_add_balance_without_order(self):
        amount = 50.00
        self.wallet.add_balance(amount)
        self.assertEqual(self.wallet.balance, 150.00)

    def test_add_balance_with_order(self):
        amount = 50.00
        order = MagicMock()
        self.wallet.get_transactions.return_value.filter.return_value.first.return_value = None
        self.wallet.add_balance(amount, order=order)
        self.assertEqual(self.wallet.balance, 150.00)

    def test_add_balance_with_existing_order_transaction(self):
        amount = 50.00
        order = MagicMock()
        self.wallet.get_transactions.return_value.filter.return_value.first.return_value = MagicMock()
        with self.assertRaises(Exception):
            self.wallet.add_balance(amount, order=order)

    def test_deduct_balance_without_order(self):
        amount = 50.00
        kwargs = {"amount": amount}
        self.wallet.deduct_balance(**kwargs)
        self.assertEqual(self.wallet.balance, 50.00)

    def test_deduct_balance_with_order(self):
        amount = 50.00
        order = MagicMock()
        kwargs = {"amount": amount, "order": order}
        self.wallet.get_transactions.return_value.filter.return_value.first.return_value = MagicMock(status="settled")
        self.wallet.deduct_balance(**kwargs)
        self.assertEqual(self.wallet.balance, 50.00)

    def test_deduct_balance_with_order_no_transaction(self):
        amount = 50.00
        order = MagicMock()
        kwargs = {"amount": amount, "order": order}
        self.wallet.get_transactions.return_value.filter.return_value.first.return_value = None
        with self.assertRaises(Exception):
            self.wallet.deduct_balance(**kwargs)

    def test_deduct_balance_with_order_unsettled_transaction(self):
        amount = 50.00
        order = MagicMock()
        kwargs = {"amount": amount, "order": order}
        self.wallet.get_transactions.return_value.filter.return_value.first.return_value = MagicMock(status="unsettled")
        with self.assertRaises(Exception):
            self.wallet.deduct_balance(**kwargs)

    def test_deduct_balance_with_transaction_id(self):
        amount = 50.00
        transaction_id = "12345"
        kwargs = {"amount": amount, "transaction_id": transaction_id}
        self.wallet.balance = 100.00
        self.wallet.get_transactions.return_value.get.return_value = MagicMock(_type="debit")
        self.wallet.deduct_balance(**kwargs)
        self.assertEqual(self.wallet.balance, 50.00)

    def test_deduct_balance_with_transaction_id_invalid(self):
        amount = 50.00
        transaction_id = "12345"
        kwargs = {"amount": amount, "transaction_id": transaction_id}
        self.wallet.balance = 100.00
        self.wallet.get_transactions.return_value.get.return_value = None
        with self.assertRaises(Exception):
            self.wallet.deduct_balance(**kwargs)

    def test_reverse_transaction(self):
        amount = 50.00
        transaction_id = "12345"
        kwargs = {"amount": amount, "transaction_id": transaction_id}
        transaction = MagicMock()
        Transaction.objects.filter.return_value.first.return_value = transaction
        self.wallet.reverse_transaction(**kwargs)
        self.assertEqual(self.wallet.balance, 150.00)


if __name__ == "__main__":
    unittest.main()