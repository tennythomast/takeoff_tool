from rest_framework import generics, permissions
from rest_framework.response import Response
from django.contrib.auth import get_user_model
from rest_framework.views import APIView
from rest_framework import status

User = get_user_model()

class CurrentUserView(APIView):
    """
    View to retrieve and update the current user's information.
    """
    permission_classes = [permissions.IsAuthenticated]
    
    def get(self, request):
        """
        Return the authenticated user's details.
        """
        user = request.user
        
        # Get organization data if user has one
        organization = None
        user_org = user.organization
        if user_org:
            organization = {
                'id': user_org.id,
                'name': user_org.name,
                'slug': user_org.slug
            }
        
        # Return user data with organization
        return Response({
            'id': user.id,
            'email': user.email,
            'first_name': user.first_name,
            'last_name': user.last_name,
            'organization': organization
        })
    
    def patch(self, request):
        """
        Update the authenticated user's information.
        Only first_name and last_name can be updated.
        """
        user = request.user
        data = request.data
        
        # Update fields if provided
        if 'first_name' in data:
            user.first_name = data['first_name']
        if 'last_name' in data:
            user.last_name = data['last_name']
        
        # Email updates are not allowed through this endpoint
        if 'email' in data:
            return Response(
                {"error": "Email updates are not allowed. Please contact support to change your email."},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Save user
        user.save()
        
        # Return updated user data
        return Response({
            'id': user.id,
            'email': user.email,
            'first_name': user.first_name,
            'last_name': user.last_name
        })
