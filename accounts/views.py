from django.contrib import messages
from django.contrib.auth import login, logout
from django.contrib.auth import views as auth_views
from django.contrib.auth.decorators import login_required
from django.shortcuts import redirect, render
from django.views.decorators.http import require_POST

from . import services
from .forms import CustomerRegistrationForm, LoginForm, OwnerRegistrationForm, ProfileForm
from .models import User


class LoginView(auth_views.LoginView):
    template_name = "accounts/login.html"
    authentication_form = LoginForm
    redirect_authenticated_user = True

    def get_success_url(self):
        url = services.post_login_url(self.request.user, self.get_redirect_url())
        # Oturumu açık müşteri `?next=` olarak bu sayfanın kendisiyle gelirse Django "Redirection loop" hatası verir.
        return services.home_url(self.request.user) if url == self.request.path else url


def _register(request, form_class, template_name):
    if request.user.is_authenticated:
        return redirect(services.home_url(request.user))

    next_url = services.safe_next_url(request, request.POST.get("next") or request.GET.get("next"))
    form = form_class(request.POST) if request.method == "POST" else form_class()
    if request.method == "POST" and form.is_valid():
        user = form.save()
        login(request, user)
        messages.success(request, f"Hesabın oluşturuldu. Hoş geldin, @{user.username}.")
        return redirect(services.post_login_url(user, next_url))
    return render(request, template_name, {"form": form, "next": next_url})


def register_customer(request):
    return _register(request, CustomerRegistrationForm, "accounts/register_customer.html")


def register_owner(request):
    return _register(request, OwnerRegistrationForm, "accounts/register_owner.html")


@require_POST
def logout_view(request):
    logout(request)
    messages.info(request, "Çıkış yaptın.")
    return redirect("core:home")


@login_required
def profile(request):
    # Form, oturumdaki kullanıcı nesnesini değiştirmesin: geçersiz denemede başlıkta yanlış ad görünmesin.
    instance = User.objects.get(pk=request.user.pk)
    if request.method == "POST":
        form = ProfileForm(request.POST, instance=instance)
        if form.is_valid():
            form.save()
            messages.success(request, "Profilin güncellendi.")
            return redirect("accounts:profile")
    else:
        form = ProfileForm(instance=instance)
    return render(request, "accounts/profile.html", {"form": form})
