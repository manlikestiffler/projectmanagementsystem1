
from typing import Protocol
from django.shortcuts import render, redirect
from django.contrib.auth import login, logout, authenticate, get_user_model
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.template.loader import render_to_string
from django.contrib.sites.shortcuts import get_current_site
from django.utils.http import urlsafe_base64_encode, urlsafe_base64_decode
from django.utils.encoding import force_bytes, force_str
from django.core.mail import EmailMessage

from .forms import *
from .decorators import user_not_authenticated
from .tokens import account_activation_token

from .forms import *
from .models import UserBase
from project.models import *
from django.db.models import Q

def staff_view(request):
    q = request.GET.get('q') if request.GET.get('q') != None else''
    projects = Project.objects.filter(Q(company__name__icontains=q) | Q(title__icontains=q) | Q(description__icontains=q), project_status='Pending')
    context = {'projects':projects}
    return render(request, 'home.html', context)

def customer_view(request):
    q = request.GET.get('q') if request.GET.get('q') != None else''
    projects = Project.objects.filter(Q(company__name__icontains=q) | Q(title__icontains=q) | Q(description__icontains=q),created_by=request.user)
    context = {'projects':projects}
    return render(request, 'home.html', context)    

@login_required
def dashboard(request):
    if request.user.is_staff:
      return staff_view(request)
    else:
        return customer_view(request)

@login_required
def edit_details(request):
    if request.method == 'POST':
        user_form = UserEditForm(instance=request.user, data=request.POST)

        if user_form.is_valid():
            user_form.save()
    else:
        user_form = UserEditForm(instance=request.user)

    return render(request,
                  'account/user/edit_details.html', {'user_form': user_form})
    
@login_required
def delete_user(request):
    user = UserBase.objects.get(user_name=request.user)
    user.is_active = False
    user.save()
    logout(request)
    return redirect('account:login')

def account_activate(request, uidb64, token):
    User = get_user_model()
    try:
        uid = force_str(urlsafe_base64_decode(uidb64))
        user = User.objects.get(pk=uid)
    except:
        user = None

    if user is not None and account_activation_token.check_token(user, token):
        user.is_active = True
        user.save()

        messages.success(request, "Thank you for your email confirmation. Now you can login your account.")
        return redirect('account:login')
    else:
        messages.error(request, "Activation link is invalid!")

    return redirect('project:home')

def activateEmail(request, user, to_email):
    mail_subject = "Activate your user account."
    message = render_to_string('account/registration/account_activation_email.html', {
        'user': user.username,
        'domain': get_current_site(request).domain,
        'uid': urlsafe_base64_encode(force_bytes(user.pk)),
        'token': account_activation_token.make_token(user),
        "protocol": 'https' if request.is_secure() else 'http'
    })
    email = EmailMessage(mail_subject, message, to=[to_email])
    if email.send():
        messages.success(request, f'Dear {user}, please go to you email <b>{to_email} inbox and click on \
                received activation link to confirm and complete the registration. Note: Check your spam folder.')
    else:
        messages.error(request, f'Problem sending email to {to_email}, check if you typed it correctly.')


def account_register(request):
    if request.method == "POST":
        form = RegistrationForm(request.POST)
        if form.is_valid():
            user = form.save(commit=False)
            user.email = form.cleaned_data['email']
            user.set_password(form.cleaned_data['password'])
            user.is_active=False
            user.save()
            activateEmail(request, user, form.cleaned_data.get('email'))
            return redirect('project:home')

        else:
            for error in list(form.errors.values()):
                messages.error(request, error)

    else:
        form = RegistrationForm()

    return render(
        request=request,
        template_name='account/registration/register.html',
        context={"form": form}
        )

def Logout(request):
    logout(request)
    return redirect('account:login')



