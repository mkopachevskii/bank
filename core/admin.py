from django.contrib import admin
from .models import Client, Account, Transaction

@admin.register(Client)
class ClientAdmin(admin.ModelAdmin):
    list_display = ('id', 'first_name', 'last_name', 'email', 'created_at')
    search_fields = ('first_name', 'last_name', 'email')
    list_filter = ('created_at',)

@admin.register(Account)
class AccountAdmin(admin.ModelAdmin):
    list_display = ('id', 'account_number', 'client', 'balance', 'account_type')
    list_filter = ('account_type',)
    search_fields = ('account_number', 'client__first_name', 'client__last_name')

@admin.register(Transaction)
class TransactionAdmin(admin.ModelAdmin):
    list_display = ('id', 'sender', 'receiver', 'amount', 'timestamp')
    list_filter = ('timestamp',)
    search_fields = ('sender__account_number', 'receiver__account_number')
    readonly_fields = ('sender', 'receiver', 'amount', 'timestamp')

    def has_add_permission(self, request):
        return False

    def has_delete_permission(self, request, obj = None):
        return False