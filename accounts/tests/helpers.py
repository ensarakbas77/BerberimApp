from accounts.models import User

PASSWORD = "Sifre-9x-Guclu!"


def make_user(username="musteri", email=None, role=User.Role.CUSTOMER, password=PASSWORD, **extra):
    return User.objects.create_user(
        email=email or f"{username}@example.com",
        username=username,
        password=password,
        role=role,
        **extra,
    )


def make_owner(username="sahip", **extra):
    return make_user(username=username, role=User.Role.OWNER, **extra)


def registration_data(**overrides):
    data = {
        "username": "ensar_k",
        "email": "ensar@example.com",
        "password1": PASSWORD,
        "password2": PASSWORD,
        "phone": "",
    }
    data.update(overrides)
    return data
