# Generated by Django 3.2.9 on 2022-01-09 14:31

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('hub', '0016_alter_itempicture_item'),
    ]

    operations = [
        migrations.AddField(
            model_name='taxon',
            name='website',
            field=models.CharField(blank=True, max_length=512, null=True),
        ),
    ]