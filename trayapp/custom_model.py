import graphene
import graphql
from graphql import GraphQLError

from trayapp.utils import get_banks_list, get_bank_account_details
from users.types import StoreType, TransactionType

from users.models import Wallet, Transaction

from graphene.types import Scalar
import json

# django cache
from django.core.cache import cache


class JSONField(Scalar):
    """
    Custom scalar type for Django JSONField.
    """

    @staticmethod
    def serialize(json_value):
        """
        Serialize the JSONField value.

        :param json_value: The JSONField value.
        :type json_value: dict
        :return: Serialized JSONField value.
        :rtype: dict
        """
        return json_value

    @staticmethod
    def parse_value(json_string):
        """
        Deserialize the JSONField value.

        :param json_string: The JSONField value as a string.
        :type json_string: str
        :return: Deserialized JSONField value.
        :rtype: dict
        """
        try:
            return json.loads(json_string)
        except (TypeError, ValueError):
            return None

    @staticmethod
    def parse_literal(node):
        """
        Parse a literal GraphQL node value.

        :param node: The GraphQL node.
        :type node: Node
        :return: Deserialized JSONField value.
        :rtype: dict
        """
        return node.value

class Output:
    """
    A class to all public classes extend to
    padronize the output
    """

    success = graphene.Boolean(default_value=True)
    msg = graphene.String(default_value="ok")

# Our BankNode model
class SubBankNode(graphene.ObjectType):
    id = graphene.Int()
    name = graphene.String()
    code = graphene.String()
    longcode = graphene.String()
    active = graphene.Boolean()
    is_deleted = graphene.Boolean()

class EmailVerifiedNode(Output, graphene.ObjectType):
    pass

class ItemsAvalibilityNode(graphene.ObjectType):
    product_slug = graphene.String()
    store_avaliable_in = graphene.List(StoreType)
    is_avaliable = graphene.Boolean()
    avaliable_store = graphene.String()


class BankNode(Output, graphene.ObjectType):
    banks = graphene.List(SubBankNode)

class AccountInfoNode(Output, graphene.ObjectType):
    balance = graphene.String()
    transactions = graphene.List(TransactionType)

class BankAccountNode(Output, graphene.ObjectType):
    bank_id = graphene.Int()
    account_name = graphene.String()
    account_number = graphene.String()

# This is the class we will be using to query the bank list
class BankListQuery(graphene.ObjectType):

    # Return a list of banks objects
    banksList = graphene.Field(BankNode, use_cursor=graphene.Boolean(required=False), perPage=graphene.Int(required=False),
                               page=graphene.Int(required=False),
                               currency=graphene.String(required=False))
    validate_bank_account = graphene.Field(BankAccountNode, account_number=graphene.String(
        required=True), bank_code=graphene.String(required=True))

    account_info = graphene.Field(AccountInfoNode)

    def resolve_account_info(self, info: graphql.ResolveInfo, **kwargs):
        user = info.context.user
        data = {
            'msg': "An Error Occured",
            'success': False,
            'balance': None,
            'transactions': None
        }
        if user and user.is_authenticated:
            wallet = Wallet.objects.filter(user=user.profile).first()
            transactions = Transaction.objects.filter(wallet=wallet).order_by('-created_at')
            data = {
                'msg': "ok",
                'success': True,
                'balance': wallet.balance if(wallet) else None,
                'transactions': transactions
             }
        return data

    # This is the function that will be called when we query the bank list
    def resolve_banksList(self, info: graphql.ResolveInfo, use_cursor=False, perPage=10, page=1, currency="NGN"):
        if info.context.user.is_authenticated:
            data = {
                'use_cursor': use_cursor,
                'perPage': perPage,
                'page': page,
                'currency': currency
            }
            # Check if the bank list is cached
            if cache.get('banklist'):
                banklist = cache.get('banklist')
                return banklist
            try:
                banklist = get_banks_list(data)  # Get the bank list
                # cache the bank list for 2 minutes
                cache.set('banklist', banklist, 120)
                if banklist:
                    if banklist['status'] == True:
                        bank_list = {
                            'success': banklist['status'],
                            'msg': banklist['message'],
                            'banks': banklist['data']

                        }
                    else:
                        bank_list = {
                            'success': banklist['status'], 'msg': banklist['message']}
                # return banksList
                return bank_list
            except:
                raise GraphQLError("Unable to Get List Banks")
        else:
            raise GraphQLError("Login Required")

    # This is the function that will be called when we query the validate_bank_account
    def resolve_validate_bank_account(self, info: graphql.ResolveInfo, account_number, bank_code):
        if info.context.user.is_authenticated:  # Check if user is authenticated
            # Get the inputs and store it in a dict
            data = {
                "account_number": account_number,
                "bank_code": bank_code
            }
            try:  # Try to get the bank account details
                accountDetails = get_bank_account_details(
                    data)  # Get the bank account details
                if accountDetails:  # Check if the account details is not empty
                    print(accountDetails)
                    if accountDetails['status'] == True:  # Check if the status is true
                        data = accountDetails['data']
                        account_details = {
                            'success': accountDetails['status'],
                            'msg': accountDetails['message'],
                            'bank_id': data['bank_id'],
                            'account_name': data['account_name'],
                            'account_number': data['account_number']
                        }
                    else:
                        account_details = {
                            'success': accountDetails['status'],
                            'msg': accountDetails['message'],
                        }
                # return account_details
                return account_details
            except:  # If there is an error
                # Raise an error
                raise GraphQLError("Unable to Get Account Details")
        else:  # If user is not authenticated
            raise GraphQLError("Login Required")  # Raise an error
