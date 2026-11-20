from decimal import Decimal
from django.db import models, transaction
from django.conf import settings

class Client(models.Model):
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='client_profile',
        null=True,
        blank=True,
        verbose_name='Пользователь'
    )
    first_name = models.CharField(max_length=50, verbose_name='Имя')
    last_name = models.CharField(max_length=50, verbose_name='Фамилия')
    email = models.EmailField(unique=True, verbose_name='Email')
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='Дата регистрации')

    def __str__(self):
        return f"{self.first_name} {self.last_name}"

class Account(models.Model):
    class AccountType(models.TextChoices):
        DEBIT = 'DEBIT', 'Дебитовый'
        SAVING = 'SAVING', 'Сберегательный'
        CREDIT = 'CREDIT', 'Кредитный'

    client = models.ForeignKey(
        Client,
        on_delete=models.CASCADE,
        related_name='accounts',
        verbose_name='Клиент'
    )
    account_number = models.CharField(max_length=20, unique=True, verbose_name='Номер счета')
    balance = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=0.00,
        verbose_name='Баланс'
    )
    account_type = models.CharField(
        max_length=10,
        choices=AccountType.choices,
        default=AccountType.DEBIT,
        verbose_name='Тип счета'
    )
    credit_limit = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=0.00,
        verbose_name='Кредитный лимит'
    )
    interest_rate = models.FloatField(
        default=0.0,
        verbose_name='Процентная ставка(%)'
    )

    def __str__(self):
        return f"Счет #{self.account_number} ({self.get_account_type_display()}) - {self.client}"

    def deposit(self, amount: Decimal):
        if amount <= 0:
            raise ValueError('Сумма пополнения должна быть больше нуля.')

        self.balance += amount
        self.save()
        return self.balance

    def withdraw(self, amount: Decimal):
        if amount <= 0:
            raise ValueError('Сумма снятия должна быть больше нуля.')
        if self.account_type == self.AccountType.CREDIT:
            available_funds = self.balance + self.credit_limit
            if amount > available_funds:
                raise ValueError('Превышен лимит доступных средств(с учетом крудитного лимита).')
        else:
            if amount > self.balance:
                raise ValueError('Недостаточно средств на счете.')
        self.balance -= amount
        self.save()
        return self.balance
    
    @classmethod
    def transfer(cls, sender_account_number: str, receiver_account_number: str, amount: Decimal):
        if amount <= Decimal('0.00'):
            raise ValueError('Сумма перевода должна быть больше нуля.')

        if sender_account_number == receiver_account_number:
            raise ValueError('Нельзя перевести деньги на тот же самый счет.')

        with transaction.atomic():
            try:
                sender = cls.objects.select_for_update().get(account_number=sender_account_number)
                receiver = cls.objects.select_for_update().get(account_number=receiver_account_number)
            except cls.DoesNotExist:
                raise ValueError('Один из счетов не найден.')

            sender.withdraw(amount)
            receiver.deposit(amount)

            Transaction.objects.create(
                sender = sender,
                receiver = receiver,
                amount = amount
            )

class Transaction(models.Model):
    sender = models.ForeignKey(Account, on_delete=models.PROTECT, related_name='sent_transactions', verbose_name='Счет отправителя')
    receiver = models.ForeignKey(Account, on_delete=models.PROTECT, related_name='received_transactions', verbose_name='Счет получателя')
    amount = models.DecimalField(max_digits=12, decimal_places=2, verbose_name='Сумма')
    timestamp = models.DateTimeField(auto_now_add=True, verbose_name='Дата и время')

    def __str__(self):
        return f'Перевод {self.amount} со счета {self.sender.account_number} на {self.receiver.account_number}'