# users/views.py

from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import login, authenticate, logout # QUAN TRỌNG: Đảm bảo import logout ở đây
from django.contrib.auth.forms import UserCreationForm, AuthenticationForm
from django.contrib.auth.decorators import login_required
from store.models import Order, OrderItem, Review # Import models từ app 'store'
# (Không cần import messages ở đây nữa nếu không dùng)

# --- Views Đăng ký ---
def register_view(request):
    if request.method == 'POST':
        form = UserCreationForm(request.POST)
        if form.is_valid():
            user = form.save()
            login(request, user)
            return redirect('home') # Chuyển về trang chủ sau khi đăng ký
    else:
        form = UserCreationForm()
    return render(request, 'users/register.html', {'form': form})

# --- Views Đăng nhập ---
def login_view(request):
    error_message = None
    if request.method == 'POST':
        form = AuthenticationForm(request, data=request.POST)
        if form.is_valid():
            username = form.cleaned_data.get('username')
            password = form.cleaned_data.get('password')
            user = authenticate(username=username, password=password)
            if user is not None:
                login(request, user)
                # Chuyển hướng đến trang người dùng muốn vào trước đó (nếu có), nếu không về home
                next_url = request.GET.get('next', '/')
                return redirect(next_url)
            else:
                error_message = "Username hoặc mật khẩu không đúng."
        else:
            # Lấy lỗi cụ thể từ form nếu có
            error_message = form.errors.get('__all__', "Username hoặc mật khẩu không đúng.")
    else:
        form = AuthenticationForm()
    return render(request, 'users/login.html', {'form': form, 'error_message': error_message})

# --- Views Đăng xuất (QUAN TRỌNG) ---
def logout_view(request):
    logout(request) # Gọi hàm logout chuẩn của Django
    # (Không cần thêm message ở đây, cứ về home là đủ)
    return redirect('home') # Chuyển về trang chủ

# --- View Lịch sử Đơn hàng ---
@login_required
def order_history_view(request):
    orders = Order.objects.filter(user=request.user).order_by('-created_at')
    context = {'orders': orders}
    return render(request, 'users/order_history.html', context)

# --- View Chi tiết Đơn hàng ---
@login_required
def order_detail_view(request, order_id):
    order = get_object_or_404(Order, id=order_id, user=request.user)
    order_items = order.items.all()

    item_review_status = {}
    if order.status == 'Hoàn thành':
        for item in order_items:
            has_reviewed = Review.objects.filter(
                product=item.product,
                user=request.user
            ).exists()
            item_review_status[item.id] = has_reviewed

    context = {
        'order': order,
        'order_items': order_items,
        'item_review_status': item_review_status
    }
    return render(request, 'users/order_detail.html', context)