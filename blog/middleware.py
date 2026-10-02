import logging

logger = logging.getLogger('blog.security')

class SOCExceptionLoggingMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        return self.get_response(request)

    def process_exception(self, request, exception):
        ip = request.META.get('HTTP_X_FORWARDED_FOR') or request.META.get('REMOTE_ADDR')
        user = request.user.username if request.user.is_authenticated else 'Anonymous'
        # Ghi nhận sự kiện SYSTEM_ERROR gọn trên 1 dòng
        logger.critical(
            f"SYSTEM_ERROR | User: '{user}' | Path: '{request.path}' | "
            f"Exception: {type(exception).__name__}: {str(exception).splitlines()[0]} | IP: {ip}"
        )
        return None