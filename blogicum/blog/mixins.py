from django.contrib.auth.mixins import UserPassesTestMixin
from django.contrib.auth.models import User
from django.core.paginator import Paginator
from django.db.models import Count
from django.shortcuts import get_object_or_404
from django.utils import timezone

from .constants import NUMBER_OF_POSTS
from .models import Post


from django import forms
from django.core.exceptions import ValidationError
from django.utils.safestring import mark_safe


class AgreementMixin(forms.Form):
    agree_to_privacy = forms.BooleanField(
        label=mark_safe(
            'Нажимая на кнопку, вы соглашаетесь с '
            '<a href="/pages/privacy/" target="_blank">политикой конфиденциальности</a>.'
        ),
        required=True,
        widget=forms.CheckboxInput(attrs={'class': 'form-check-input'})
    )

    def clean_agree_to_privacy(self):
        if not self.cleaned_data.get('agree_to_privacy'):
            raise ValidationError(
                "Пожалуйста, поставьте галочку, чтобы подтвердить ваше согласие с политикой конфиденциальности."
            )
        return self.cleaned_data['agree_to_privacy']


class PostQueryMixin:
    def get_filtered_posts(self, author=None, published_only=False):
        queryset = Post.objects.select_related(
            'author', 'category', 'location')
        if author:
            queryset = queryset.filter(author=author)
        if published_only:
            queryset = queryset.filter(
                is_published=True,
                pub_date__lte=timezone.now(),
                category__is_published=True
            )
        return self.add_comment_count(queryset.order_by('-pub_date'))

    def add_comment_count(self, posts):
        return posts.annotate(comment_count=Count('comments'))


class AuthorRequiredMixin(UserPassesTestMixin):
    def test_func(self):
        obj = self.get_object()
        return self.request.user == obj.author


class PaginatorMixin:
    paginate_by = NUMBER_OF_POSTS

    def get_paginated_context(self, queryset):
        # строка paginate_by =... служит как "страховка" на случай,
        # если paginate_by не будет установлен в контексте вызова
        # без этой строки валятся почти все тесты
        paginate_by = self.paginate_by or NUMBER_OF_POSTS
        paginator = Paginator(queryset, paginate_by)
        page_number = self.request.GET.get('page')
        page_obj = paginator.get_page(page_number)
        return {
            'page_obj': page_obj,
            'is_paginated': page_obj.has_other_pages(),
        }


class UserPostQueryMixin(PostQueryMixin):
    def get_user_posts(self):
        user = get_object_or_404(User, username=self.kwargs.get('username'))
        if self.request.user == user:
            return self.get_filtered_posts(author=user)
        return self.get_filtered_posts(author=user, published_only=True)
