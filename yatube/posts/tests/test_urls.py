from http import HTTPStatus

from django.test import TestCase, Client
from django.contrib.auth import get_user_model

from posts.models import Post, Group

User = get_user_model()


class StaticURLTests(TestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.user = User.objects.create(
            username='User'
        )
        Post.objects.create(
            text='Текст поста',
            author=cls.user
        )
        Group.objects.create(
            title='Нзвание группы',
            slug='test-slug',
            description='Описание группы'
        )

    def setUp(self):
        # Создаем неавторизованный клиент
        self.guest_client = Client()
        # Создаем авторизованый клиент
        self.authorized_client = Client()
        self.authorized_client.force_login(StaticURLTests.user)

    def test_all_public_pages(self):
        """Общедоступные страницы работают"""
        urls = [
            '/', '/group/test-slug/', '/posts/1/', '/profile/User/'
        ]
        for url in urls:
            response = self.guest_client.get(url)
            self.assertEqual(response.status_code, HTTPStatus.OK)

    def test_private_pages(self):
        """Приватные страницы доступны авторизованным пользователям."""
        urls = [
            '/create/', '/posts/1/edit/'
        ]
        for url in urls:
            response = self.authorized_client.get(url)
            self.assertEqual(response.status_code, HTTPStatus.OK)

    def test_private_page_redirect_if_anonymous(self):
        """Приватные страницы перенаправляют анонимного пользователя."""
        urls = [
            '/create/', '/posts/1/edit/', '/posts/1/comment/'
        ]
        for url in urls:
            response = self.guest_client.get(url)
            self.assertRedirects(response, f'/auth/login/?next={url}')

    def test_urls_uses_correct_template(self):
        """URL-адрес использует соответствующий шаблон."""
        templates_url_names = {
            '/': 'posts/index.html',
            '/group/test-slug/': 'posts/group_list.html',
            '/posts/1/': 'posts/post_detail.html',
            '/profile/User/': 'posts/profile.html',
            '/create/': 'posts/create_post.html',
            '/posts/1/edit/': 'posts/create_post.html',
        }
        for address, template in templates_url_names.items():
            with self.subTest(address=address):
                response = self.authorized_client.get(address)
                self.assertTemplateUsed(response, template)

    def test_404_page(self):
        """Несуществующая страница не доступна."""
        response = self.authorized_client.get('/nonexist-page/')
        self.assertEqual(response.status_code, HTTPStatus.NOT_FOUND)
        self.assertTemplateUsed(response, 'core/404.html')
