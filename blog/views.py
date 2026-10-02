from django.db import connection
from django.shortcuts import render
import logging

logger = logging.getLogger('blog.security')


def search_blog(request):
    query = request.GET.get('q', '')
    ip = request.META.get('HTTP_X_FORWARDED_FOR') or request.META.get('REMOTE_ADDR')
    logger.info(f"Search query: '{query}' | IP: {ip}")

    results = []
    if query:
        try:
            with connection.cursor() as cursor:
                raw_sql = f"SELECT id, title, content FROM blog_post WHERE title LIKE '%{query}%'"
                cursor.execute(raw_sql)
                results = cursor.fetchall()
        except Exception as e:
            # Ghi log lỗi SQL gọn trên 1 dòng để SIEM dễ phân tích
            logger.error(f"SQL Error with query '{query}' | IP: {ip} | Detail: {str(e).splitlines()[0]}")

    return render(request, 'search_results.html', {'results': results, 'query': query})