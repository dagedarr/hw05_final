from http import HTTPStatus

from django.contrib.auth import get_user_model
from django.core.cache import cache
from django.test import Client, TestCase
from django.urls import reverse

from posts.models import Group, Post

User = get_user_model()


class StaticURLTests(TestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        # Создадим запись в БД для проверки доступности адреса group/<slug>
        cls.author = User.objects.create_user(username='author')
        cls.user = User.objects.create_user(username='HasNoName')

        cls.group = Group.objects.create(
            title='Тестовый заголовок',
            slug='test-slug',
            description='Тестовое описание'
        )

        cls.post = Post.objects.create(
            text='Тестовый текст',
            group=cls.group,
            author=cls.author
        )

        cls.page_names_urls = {
            'index': reverse('posts:index'),
            'group': reverse('posts:group_list',
                             kwargs={'slug': cls.group.slug}),
            'profile': reverse('posts:profile',
                               kwargs={'username': cls.user.username}),
            'post_detail': reverse('posts:post_detail',
                                   kwargs={'post_id': cls.post.id}),
            'post_edit': reverse('posts:post_edit',
                                 kwargs={'post_id': cls.post.id}),
            'post_create': reverse('posts:post_create'),

            'unexisting_page': '/unexisting_page/',

            'follow_index': reverse('posts:follow_index'),

            'follow': reverse('posts:profile_follow',
                               kwargs={'username': cls.author.username}),

            'post_author_profile': reverse('posts:profile',
                               kwargs={'username': cls.author.username}),

            'unfollow': reverse('posts:profile_unfollow',
                               kwargs={'username': cls.author.username}),

            'add_comment': reverse('posts:add_comment',
                                   kwargs={'post_id': cls.post.id}),
        }

    def setUp(self):
        # Создание гостя
        self.guest_client = Client()
        # Создание авторизованного пользователя
        self.authorized_client = Client()
        self.authorized_client.force_login(self.user)
        # Создание автора
        self.author_client = Client()
        self.author_client.force_login(self.author)

        cache.clear()

    def test_post_pages_available_for_guests(self):
        """Cтраницы: главная, группы, профиль и детали поста доступны всем."""

        for url in list(self.page_names_urls.values())[:4]:
            with self.subTest():
                response = self.guest_client.get(url)
                self.assertEqual(response.status_code, HTTPStatus.OK)

    def test_post_edit_available_for_author(self):
        """"Редактор поста доступен только автору"""
        url = self.page_names_urls['post_edit']
        response = self.author_client.get(url)
        self.assertEqual(response.status_code, HTTPStatus.OK)

    def test_create_post_available_for_auth(self):
        """"Создание поста доступно авторизованному пользователю"""

        url = self.page_names_urls['post_create']
        response = self.authorized_client.get(url)
        self.assertEqual(response.status_code, HTTPStatus.OK)

    def page404_available(self):
        """"Переход на несуществующую страницу дает 404"""
        url = self.page_names_urls['unexisting_page']
        response = self.guest_client.get(url)
        self.assertEqual(response.status_code, HTTPStatus.NOT_FOUND)

    def test_follow_feed_available_for_auth(self):  # Добавлено
        """"Лента подписок доступна авторизованному пользователю"""
        url = self.page_names_urls['follow_index']
        response = self.authorized_client.get(url)
        self.assertEqual(response.status_code, HTTPStatus.OK)

    def test_follow_author_available_for_auth(self):  # Добавлено
        """"Авторизованный пользователь может подписаться"""
        url = self.page_names_urls['follow']
        response = self.authorized_client.get(url)
        expected_url = self.page_names_urls['post_author_profile']
        self.assertRedirects(
            response=response,
            expected_url=expected_url,
            status_code=HTTPStatus.FOUND,
            target_status_code=HTTPStatus.OK,
        )

    def test_unfollow_author_available_for_auth(self):  # Добавлено
        """"Авторизованный пользователь может отписаться"""
        # Сначала подписались
        follow_url = self.page_names_urls['follow']
        self.authorized_client.get(follow_url)

        # Потом отписались
        unfollow_url = self.page_names_urls['unfollow']
        response = self.authorized_client.get(unfollow_url)

        expected_url = self.page_names_urls['index']

        self.assertRedirects(
            response=response,
            expected_url=expected_url,
            status_code=HTTPStatus.FOUND,
            target_status_code=HTTPStatus.OK,
        )

    def test_add_coment_available_for_auth(self):  # Добавлено
        """"Комментарии доступны авторизованному пользователю"""
        url = self.page_names_urls['add_comment']
        response = self.authorized_client.get(url)

        expected_url = self.page_names_urls['post_detail']

        self.assertRedirects(
            response=response,
            expected_url=expected_url,
            status_code=HTTPStatus.FOUND,
            target_status_code=HTTPStatus.OK,
        )

    def test_urls_uses_correct_template(self):
        """URL-адрес использует соответствующий шаблон."""

        template_url_names = [
            ('posts/index.html', self.page_names_urls['index']),
            ('posts/group_list.html', self.page_names_urls['group']),
            ('posts/profile.html', self.page_names_urls['profile']),
            ('posts/post_detail.html', self.page_names_urls['post_detail']),
            ('posts/create_post.html', self.page_names_urls['post_edit']),
            ('posts/create_post.html', self.page_names_urls['post_create']),

            ('posts/follow.html', self.page_names_urls['follow_index']),  # Добавлено
        ]

        for tempalate_url_couple in template_url_names:
            with self.subTest():
                response = self.authorized_client.get(tempalate_url_couple[1])
                self.assertTemplateUsed(response, tempalate_url_couple[0])
