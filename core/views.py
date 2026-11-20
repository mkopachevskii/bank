from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from .models import Client, Account, Transaction
from .serializers import ClientSerializer, AccountSerializer, TransactionSerializer
from .services import TransferService, TransferError


class ClientViewSet(viewsets.ModelViewSet):
    queryset = Client.objects.all()
    serializer_class = ClientSerializer


class AccountViewSet(viewsets.ModelViewSet):
    queryset = Account.objects.all()
    serializer_class = AccountSerializer

    @action(detail=True, methods=['post'])
    def transfer(self, request, pk=None):
        source_account = self.get_object()

        if source_account.client.user != request.user and not request.user.is_superuser:
            return Response(
                {"error": "Вы можете переводить средства только со своего счета."},
                status=status.HTTP_403_FORBIDDEN
            )

        service = TransferService(source_account)

        try:
            new_balance = service.execute(
                target_account_id=request.data.get('target_account_id'),
                raw_amount=request.data.get('amount')
            )
            return Response(
                {
                    "message": "Перевод успешно выполнен!",
                    "new_balance": new_balance
                },
                status=status.HTTP_200_OK
            )
        except TransferError as e:
            return Response(
                {"error": e.message},
                status=e.status_code
            )
        except Exception as e:
            return Response(
                {"error": f"Произошла ошибка при переводе: {str(e)}"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class TransactionViewSet(viewsets.ModelViewSet):
    queryset = Transaction.objects.all()
    serializer_class = TransactionSerializer
    http_method_names = ['get', 'head', 'options']