from django import forms
from django.contrib.auth.models import User
from django.contrib.auth.forms import UserCreationForm, AuthenticationForm, PasswordResetForm
from .models import Profile
from django.contrib.auth import password_validation
from django.core.exceptions import ValidationError
from django.core.mail import EmailMultiAlternatives, get_connection
from django.template.loader import render_to_string
from .tasks import password_reset_send_mail_task

import re

email_val = r'^[a-zA-Z0-9]([A-Za-z0-9]+[._-])*[A-Za-z0-9_]+@[A-Za-z0-9-_]+(\.[A-Z|a-z]{2,})+$'


class UserRegisterForm(UserCreationForm):
    email = forms.EmailField(required=True, widget=forms.TextInput(attrs={'class': 'form-control text-center',
                                                                          'placeholder': 'Введите почту'}))

    username = forms.CharField(required=True, max_length=15, label='Введите логин',
                               help_text='Нельзя вводить символы @, /, _.',
                               widget=forms.TextInput(attrs={'class': 'form-control text-center',
                                                             'placeholder': 'Введите логин'}))

    password1 = forms.CharField(required=True, label='Введтие пароль', help_text='Пароль должен быть длинным',
                                widget=forms.PasswordInput(attrs={'class': 'form-control text-center'}))

    class Meta:
        model = User
        fields = ['username', 'email', 'password1']

    def clean_password1(self):
        password1 = self.cleaned_data.get('password1')
        try:
            password_validation.validate_password(password1, self.instance)
        except forms.ValidationError as error:
            self.add_error('password1', error)
        return password1

    def clean_email(self):
        email = self.cleaned_data['email']
        if not re.match(email_val, email):
            raise ValidationError('Проверьте правильность ввода email')
        return email

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        del self.fields['password2']


class UserUpdateForm(forms.ModelForm):
    email = forms.EmailField(required=True, label='',
                             widget=forms.TextInput(attrs={'class': 'form-control text-center',
                                                           'placeholder': 'Введите почту'}))

    username = forms.CharField(required=True, label='',
                               widget=forms.TextInput(
                                   attrs={'class': 'form-control text-center', 'placeholder': 'Введите логин'}))

    class Meta:
        model = User
        fields = ['email', 'username']


class ProfileImageForm(forms.ModelForm):
    img = forms.ImageField(
        label="",
        required=True,
        widget=forms.FileInput(
            attrs={'class': 'form-control text-center'}),

    )

    class Meta:
        model = Profile
        fields = ['img']


class AuthForm(AuthenticationForm):
    username = forms.CharField(
        widget=forms.TextInput(attrs={'class': 'form-control text-center', 'placeholder': 'Введите логин'}))
    password = forms.CharField(label='Пароль пользователя',
                               widget=forms.PasswordInput(
                                   attrs={'class': 'form-control text-center', 'placeholder': 'Введите пароль'}))

    class Meta:
        model = User


class EmailValidationPasswordResetView:

    def clean_email(self):
        email = self.cleaned_data['email']
        if not re.match(email_val, email):
            raise ValidationError('Введите верный email')
        elif not User.objects.filter(email=email).exists():
            raise ValidationError("Пользователя с такой почтой не существует")
        return email


# class CustomPasswordResetForm(EmailValidationPasswordResetView, PasswordResetForm):
#     email = forms.EmailField(required=False, widget=forms.TextInput(attrs={'class': 'form-control text-center',
#                                                                            'placeholder': 'Введите почту'}))
#
#     def render_subject(self):
#         return "Сброс пароля"
#
#     def render_email(self, email_template_name, context):
#         email_body = render_to_string(email_template_name, context)
#         return email_body
#
#     def send_mail(self, subject_template_name,
#                   email_template_name, context,
#                   from_email,
#                   to_email,
#                   html_email_template_name=None):
#
#         subject = self.render_subject()
#         body = self.render_email(email_template_name, context)
#         email_message = EmailMultiAlternatives(subject, body, from_email, [to_email])
#
#         if html_email_template_name is not None:
#             html_email = self.render_html_email(html_email_template_name, context)
#             email_message.attach_alternative(html_email, 'text/html')
#
#         email_settings_db = EmailSettings.objects.filter(is_active='True').first()
#         if email_settings_db:
#             email_message.connection = get_connection(
#                 backend=settings.EMAIL_BACKEND,
#                 host=email_settings_db.host_email,
#                 port=email_settings_db.port_email,
#                 username=email_settings_db.name_email,
#                 password=email_settings_db.password_email,
#                 use_tls=settings.EMAIL_USE_TLS,
#             )
#
#         email_message.send()


class CustomPasswordResetForm(EmailValidationPasswordResetView, PasswordResetForm):
    email = forms.EmailField(required=False, widget=forms.TextInput(attrs={'class': 'form-control text-center',
                                                                           'placeholder': 'Введите почту'}))



    def render_email(self, email_template_name, context):
        email_body = render_to_string(email_template_name, context)
        return email_body

    def send_mail(self, subject_template_name,
                  email_template_name, context,
                  from_email,
                  to_email,
                  html_email_template_name=None):

        subject = "Сброс пароля"
        body = self.render_email(email_template_name, context)
        password_reset_send_mail_task.delay(subject, body, from_email, to_email, html_email_template_name)
