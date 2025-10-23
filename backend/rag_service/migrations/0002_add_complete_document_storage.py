from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('rag_service', '0001_initial'),
    ]

    operations = [
        migrations.AddField(
            model_name='document',
            name='storage_approach',
            field=models.CharField(
                choices=[
                    ('chunked', 'Chunked Storage'), 
                    ('complete', 'Complete Document Storage'), 
                    ('hybrid', 'Hybrid Storage')
                ],
                db_index=True,
                default='complete',
                help_text='Approach used for storing document content',
                max_length=20
            ),
        ),
        migrations.AddField(
            model_name='document',
            name='content_search_vector',
            field=models.JSONField(
                blank=True,
                help_text='Search vector for full-text search capabilities',
                null=True
            ),
        ),
        migrations.AddIndex(
            model_name='document',
            index=models.Index(fields=['storage_approach'], name='rag_documen_storage_f6e2c2_idx'),
        ),
    ]
