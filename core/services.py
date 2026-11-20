from decimal import Decimal, InvalidOperation
from django.db import transaction
from .models import Account, Transaction


class TransferError(Exception):
    def __init__(self, message: str, status_code: int = 400):
        self.message = message
        self.status_code = status_code
        super().__init__(message)


class TransferService:
    def __init__(self, source_account: Account):
        self.source_account = source_account

    @staticmethod
    def parse_amount(raw_amount) -> Decimal:
        if raw_amount is None or raw_amount == "":
            raise TransferError("Не указан счет получателя или сумма перевода.", status_code=400)
        try:
            amount = Decimal(str(raw_amount))
        except (InvalidOperation, ValueError, TypeError):
            raise TransferError("Сумма перевода должна быть числом.", status_code=400)

        if amount <= 0:
            raise TransferError("Сумма перевода должна быть больше нуля.", status_code=400)
        return amount

    def get_target_account(self, target_account_id) -> Account:
        if not target_account_id:
            raise TransferError("Не указан счет получателя или сумма перевода.", status_code=400)
        try:
            target_account = Account.objects.get(pk=target_account_id)
        except Account.DoesNotExist:
            raise TransferError("Счет получателя не найден.", status_code=404)

        if self.source_account.id == target_account.id:
            raise TransferError("Нельзя перевести деньги на свой же счет.", status_code=400)

        return target_account

    def execute(self, target_account_id, raw_amount) -> Decimal:
        amount = self.parse_amount(raw_amount)
        target_account = self.get_target_account(target_account_id)

        if self.source_account.balance < amount:
            raise TransferError("Недостаточно средств на счете.", status_code=400)

        with transaction.atomic():
            self.source_account.balance -= amount
            self.source_account.save()

            target_account.balance += amount
            target_account.save()

            Transaction.objects.create(
                sender=self.source_account,
                receiver=target_account,
                amount=amount
            )

        return self.source_account.balance