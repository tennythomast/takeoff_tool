from rest_framework import serializers
from rest_framework.exceptions import AuthenticationFailed
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer
from rest_framework_simplejwt.views import TokenObtainPairView
from django.contrib.auth import authenticate


class EmailTokenObtainPairSerializer(TokenObtainPairSerializer):
    username_field = 'email'
    
    def validate(self, attrs):
        # Get email and password from request
        email = attrs.get('email')
        password = attrs.get('password')
        
        if email and password:
            # Authenticate with email and password
            user = authenticate(request=self.context.get('request'),
                                email=email, password=password)
            
            # If authentication fails
            if not user:
                msg = 'No active account found with the given credentials'
                raise AuthenticationFailed(msg, code='authorization')
            
            # Check if the user is active
            if not user.is_active:
                msg = 'User account is disabled.'
                raise AuthenticationFailed(msg, code='authorization')
            
            # Set the user on the serializer
            attrs['user'] = user
            return super().validate(attrs)
        else:
            msg = 'Must include "email" and "password".'
            raise AuthenticationFailed(msg, code='authorization')


class EmailTokenObtainPairView(TokenObtainPairView):
    serializer_class = EmailTokenObtainPairSerializer
