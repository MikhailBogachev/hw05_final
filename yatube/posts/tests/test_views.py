import shutil
import tempfile

from django.conf import settings
from django.test import TestCase, Client, override_settings
from django.contrib.auth import get_user_model
from django.urls import reverse
from django import forms
from django.core.files.uploadedfile import SimpleUploadedFile
from django.core.cache import cache

from posts.models import Post, Group, Comment, Follow

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
        cls.user_2 = User.objects.create(
            username='User_2'
        )
        cls.group = Group.objects.create(
            title='Название группы',
            slug='test-slug',
            description='Описание группы'
        )
        small_gif = (
            b'\x47\x49\x46\x38\x39\x61\x02\x00'
            b'\x01\x00\x80\x00\x00\x00\x00\x00'
            b'\xFF\xFF\xFF\x21\xF9\x04\x00\x00'
            b'\x00\x00\x00\x2C\x00\x00\x00\x00'
            b'\x02\x00\x01\x00\x00\x02\x02\x0C'
            b'\x0A\x00\x3B'
        )
        cls.uploaded = SimpleUploadedFile(
            name='small.gif',
            content=small_gif,
            content_type='image/gif'
        )
        cls.post = Post.objects.create(
            text='Текст поста',
            author=cls.user,
            group=cls.group,
            image=cls.uploaded
        )
        Comment.objects.create(
            post=cls.post,
            author=cls.user,
            text='Текст комментария'
        )
        Follow.objects.create(
            user=cls.user_2,
            author=cls.user
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
        self.authorized_client_2 = Client()
        self.authorized_client_2.force_login(StaticViewTests.user_2)
        cache.clear()

        Follow.objects.all().delete()
        Follow.objects.create(
            user=StaticViewTests.user_2,
            author=StaticViewTests.user
        )

    # Проверяем используемые шаблоны
    def test_pages_uses_correct_template(self):
        """URL-адрес использует соответствующий шаблон."""
        # Собираем в словарь пары "имя_html_шаблона: reverse(name)"
        templates_pages_names = {
            reverse('posts:index'): (
                'posts/index.html'
            ),
            reverse('posts:group_list', kwargs={'slug': 'test-slug'}): (
                'posts/group_list.html'
            ),
            reverse('posts:profile', kwargs={'username': 'User'}): (
                'posts/profile.html'
            ),
            reverse('posts:post_detail', kwargs={'post_id': 1}): (
                'posts/post_detail.html'
            ),
            reverse('posts:post_create'): (
                'posts/create_post.html'
            ),
            reverse('posts:post_edit', kwargs={'post_id': 1}): (
                'posts/create_post.html'
            ),
        }
        for reverse_name, template in templates_pages_names.items():
            with self.subTest(reverse_name=reverse_name):
                response = self.authorized_client.get(reverse_name)
                self.assertTemplateUsed(response, template)

    def post_context_is_correct(self, obj):
        task_text = obj.text
        task_author = obj.author.username
        task_group = obj.group.title
        task_image = obj.image
        self.assertEqual(task_text, StaticViewTests.post.text)
        self.assertEqual(task_author, StaticViewTests.user.username)
        self.assertEqual(task_group, StaticViewTests.group.title)
        self.assertEqual(
            str(task_image).split('/')[1],
            str(StaticViewTests.uploaded)
        )

    def test_index_page_correct_context(self):
        """Шаблон index сформирован с правильным контекстом"""
        response = self.authorized_client.get(reverse('posts:index'))
        first_object = response.context['page_obj'][0]
        self.post_context_is_correct(first_object)

    def test_group_page_correct_context(self):
        """Шаблон group_list сформирован с правильным контекстом"""
        response = self.authorized_client.get(
            reverse('posts:group_list', kwargs={'slug': 'test-slug'})
        )
        first_object = response.context['page_obj'][0]
        group_object = response.context['group']
        task_group_title = group_object.title
        task_group_slug = group_object.slug
        task_group_description = group_object.description

        self.post_context_is_correct(first_object)
        fields = {
            task_group_title: StaticViewTests.group.title,
            task_group_slug: StaticViewTests.group.slug,
            task_group_description: StaticViewTests.group.description
        }
        for value, expected in fields.items():
            with self.subTest(value=value):
                self.assertEqual(value, expected)

    def test_profile_page_correct_context(self):
        """Шаблон profile сформирован с правильным контекстом"""
        response = self.authorized_client.get(
            reverse('posts:profile', kwargs={'username': 'User'})
        )
        first_object = response.context['page_obj'][0]
        author_object = response.context['author']
        post_count_object = response.context['post_count']
        task_author_username = author_object.username
        task_post_count = post_count_object

        self.post_context_is_correct(first_object)
        self.assertEqual(task_author_username, StaticViewTests.user.username)
        self.assertEqual(task_post_count, 1)

    def test_post_detail_page_correct_context(self):
        """Шаблон post_detail сформирован с правильным контекстом"""
        response = self.authorized_client.get(
            reverse('posts:post_detail', kwargs={'post_id': 1})
        )
        first_object = response.context['post']
        post_count_object = response.context['post_count']
        task_post_count = post_count_object

        self.post_context_is_correct(first_object)
        self.assertEqual(task_post_count, 1)

    def test_post_create_page_correct_context(self):
        """Шаблон post_create сформирован с правильным контекстом"""
        response = self.authorized_client.get(
            reverse('posts:post_create')
        )
        form_fields = {
            'text': forms.fields.CharField,
            'group': forms.fields.ChoiceField,
        }
        for value, expected in form_fields.items():
            with self.subTest(value=value):
                form_field = response.context.get('form').fields.get(value)
                self.assertIsInstance(form_field, expected)

    def test_post_edit_page_correct_context(self):
        """Шаблон post_edit сформирован с правильным контекстом"""
        response = self.authorized_client.get(
            reverse('posts:post_edit', kwargs={'post_id': 1})
        )

        form_fields = {
            'text': forms.fields.CharField,
            'group': forms.fields.ChoiceField,
        }
        for value, expected in form_fields.items():
            with self.subTest(value=value):
                form_field = response.context.get('form').fields.get(value)
                self.assertIsInstance(form_field, expected)

        post_obj = response.context['post']
        key_is_edit = response.context['is_edit']
        task_post_text = post_obj.text
        task_post_author = post_obj.author.username
        task_is_edit = key_is_edit

        self.assertEqual(task_post_text, StaticViewTests.post.text)
        self.assertEqual(task_post_author, StaticViewTests.user.username)
        self.assertEqual(task_is_edit, True)

    def test_cache_index_page(self):
        """Кеширование главной страницы работает"""
        response = self.authorized_client.get(reverse('posts:index'))
        self.assertContains(response, StaticViewTests.post.text)

        Post.objects.all().delete()
        response = self.authorized_client.get(reverse('posts:index'))
        self.assertContains(response, StaticViewTests.post.text)

        cache.clear()
        response = self.authorized_client.get(reverse('posts:index'))
        self.assertNotContains(response, StaticViewTests.post.text)

    def test_follow_unfollow(self):
        """
        Авторизованный пользователь может \
        подписаться на авторов
        """
        sub = Follow.objects.filter(
            user=StaticViewTests.user,
            author=StaticViewTests.user_2
        )
        self.assertFalse(sub.count())
        self.authorized_client.get(
            reverse(
                'posts:profile_follow',
                kwargs={'username': StaticViewTests.user_2}
            )
        )
        sub = Follow.objects.filter(
            user=StaticViewTests.user,
            author=StaticViewTests.user_2
        )
        self.assertTrue(sub.count())

    def test_unfollow(self):
        """
        Авторизованный пользователь может \
        подписаться на авторов
        """
        sub = Follow.objects.filter(
            user=StaticViewTests.user_2,
            author=StaticViewTests.user
        )
        self.assertTrue(sub.count())
        self.authorized_client_2.get(
            reverse(
                'posts:profile_unfollow',
                kwargs={'username': StaticViewTests.user}
            )
        )
        sub = Follow.objects.filter(
            user=StaticViewTests.user_2,
            author=StaticViewTests.user
        )
        self.assertFalse(sub.count())

    def test_follow_page(self):
        """
        Новая запись появляется в ленте \
        у подписавшегося на автора пользователя, \
        и не появляется у неподписанного
        """
        response = self.authorized_client_2.get(reverse('posts:follow_index'))
        self.assertTrue(response.context.get('page_obj', 0))
        response = self.authorized_client.get(reverse('posts:follow_index'))
        self.assertFalse(response.context.get('page_obj', 0))


class PaginatorViewTests(TestCase):
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
        for num_post in range(1, 16):
            Post.objects.create(
                text=f'Текст поста {num_post}',
                author=cls.user,
                group=cls.group
            )

    def setUp(self):
        # Создаем неавторизованный клиент
        self.guest_client = Client()
        # Создаем авторизованый клиент
        self.authorized_client = Client()
        self.authorized_client.force_login(PaginatorViewTests.user)

    def test_index_first_page(self):
        """Шаблон index выводит нужное кол-во постов на первую страницу"""
        response = self.authorized_client.get(
            reverse('posts:index')
        )
        self.assertEqual(len(response.context['page_obj']), 10)

    def test_index_second_page(self):
        """Шаблон index выводит нужное кол-во постов на вторую страницу"""
        response = self.authorized_client.get(
            reverse('posts:index') + '?page=2'
        )
        self.assertEqual(len(response.context['page_obj']), 5)

    def test_group_post_first_page(self):
        """Шаблон group_post выводит нужное кол-во постов на первую страницу"""
        response = self.authorized_client.get(
            reverse('posts:group_list', kwargs={'slug': 'test-slug'})
        )
        self.assertEqual(len(response.context['page_obj']), 10)

    def test_group_post_second_page(self):
        """Шаблон group_post выводит нужное кол-во постов на вторую страницу"""
        response = self.authorized_client.get(
            reverse(
                'posts:group_list', kwargs={'slug': 'test-slug'}
            )
            + '?page=2'
        )
        self.assertEqual(len(response.context['page_obj']), 5)

    def test_profile_first_page(self):
        """Шаблон profile выводит нужное кол-во постов на первую страницу"""
        response = self.authorized_client.get(
            reverse('posts:profile', kwargs={'username': 'User'})
        )
        self.assertEqual(len(response.context['page_obj']), 10)

    def test_profile_second_page(self):
        """Шаблон profile выводит нужное кол-во постов на вторую страницу"""
        response = self.authorized_client.get(
            reverse(
                'posts:profile', kwargs={'username': 'User'}
            )
            + '?page=2'
        )
        self.assertEqual(len(response.context['page_obj']), 5)
