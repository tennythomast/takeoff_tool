#!/usr/bin/env python
"""
Script to check if an Anthropic API key exists in the database and add one if needed.
Run this script inside the Docker container with:
docker-compose exec backend python scripts/check_anthropic_key.py
"""

import os
import sys
import django
import logging
from decimal import Decimal

# Set up Django environment
sys.path.append('/app/backend')
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'dataelan.settings')
django.setup()

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def check_anthropic_key():
    """Check if an Anthropic API key exists in the database and add one if needed."""
    from modelhub.models import Provider, APIKey
    
    # Check if Anthropic provider exists
    try:
        anthropic_provider = Provider.objects.get(slug='anthropic')
        logger.info(f"Found Anthropic provider: {anthropic_provider.name}")
    except Provider.DoesNotExist:
        logger.error("Anthropic provider not found in database. Please create it first.")
        return False
    
    # Check if there's an API key for Anthropic
    api_key = APIKey.objects.filter(
        provider=anthropic_provider,
        is_active=True
    ).first()
    
    if api_key:
        logger.info(f"Anthropic API key exists (ID: {api_key.id})")
        # Check if the key is valid (not empty)
        if not api_key.key or api_key.key.strip() == "":
            logger.warning("Existing Anthropic API key is empty or invalid")
            return False
        return True
    else:
        logger.warning("No active Anthropic API key found in database")
        return False

def add_anthropic_key(api_key_value):
    """Add an Anthropic API key to the database."""
    from modelhub.models import Provider, APIKey
    
    if not api_key_value or api_key_value.strip() == "":
        logger.error("Cannot add empty API key")
        return False
    
    try:
        anthropic_provider = Provider.objects.get(slug='anthropic')
        
        # Create new API key
        api_key = APIKey(
            provider=anthropic_provider,
            key=api_key_value,
            is_active=True,
            name="Anthropic API Key",
            description="Added by check_anthropic_key.py script",
            daily_quota=Decimal('10.00'),  # Set appropriate quota
            monthly_quota=Decimal('100.00')  # Set appropriate quota
        )
        api_key.save()
        
        logger.info(f"Successfully added new Anthropic API key (ID: {api_key.id})")
        return True
    except Provider.DoesNotExist:
        logger.error("Anthropic provider not found in database")
        return False
    except Exception as e:
        logger.error(f"Error adding Anthropic API key: {str(e)}")
        return False

if __name__ == "__main__":
    logger.info("Checking Anthropic API key in database...")
    
    if check_anthropic_key():
        logger.info("Valid Anthropic API key exists in database")
    else:
        # Try to get key from environment
        api_key_value = os.environ.get('ANTHROPIC_API_KEY')
        
        if api_key_value:
            logger.info("Found ANTHROPIC_API_KEY in environment, adding to database")
            if add_anthropic_key(api_key_value):
                logger.info("Successfully added Anthropic API key from environment")
            else:
                logger.error("Failed to add Anthropic API key from environment")
        else:
            logger.error("No ANTHROPIC_API_KEY found in environment")
            logger.info("Please set the ANTHROPIC_API_KEY environment variable and run this script again")
            logger.info("Or manually add an API key through the admin interface")
