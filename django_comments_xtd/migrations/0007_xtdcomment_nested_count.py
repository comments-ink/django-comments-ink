# Generated by Django 3.0.1 on 2020-09-12 20:08

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("django_comments_xtd", "0006_auto_20181204_0948"),
    ]

    operations = [
        migrations.AddField(
            model_name="xtdcomment",
            name="nested_count",
            field=models.IntegerField(db_index=True, default=0),
        ),
    ]
