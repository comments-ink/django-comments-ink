# -*- coding: utf-8 -*-
# Generated by Django 1.9.4 on 2016-07-11 19:29
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("django_comments_xtd", "0001_initial"),
    ]

    operations = [
        migrations.CreateModel(
            name="BlackListedDomain",
            fields=[
                (
                    "id",
                    models.AutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                ("domain", models.CharField(db_index=True, max_length=200)),
            ],
            options={
                "ordering": ("domain",),
            },
        ),
    ]
