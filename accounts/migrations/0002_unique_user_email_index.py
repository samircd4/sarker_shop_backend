from django.db import migrations


class Migration(migrations.Migration):
    dependencies = [
        ('accounts', '0001_initial'),
    ]

    operations = [
        migrations.RunSQL(
            sql="CREATE UNIQUE INDEX IF NOT EXISTS unique_user_email ON auth_user(email);",
            reverse_sql="DROP INDEX IF EXISTS unique_user_email;"
        ),
    ]

