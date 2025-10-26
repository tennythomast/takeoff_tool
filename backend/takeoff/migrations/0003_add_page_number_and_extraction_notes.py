# Generated migration to add page_number and extraction_notes fields

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('takeoff', '0001_initial'),
    ]

    operations = [
        migrations.AddField(
            model_name='takeoffelement',
            name='page_number',
            field=models.IntegerField(default=1, help_text='Page number where this element was found'),
        ),
        migrations.AddField(
            model_name='takeoffelement',
            name='extraction_notes',
            field=models.JSONField(default=dict, blank=True, help_text='Notes and metadata from the extraction process'),
        ),
        migrations.AddIndex(
            model_name='takeoffelement',
            index=models.Index(fields=['page_number'], name='takeoff_ele_page_nu_idx'),
        ),
    ]
