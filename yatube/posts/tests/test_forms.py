import shutil
import tempfile
from http import HTTPStatus

from django.conf import settings
from django.test import TestCase, Client, override_settings
from django.contrib.auth import get_user_model
from django.urls import reverse
from django.core.files.uploadedfile import SimpleUploadedFile
from django.core.cache import cache

from posts.models import Post, Group

TEMP_MEDIA_ROOT = tempfile.mkdtemp(dir=settings.BASE_DIR)

User = get_user_model()


@override_settings(MEDIA_ROOT=TEMP_MEDIA_ROOT)
class StaticViewTests(TestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.user = User.objects.create(
            username='User'
        )
        cls.group = Group.objects.create(
            title='Название группы',
            slug='test-slug',
            description='Описание группы'
        )
        Group.objects.create(
            title='Название группы 2',
            slug='test-slug-2',
            description='Описание группы 2'
        )
        cls.post = Post.objects.create(
            text='Текст поста',
            author=cls.user,
            group=cls.group,
        )

    @classmethod
    def tearDownClass(cls):
        super().tearDownClass()
        shutil.rmtree(TEMP_MEDIA_ROOT, ignore_errors=True)

    def setUp(self):
        # Создаем неавторизованный клиент
        self.guest_client = Client()

        # Создаем авторизованый клиент
        self.authorized_client = Client()
        self.authorized_client.force_login(StaticViewTests.user)

        cache.clear()

    def test_create_post_form(self):
        """Проверяем создание поста при отправке валидной формы"""
        count_post = Post.objects.count()
        small_gif = (
            b'\x47\x49\x46\x38\x39\x61\x02\x00'
            b'\x01\x00\x80\x00\x00\x00\x00\x00'
            b'\xFF\xFF\xFF\x21\xF9\x04\x00\x00'
            b'\x00\x00\x00\x2C\x00\x00\x00\x00'
            b'\x02\x00\x01\x00\x00\x02\x02\x0C'
            b'\x0A\x00\x3B'
        )
        uploaded = SimpleUploadedFile(
            name='small.gif',
            content=small_gif,
            content_type='image/gif'
        )
        form_data = {
            'text': 'Тестовый текст',
            'group': 1,
            'image': uploaded
        }
        # Авторизованный пользователь
        response = self.authorized_client.post(
            reverse('posts:post_create'),
            data=form_data,
            follow=True
        )
        self.assertEqual(response.status_code, HTTPStatus.OK)
        self.assertRedirects(
            response,
            f'/profile/{StaticViewTests.user.username}/'
        )
        self.assertEqual(Post.objects.count(), count_post + 1)

        # Анонимный пользователь
        count_post = Post.objects.count()
        response = self.guest_client.post(
            reverse('posts:post_create'),
            data=form_data,
            follow=True
        )
        self.assertEqual(Post.objects.count(), count_post)

    def test_edit_post_form(self):
        """Проверяем редактирование поста при отправке валидной формы"""
        form_data = {
            'text': 'Измененный Тестовый текст',
            'group': 2
        }

        post_text = StaticViewTests.post.text
        post_group = StaticViewTests.group.id

        # Авторизованный пользователь
        self.authorized_client.post(
            reverse('posts:post_edit', kwargs={'post_id': 1}),
            data=form_data,
            follow=True
        )
        edit_post_text = Post.objects.get(pk=1).text
        edit_post_group = Post.objects.get(pk=1).group.id

        self.assertNotEqual(post_text, edit_post_text)
        self.assertNotEqual(post_group, edit_post_group)
        self.assertEqual(edit_post_text, 'Измененный Тестовый текст')
        self.assertEqual(edit_post_group, 2)
        self.assertEqual(Post.objects.filter(group=1).count(), 0)
        self.assertEqual(Post.objects.filter(group=2).count(), 1)

        # Анонимный пользователь
        form_data = {
            'text': 'Измененный анонимом текст',
            'group': 1
        }
        self.guest_client.post(
            reverse('posts:post_edit', kwargs={'post_id': 1}),
            data=form_data,
            follow=True
        )
        self.assertNotEqual(edit_post_text, form_data['text'])
        self.assertNotEqual(edit_post_group, 1)
