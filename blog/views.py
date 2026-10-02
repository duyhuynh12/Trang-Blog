from django.db import connection
from django.shortcuts import render, redirect
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from .models import Post
from django.contrib.auth import authenticate, login, logout, update_session_auth_hash
import logging

logger = logging.getLogger('blog.security')


def get_client_ip(request):
    return request.META.get('HTTP_X_FORWARDED_FOR') or request.META.get('REMOTE_ADDR')


# 1. Trang chủ + Tìm kiếm (Chứa lỗ hổng SQLi & Reflected XSS)
def home_and_search(request):
    query = request.GET.get('q', '')
    ip = get_client_ip(request)

    if query:
        logger.info(f"SEARCH_QUERY | Query: '{query}' | IP: {ip}")
        results = []
        try:
            with connection.cursor() as cursor:
                # LỖ HỔNG SQLi: Ghép chuỗi trực tiếp
                raw_sql = f"SELECT id, title, content, attachment FROM blog_post WHERE title LIKE '%{query}%' ORDER BY id DESC"
                cursor.execute(raw_sql)
                results = cursor.fetchall()
        except Exception as e:
            logger.error(f"SQL_ERROR | Query: '{query}' | IP: {ip} | Detail: {str(e).splitlines()[0]}")
    else:
        # Hiển thị toàn bộ bài viết khi không tìm kiếm
        with connection.cursor() as cursor:
            cursor.execute("SELECT id, title, content, attachment FROM blog_post ORDER BY id DESC")
            results = cursor.fetchall()

    return render(request, 'home.html', {'results': results, 'query': query})


# 2. Đăng nhập (Dùng để thực hành bắt log Brute-force)
def user_login(request):
    ip = get_client_ip(request)
    error = None
    if request.method == 'POST':
        u = request.POST.get('username')
        p = request.POST.get('password')
        user = authenticate(request, username=u, password=p)
        if user is not None:
            login(request, user)
            logger.info(f"LOGIN_SUCCESS | User: '{u}' | IP: {ip}")
            return redirect('home')
        else:
            # Log quan trọng để SIEM phát hiện tấn công dò mật khẩu (Brute-force)
            logger.warning(f"LOGIN_FAILED | User: '{u}' | IP: {ip}")
            error = "Tài khoản hoặc mật khẩu không chính xác!"
    return render(request, 'login.html', {'error': error})


# 3. Đăng xuất
def user_logout(request):
    ip = get_client_ip(request)
    if request.user.is_authenticated:
        logger.info(f"LOGOUT | User: '{request.user.username}' | IP: {ip}")
    logout(request)
    return redirect('home')


# 4. Đăng bài & Upload File (Chứa lỗ hổng Unrestricted File Upload & Stored XSS)
@login_required(login_url='/login/')
def create_post(request):
    ip = get_client_ip(request)
    if request.method == 'POST':
        title = request.POST.get('title')
        content = request.POST.get('content')
        uploaded_file = request.FILES.get('attachment')

        # LỖ HỔNG UPLOAD: Không kiểm tra đuôi file (cho phép up .php, .py, .html, .exe...)
        post = Post.objects.create(title=title, content=content, attachment=uploaded_file)

        file_name = uploaded_file.name if uploaded_file else "None"
        logger.info(
            f"POST_CREATED | User: '{request.user.username}' | Title: '{title}' | File: '{file_name}' | IP: {ip}")
        return redirect('home')

    return render(request, 'create_post.html')


@login_required(login_url='/login/')
def change_password(request):
    ip = get_client_ip(request)
    error = None
    success = None
    if request.method == 'POST':
        old_p = request.POST.get('old_password')
        new_p = request.POST.get('new_password')

        if request.user.check_password(old_p):
            request.user.set_password(new_p)
            request.user.save()
            update_session_auth_hash(request, request.user)  # Giữ trạng thái đăng nhập
            logger.info(f"PASSWORD_CHANGED | User: '{request.user.username}' | Status: SUCCESS | IP: {ip}")
            success = "Đổi mật khẩu thành công!"
        else:
            logger.warning(
                f"PASSWORD_CHANGE_FAILED | User: '{request.user.username}' | Reason: Wrong old password | IP: {ip}")
            error = "Mật khẩu cũ không chính xác!"

    return render(request, 'change_password.html', {'error': error, 'success': success})


# 6. Hàm chủ động gây lỗi hệ thống (Dùng để kiểm thử log SYSTEM_ERROR)
def trigger_error(request):
    # Chia cho 0 để tạo lỗi ZeroDivisionError (HTTP 500)
    return 1 / 0