# core/middleware.py - Replace your existing middleware
from urllib.parse import parse_qs
from django.contrib.auth.models import AnonymousUser
from django.contrib.auth import get_user_model
from rest_framework_simplejwt.tokens import AccessToken
from rest_framework_simplejwt.exceptions import InvalidToken, TokenError
from channels.middleware import BaseMiddleware
from channels.db import database_sync_to_async
import logging

logger = logging.getLogger(__name__)
User = get_user_model()

class TokenAuthMiddleware(BaseMiddleware):
    async def __call__(self, scope, receive, send):
        try:
            # Get token from query params
            query_string = scope.get('query_string', b'').decode()
            query_params = parse_qs(query_string)
            token = query_params.get('token', [None])[0]
            
            if token:
                # Validate JWT token
                access_token = AccessToken(token)
                
                # Try email first (based on your JWT settings)
                if 'email' in access_token:
                    email = access_token['email']
                    user = await self.get_user_by_email(email)
                # Fallback to user_id
                elif 'user_id' in access_token:
                    user_id = access_token['user_id']
                    user = await self.get_user_by_id(user_id)
                # Try 'sub' (standard JWT claim)
                elif 'sub' in access_token:
                    identifier = access_token['sub']
                    if '@' in str(identifier):
                        user = await self.get_user_by_email(identifier)
                    else:
                        user = await self.get_user_by_id(identifier)
                else:
                    logger.error(f"Token missing user identifier. Available: {list(access_token.keys())}")
                    user = AnonymousUser()
                
                scope['user'] = user if user and user.is_authenticated else AnonymousUser()
            else:
                scope['user'] = AnonymousUser()
                
        except Exception as e:
            logger.error(f"Auth error: {e}")
            scope['user'] = AnonymousUser()
            
        return await super().__call__(scope, receive, send)
    
    @database_sync_to_async
    def get_user_by_email(self, email):
        try:
            return User.objects.get(email=email, is_active=True)
        except User.DoesNotExist:
            return AnonymousUser()
    
    @database_sync_to_async
    def get_user_by_id(self, user_id):
        try:
            return User.objects.get(id=user_id, is_active=True)
        except User.DoesNotExist:
            return AnonymousUser()