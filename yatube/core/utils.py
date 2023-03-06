from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger


def paginate(queryset, page, count=10):
    """
    Функция для разбивки объектов запроса на страницы
    """
    paginator = Paginator(queryset, count)

    try:
        results = paginator.page(page)
    except PageNotAnInteger:
        results = paginator.page(1)
    except EmptyPage:
        results = paginator.page(paginator.num_pages)

    return results
