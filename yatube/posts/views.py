from django.shortcuts import (
    render, get_object_or_404, redirect
)
from django.contrib.auth import get_user_model
from django.contrib.auth.decorators import login_required

from .models import Post, Group, Follow
from .forms import PostForm, CommentForm
from core.utils import paginate


User = get_user_model()


def index(request):
    """Вью для отображения главной страницы с публикациями"""
    template: str = 'posts/index.html'
    post_list = Post.objects.select_related('author').all()
    page_number = request.GET.get('page')
    page_obj = paginate(post_list, page_number)

    context: dict = {
        'page_obj': page_obj,
    }
    return render(request, template, context)


def group_posts(request, slug):
    """Вью для отображения страниц с постами конкретной группы"""
    template: str = 'posts/group_list.html'
    group = get_object_or_404(Group, slug=slug)
    post_list = group.posts.all()
    page_number = request.GET.get('page')
    page_obj = paginate(post_list, page_number)

    context: dict = {
        'group': group,
        'page_obj': page_obj,
    }
    return render(request, template, context)


def profile(request, username):
    template = 'posts/profile.html'
    author = get_object_or_404(User, username=username)
    following = request.user.is_authenticated and Follow.objects.filter(
        user=request.user, author=author
    ).exists()
    post_list = author.posts.all()
    post_count = post_list.count()
    page_number = request.GET.get('page')
    page_obj = paginate(post_list, page_number)

    context = {
        'author': author,
        'page_obj': page_obj,
        'post_count': post_count,
        'following': following,
    }
    return render(request, template, context)


def post_detail(request, post_id):
    template = 'posts/post_detail.html'
    post = get_object_or_404(Post, pk=post_id)
    form = CommentForm()
    post_count = post.author.posts.count()
    context = {
        'post': post,
        'post_count': post_count,
        'form': form,
    }
    return render(request, template, context)


@login_required
def post_create(request):
    form = PostForm(
        request.POST or None,
        files=request.FILES or None
    )
    if form.is_valid():
        post = form.save(commit=False)
        post.author = request.user
        post.save()
        return redirect(f'/profile/{post.author}/')
    return render(request, 'posts/create_post.html', {
        'form': form,
    })


@login_required
def post_edit(request, post_id):
    post = get_object_or_404(Post, pk=post_id)
    if post.author != request.user:
        return redirect('posts:post_detail', post_id)
    form = PostForm(
        request.POST or None,
        files=request.FILES or None,
        instance=post
    )
    is_edit = True
    context = {
        'form': form,
        'is_edit': is_edit,
        'post': post,
    }
    if form.is_valid():
        form.save()
        return redirect('posts:post_detail', post_id)
    return render(request, 'posts/create_post.html', context)


@login_required
def add_comment(request, post_id):
    post = get_object_or_404(Post, pk=post_id)
    form = CommentForm(request.POST or None)
    if form.is_valid():
        comment = form.save(commit=False)
        comment.author = request.user
        comment.post = post
        comment.save()
    return redirect('posts:post_detail', post_id=post_id)


@login_required
def follow_index(request):
    following_list = Follow.objects.values_list('author').filter(
        user=request.user
    )
    post_list = Post.objects.filter(author__in=following_list)
    page_number = request.GET.get('page')
    page_obj = paginate(post_list, page_number)
    context = {
        'page_obj': page_obj
    }
    return render(request, 'posts/follow.html', context=context)


@login_required
def profile_follow(request, username):
    author = get_object_or_404(User, username=username)
    if author != request.user:
        Follow.objects.get_or_create(user=request.user, author=author)
    return redirect('posts:follow_index')


@login_required
def profile_unfollow(request, username):
    author = User.objects.get(username=username)
    follow = Follow.objects.get(user=request.user, author=author)
    follow.delete()
    return redirect('posts:follow_index')
