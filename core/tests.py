from decimal import Decimal
from django.test import TestCase
from django.urls import reverse
from django.contrib.auth.models import User
from rest_framework import status
from rest_framework.test import APIClient
from core.models import Client, Account, Transaction


class AccountModelTest(TestCase):
    """Набор тестов для проверки бизнес-логики банковских счетов и переводов"""

    def setUp(self):
        """Подготовка тестовых данных перед запуском каждого теста"""
        self.client_obj = Client.objects.create(
            first_name="Тест",
            last_name="Тестов",
            email="test@gmail.com"
        )
        self.account = Account.objects.create(
            client=self.client_obj,
            account_number="TEST-ACC-001",
            account_type=Account.AccountType.CREDIT,
            balance=Decimal("1000.00"),
            credit_limit=Decimal("5000.00")
        )

    def test_deposit_success(self):
        """Тест: Успешное пополнение счета положительной суммой"""
        new_balance = self.account.deposit(Decimal("500.50"))
        self.assertEqual(new_balance, Decimal("1500.50"))
        self.assertEqual(self.account.balance, Decimal("1500.50"))

    def test_deposit_negative(self):
        """Тест: Ошибка при попытке пополнить счет отрицательной суммой или нулем"""
        with self.assertRaises(ValueError):
            self.account.deposit(Decimal("0.00"))
        with self.assertRaises(ValueError):
            self.account.deposit(Decimal("-100.00"))

    def test_withdraw_within_credit_limit(self):
        """Тест: Успешное снятие средств в пределах баланса и кредитного лимита"""
        new_balance = self.account.withdraw(Decimal("4000.00"))
        self.assertEqual(new_balance, Decimal("-3000.00"))

    def test_withdraw_exceed_limit(self):
        """Тест: Ошибка при попытке снять сумму, превышающую общие доступные средства"""
        with self.assertRaises(ValueError):
            self.account.withdraw(Decimal("10000.00"))

    def test_transfer_success(self):
        """Тест: Успешный перевод средств между двумя счетами с записью транзакции"""
        client_2 = Client.objects.create(
            first_name="Петр",
            last_name="Петров",
            email="petr@example.com"
        )
        account_2 = Account.objects.create(
            client=client_2,
            account_number="TEST-ACC-002",
            account_type=Account.AccountType.DEBIT,
            balance=Decimal("500.00"),
            credit_limit=Decimal("0.00")
        )

        Account.transfer(
            sender_account_number=self.account.account_number,
            receiver_account_number=account_2.account_number,
            amount=Decimal("300.00")
        )

        self.account.refresh_from_db()
        account_2.refresh_from_db()
        self.assertEqual(self.account.balance, Decimal("700.00"))  # 1000 - 300
        self.assertEqual(account_2.balance, Decimal("800.00"))      # 500 + 300
        self.assertTrue(
            Transaction.objects.filter(
                sender=self.account,
                receiver=account_2,
                amount=Decimal("300.00")
            ).exists()
        )


class AccountTransferAPITest(TestCase):
    """Тесты REST API эндпоинта перевода средств /api/accounts/{id}/transfer/"""

    def setUp(self):
        self.api_client = APIClient()
        self.user = User.objects.create_user(
            username="tester",
            password="strong_password_123"
        )
        self.api_client.force_authenticate(user=self.user)

        self.client_1 = Client.objects.create(
            user=self.user,
            first_name="Иван",
            last_name="Иванов",
            email="ivan@example.com"
        )
        self.client_2 = Client.objects.create(
            first_name="Мария",
            last_name="Смирнова",
            email="maria@example.com"
        )
        self.sender_account = Account.objects.create(
            client=self.client_1,
            account_number="ACC-SENDER-001",
            account_type=Account.AccountType.DEBIT,
            balance=Decimal("1000.00"),
            credit_limit=Decimal("0.00")
        )
        self.receiver_account = Account.objects.create(
            client=self.client_2,
            account_number="ACC-RECEIVER-002",
            account_type=Account.AccountType.DEBIT,
            balance=Decimal("200.00"),
            credit_limit=Decimal("0.00")
        )
        self.url = reverse("account-transfer", kwargs={"pk": self.sender_account.pk})

    def test_api_transfer_success(self):
        """Успешный перевод через API обновляет балансы и создает Transaction"""
        response = self.api_client.post(
            self.url,
            {"target_account_id": self.receiver_account.id, "amount": "250.00"},
            format="json"
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.sender_account.refresh_from_db()
        self.receiver_account.refresh_from_db()

        self.assertEqual(self.sender_account.balance, Decimal("750.00"))
        self.assertEqual(self.receiver_account.balance, Decimal("450.00"))

        tx = Transaction.objects.get(
            sender=self.sender_account,
            receiver=self.receiver_account
        )
        self.assertEqual(tx.amount, Decimal("250.00"))

    def test_api_transfer_insufficient_funds(self):
        """Перевод при нехватке средств возвращает 400 и не меняет балансы"""
        response = self.api_client.post(
            self.url,
            {"target_account_id": self.receiver_account.id, "amount": "5000.00"},
            format="json"
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.sender_account.refresh_from_db()
        self.receiver_account.refresh_from_db()
        self.assertEqual(self.sender_account.balance, Decimal("1000.00"))
        self.assertEqual(self.receiver_account.balance, Decimal("200.00"))
        self.assertEqual(Transaction.objects.count(), 0)

    def test_api_transfer_to_same_account(self):
        """Перевод на тот же самый счет возвращает 400"""
        response = self.api_client.post(
            self.url,
            {"target_account_id": self.sender_account.id, "amount": "100.00"},
            format="json"
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(Transaction.objects.count(), 0)

    def test_api_transfer_target_not_found(self):
        """Перевод на несуществующий счет возвращает 404"""
        response = self.api_client.post(
            self.url,
            {"target_account_id": 99999, "amount": "100.00"},
            format="json"
        )

        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
        self.assertEqual(Transaction.objects.count(), 0)

    def test_api_transfer_non_positive_amount(self):
        """Нулевая или отрицательная сумма перевода возвращает 400"""
        for bad_amount in ["0", "-50.00"]:
            response = self.api_client.post(
                self.url,
                {"target_account_id": self.receiver_account.id, "amount": bad_amount},
                format="json"
            )
            self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

        self.assertEqual(Transaction.objects.count(), 0)
    def test_api_transfer_from_other_user_account_forbidden(self):
        """Перевод с чужого счета возвращает 403 Forbidden"""
        other_user = User.objects.create_user(
            username="other_user",
            password="strong_password_123"
        )
        other_client = Client.objects.create(
            user=other_user,
            first_name="Алексей",
            last_name="Алексеев",
            email="alex@example.com"
        )
        other_account = Account.objects.create(
            client=other_client,
            account_number="ACC-OTHER-003",
            account_type=Account.AccountType.DEBIT,
            balance=Decimal("1000.00"),
            credit_limit=Decimal("0.00")
        )
        url = reverse("account-transfer", kwargs={"pk": other_account.pk})

        response = self.api_client.post(
            url,
            {"target_account_id": self.receiver_account.id, "amount": "100.00"},
            format="json"
        )

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        other_account.refresh_from_db()
        self.assertEqual(other_account.balance, Decimal("1000.00"))