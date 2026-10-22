from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


def vincular_empleados(apps, schema_editor):
    """
    Cada Usuario (empleado) queda vinculado a un User de Django:
    - Si ya existe un User con el mismo email (sin distinguir mayúsculas), se vincula.
    - Si no, se crea uno con username = email y se copia el hash de la
      contraseña que tenía Usuario.password (así sigue entrando con la misma clave).
    """
    Usuario = apps.get_model("inventario", "Usuario")
    User = apps.get_model(*settings.AUTH_USER_MODEL.split("."))

    for empleado in Usuario.objects.filter(user__isnull=True):
        email = (empleado.email or "").strip().lower()
        user = User.objects.filter(email__iexact=email).first()
        if user is None:
            user = User.objects.create(
                username=email,
                email=email,
                first_name=empleado.nombres[:150],
                last_name=empleado.apellidos[:150],
                # Hash existente; si estaba vacío queda como contraseña inutilizable.
                password=empleado.password or "!",
                is_active=True,
            )
        empleado.user = user
        empleado.email = email
        empleado.save(update_fields=["user", "email"])


class Migration(migrations.Migration):

    dependencies = [
        ("inventario", "0005_venta_estado"),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.AddField(
            model_name="usuario",
            name="user",
            field=models.OneToOneField(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.PROTECT,
                related_name="empleado",
                to=settings.AUTH_USER_MODEL,
            ),
        ),
        migrations.RunPython(vincular_empleados, migrations.RunPython.noop),
        migrations.RemoveField(model_name="usuario", name="password"),
        migrations.AlterField(
            model_name="venta",
            name="metodo_pago",
            field=models.CharField(
                choices=[
                    ("efectivo", "Efectivo"),
                    ("tarjeta_debito", "Tarjeta débito"),
                    ("tarjeta_credito", "Tarjeta crédito"),
                    ("transferencia", "Transferencia"),
                ],
                max_length=30,
            ),
        ),
    ]