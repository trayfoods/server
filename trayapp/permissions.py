from graphql.error import GraphQLError


class BasePermission:
    @staticmethod
    def has_permission(context):
        return True
        


class IsAuthenticated(BasePermission):
    """
    permission to check for user authentication
    """
    @classmethod
    def has_permission(cls, context):
        return context.user and (context.user.is_authenticated and context.user.is_active)


def permission_checker(permissions: list):
    def wrap_decorator(func):
        def inner(cls, info, *args, **kwargs):
            if check_permission(permissions, info.context):
                return func(cls, info, **kwargs)
            
            raise GraphQLError("Permission Denied")
        
        return inner
    
    return wrap_decorator


def check_permission(permissions, context):
    return all(permission.has_permission(context) for permission in permissions)
