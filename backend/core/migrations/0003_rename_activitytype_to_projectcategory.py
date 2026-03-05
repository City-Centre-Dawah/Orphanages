"""Rename ActivityType to ProjectCategory for naming clarity."""

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ("core", "0002_user_telegram_id_user_telegram_username"),
    ]

    operations = [
        migrations.RenameModel(
            old_name="ActivityType",
            new_name="ProjectCategory",
        ),
        migrations.AlterModelOptions(
            name="projectcategory",
            options={
                "ordering": ["sort_order", "name"],
                "verbose_name": "Project category",
                "verbose_name_plural": "Project categories",
            },
        ),
    ]
