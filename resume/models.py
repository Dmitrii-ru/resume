from datetime import datetime

from core.settings import USE_HTTPS, ALLOWED_HOSTS
from .cache import count_visit
from django.db import models
from django.db.models import Sum, Count
from django.urls import reverse
from django.utils.text import slugify
from pytils.translit import slugify
from ckeditor.fields import RichTextField
from .cache import delete_cache
from PIL import Image

CHOICE_STATUS = [
    ('True', 'Завершен'),
    ('False', 'В работе')
]

CHOICE_EMAIL = [
    (True, 'Использовать почту'),
    (False, 'Не использовать почту')
]


class MyEducation(models.Model):
    name = models.CharField('Название курса', max_length=200)
    school = models.CharField('Школа', max_length=200)
    end = models.CharField('Дата окончания', max_length=20, null=True, blank=True)
    diploma = models.CharField('Ссылка на диплом', max_length=200, null=True, blank=True)
    percent = models.IntegerField('Процент завершения курса')

    def __str__(self):
        return f'{self.name}'

    class Meta:
        verbose_name = "Курс"
        verbose_name_plural = "Курсы"

    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)
        delete_cache(self._meta.model_name)


class AboutMe(models.Model):
    text = RichTextField('О себе', max_length=4000, blank=True, null=True)
    phone = models.CharField('Телефон', max_length=30)
    city = models.CharField('Город', max_length=30)
    mail = models.CharField('Почта', max_length=30)
    name = models.CharField('Имя', max_length=50)
    education_my = models.CharField('Образование не в IT', max_length=500)
    link_HH = models.CharField('HH', max_length=100, null=True, blank=True)

    class Meta:
        verbose_name = "О себе"
        verbose_name_plural = "О себе"

    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)
        delete_cache(self._meta.model_name)

    def __str__(self):
        return f'{self.name}'


class Stack(models.Model):
    name = models.CharField('Название технологии', max_length=20, unique=True)
    slug = models.SlugField('Слаг', null=False, db_index=True, unique=True)

    def __str__(self):
        return f'{self.name}'

    def get_absolute_url(self):
        return reverse('resume_urls:stack', kwargs={'stack_slug': self.slug})

    class Meta:
        verbose_name = "Стэк"
        verbose_name_plural = "Стэки"

    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)
        delete_cache(self._meta.model_name)


class Project(models.Model):
    slug = models.SlugField('Слаг', null=False, blank=True, unique=True)
    stacks = models.ManyToManyField(Stack, verbose_name='Технологии проекта', related_name='project_stacks')
    name = models.CharField('Название проекта', max_length=50, unique=True)
    about = models.CharField('О проекте', max_length=200)
    image = models.ImageField('Ава проекта', upload_to='img', null=True, blank=True, default='default_project.png')
    status = models.CharField('Статус', choices=CHOICE_STATUS, default="True", max_length=5)
    link_git = models.CharField('Ссылка на GitHub', max_length=100, null=True, blank=True)
    link_site = models.CharField('Ссылка на WebSite', max_length=100, null=True, blank=True)
    api = models.CharField('API', max_length=100, null=True, blank=True)

    def get_absolute_url(self):
        return reverse('resume_urls:project_detail', kwargs={'project_slug': self.slug})

    @staticmethod
    def get_protocol_base_url():
        protocol = 'https' if USE_HTTPS else 'http'
        base_url = ALLOWED_HOSTS[0]
        return protocol, base_url

    def api_docs_url(self):
        if self.api:
            protocol, base_url = self.get_protocol_base_url()
            return f"{protocol}://{base_url}:8000/{self.api}"
        return None

    def api_swag_url(self):
        if self.api:
            protocol, base_url = self.get_protocol_base_url()
            return f"{protocol}://{base_url}:8000/{str(self.api).replace('docs','docs-swagger')}"
        return None

    def web_site_url(self):
        if self.link_site:
            protocol, base_url = self.get_protocol_base_url()
            return f"{protocol}://{base_url}:8000/{self.link_site}"
        return None


    def __str__(self):
        return f'{self.name}'

    class Meta:
        verbose_name = "Проект"
        verbose_name_plural = "Проекты"

    def save(self, *args, **kwargs):
        self.slug = slugify(self.name)
        super().save(*args, **kwargs)
        delete_cache(self._meta.model_name)
        if self.image:
            image = Image.open(self.image.path)
            if image.height > 270 or image.width > 270:
                resize = (270, 270)
                image.thumbnail(resize)
                image.save(self.image.path)


class EmailSend(models.Model):
    email = models.CharField('Почта', max_length=50)
    name = models.CharField('Имя', max_length=50)
    date = models.DateField(auto_now_add=True)

    def __str__(self):
        return f'{self.name} - {self.email} - {self.date}'


class CardProject(models.Model):
    project = models.ForeignKey(Project, verbose_name='Проект', on_delete=models.CASCADE)
    title = models.CharField('Тема', max_length=40)
    text = RichTextField('Текст', max_length=10000)

    def __str__(self):
        return f'{self.project} - {self.title}'

    class Meta:
        verbose_name = "Карточка"
        verbose_name_plural = "Карточки"

    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)
        delete_cache(self._meta.model_name)


class EmailSettings(models.Model):
    host_email = models.CharField('Хостинг, пример: smtp.gmail.com', max_length=100)
    name_email = models.CharField('Имя почты, пример: testemailru014@gmail.com', max_length=100)
    password_email = models.CharField('Пароль, пример: 1234dssads12', max_length=100)
    port_email = models.IntegerField('Порт, пример: 587')
    is_active = models.BooleanField('Статус почты', choices=CHOICE_EMAIL, default=False, max_length=5)

    class Meta:
        verbose_name = "Почта"
        verbose_name_plural = "Почты"

    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)
        if self.is_active == True:
            EmailSettings.objects.exclude(id=self.pk).update(is_active=False)

    def __str__(self):
        return f'{self.host_email} - {self.name_email} - {self.port_email} - {self.is_active}'


class UniqueIP(models.Model):
    ip_address = models.GenericIPAddressField()
    date = models.DateField(auto_now_add=True)
    path_client = models.JSONField(default=dict)
    info_client = RichTextField(default='Нет информации')

    class Meta:
        verbose_name = "Посетитель"
        verbose_name_plural = f"Посетители {count_visit()}"

    def __str__(self):
        return f'{self.ip_address}  //  {self.date}  //'


class Feedback(models.Model):
    title = models.CharField('Заголовок ', max_length=33, blank=True)
    text = RichTextField('Текст')
    date = models.DateField(auto_now_add=True)

    def __str__(self):
        return f'{self.title}  - {self.date}'

# def get_aggregate_feedback():
#     return len(Feedback.objects.all())
#
# Feedback._meta.verbose_name_plural = f"Количество feedback {get_aggregate_feedback()}"
