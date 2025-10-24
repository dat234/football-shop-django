# Imports từ Django
from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.db.models import Q, Avg # Import Avg để tính trung bình
from django.core.paginator import Paginator
from django.utils import timezone

# Import từ project của bạn
from .models import Product, Category, Order, OrderItem, Voucher, Review 

# -----------------------------------------------------------------------------
# GĐ 19: Home (Tìm kiếm, Lọc, Sắp xếp, Phân trang)
# -----------------------------------------------------------------------------
def home(request):
    all_categories = Category.objects.all()
    search_query = request.GET.get('q')
    category_id = request.GET.get('category')
    sort_by = request.GET.get('sort', '-id') # Mặc định mới nhất

    products = Product.objects.all() # Bắt đầu với tất cả

    # Lọc theo tìm kiếm
    if search_query:
        products = products.filter(
            Q(name__icontains=search_query) |
            Q(description__icontains=search_query)
        ).distinct()

    # Lọc theo danh mục
    if category_id:
        products = products.filter(category__id=category_id)

    # Sắp xếp
    if sort_by in ['price_asc', 'price_desc', '-id']:
        if sort_by == 'price_asc':
            products = products.order_by('price')
        elif sort_by == 'price_desc':
            products = products.order_by('-price')
        else:
            products = products.order_by('-id')

    # Phân trang
    query_params = request.GET.copy()
    if 'page' in query_params: del query_params['page']
    query_string = query_params.urlencode()

    paginator = Paginator(products, 12) # 12 sản phẩm/trang
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    context = {
        'page_obj': page_obj,
        'all_categories': all_categories,
        'search_query': search_query,
        'current_category_id': int(category_id) if category_id else None,
        'query_string': query_string,
        'current_sort': sort_by
    }
    return render(request, 'store/home.html', context)

# -----------------------------------------------------------------------------
# GĐ 21 (Sửa đổi logic POST): Trang Chi tiết Sản phẩm
# -----------------------------------------------------------------------------
# --- GĐ 21 (Sửa đổi logic GET và POST): Trang Chi tiết Sản phẩm ---
def product_detail(request, product_id):
    product = get_object_or_404(Product, id=product_id)
    reviews = product.reviews.all()
    average_rating = reviews.aggregate(Avg('rating'))['rating__avg']

    # ----- LOGIC KIỂM TRA ĐIỀU KIỆN REVIEW (SỬA Ở ĐÂY) -----
    can_review = False # Mặc định là không thể review
    has_reviewed = False
    review_message = "" # Tin nhắn giải thích

    if request.user.is_authenticated:
        # 1. Kiểm tra xem đã review chưa
        has_reviewed = Review.objects.filter(product=product, user=request.user).exists()
        if has_reviewed:
            review_message = "Bạn đã đánh giá sản phẩm này rồi."
        else:
            # 2. Nếu chưa review, kiểm tra xem đã mua và hoàn thành chưa
            has_completed_order = Order.objects.filter(
                user=request.user,
                status='Hoàn thành',
                items__product=product
            ).exists()
            if has_completed_order:
                can_review = True # ĐỦ ĐIỀU KIỆN ĐỂ HIỂN THỊ FORM
            else:
                review_message = "Bạn cần mua và nhận hàng thành công trước khi đánh giá."
    else:
        review_message = "Đăng nhập để đánh giá."
    # ----- KẾT THÚC SỬA LOGIC KIỂM TRA -----


    # Xử lý POST để gửi review (Logic POST vẫn giữ nguyên kiểm tra can_actually_review)
    if request.method == 'POST' and request.POST.get('action') == 'submit_review':
        if not request.user.is_authenticated:
             return redirect('login')
        if has_reviewed:
             messages.error(request, "Bạn đã đánh giá sản phẩm này rồi.")
             return redirect('product_detail', product_id=product_id)

        # Kiểm tra lại lần cuối (an toàn)
        can_actually_review = Order.objects.filter(
            user=request.user, status='Hoàn thành', items__product=product
        ).exists()
        if not can_actually_review:
            messages.error(request, "Bạn cần mua và nhận hàng thành công trước khi đánh giá.")
            return redirect('product_detail', product_id=product_id)

        rating = request.POST.get('rating')
        comment = request.POST.get('comment')
        if not rating or not rating.isdigit() or int(rating) not in range(1, 6):
            messages.error(request, "Vui lòng chọn số sao hợp lệ.")
            return redirect('product_detail', product_id=product_id)

        Review.objects.create(
            product=product, user=request.user, rating=int(rating), comment=comment
        )
        messages.success(request, "Cảm ơn bạn đã gửi đánh giá!")
        return redirect('product_detail', product_id=product_id)

    # Context cho GET (Gửi cả 'can_review' và 'review_message')
    context = {
        'product': product,
        'reviews': reviews,
        'average_rating': average_rating,
        'can_review': can_review, # Template sẽ dùng biến này
        'has_reviewed': has_reviewed, # Vẫn cần để hiển thị thông báo "Đã đánh giá"
        'review_message': review_message, # Hiển thị lý do không review được
    }
    return render(request, 'store/product_detail.html', context)
# -----------------------------------------------------------------------------
# GĐ 6 (Sửa đổi): Thêm vào Giỏ hàng
# -----------------------------------------------------------------------------
def add_to_cart(request, product_id):
    # Chỉ xử lý nếu là POST và action là 'add_to_cart'
    if request.method == 'POST' and request.POST.get('action') == 'add_to_cart':
        quantity = int(request.POST.get('quantity', 1)) # Lấy số lượng
        cart = request.session.get('cart', {}) # Lấy giỏ hàng
        product = get_object_or_404(Product, id=product_id) # Lấy sản phẩm
        product_id_str = str(product_id)

        # Logic kiểm tra tồn kho và cập nhật số lượng
        if quantity > 0 and product.stock > 0 : # Thêm kiểm tra stock > 0
            current_quantity = cart.get(product_id_str, 0)
            new_quantity = current_quantity + quantity
            # Không cho thêm quá số lượng tồn kho
            if new_quantity <= product.stock:
                cart[product_id_str] = new_quantity
                messages.success(request, f"Đã thêm {quantity} '{product.name}' vào giỏ hàng thành công!")
            else:
                # Nếu thêm quá, chỉ thêm tối đa số lượng còn lại
                can_add = product.stock - current_quantity
                if can_add > 0:
                    cart[product_id_str] = product.stock
                    messages.warning(request, f"Chỉ còn {product.stock} sản phẩm. Đã thêm tối đa {can_add} '{product.name}' vào giỏ.")
                else:
                    messages.warning(request, f"Sản phẩm '{product.name}' đã ở mức tối đa trong giỏ của bạn.") # Sửa thông báo
        elif product.stock <= 0:
             messages.error(request, f"Sản phẩm '{product.name}' đã hết hàng.")
        else: # quantity <= 0
             messages.error(request, "Số lượng không hợp lệ.")


        request.session['cart'] = cart # Lưu lại giỏ hàng

    # Luôn quay về trang chi tiết sản phẩm (dù là GET hay POST khác action)
    return redirect('product_detail', product_id=product_id)


# --- GĐ 7: Xem Giỏ hàng ---
# (Hàm cart_view không thay đổi)
def cart_view(request):
    cart = request.session.get('cart', {})
    detailed_cart_items = []
    total_price = 0

    for product_id, quantity in list(cart.items()): # Dùng list() để có thể xóa item khi lặp
        try:
            product = Product.objects.get(id=int(product_id))
            # Kiểm tra lại tồn kho khi xem giỏ hàng
            if quantity > product.stock:
                # Nếu số lượng trong giỏ > tồn kho, tự động giảm về mức tồn kho
                cart[product_id] = product.stock
                quantity = product.stock
                messages.warning(request, f"Số lượng '{product.name}' đã được cập nhật do thay đổi tồn kho.")

            if quantity > 0: # Chỉ hiển thị nếu số lượng > 0
                subtotal = product.price * quantity
                detailed_cart_items.append({
                    'product': product,
                    'quantity': quantity,
                    'subtotal': subtotal,
                })
                total_price += subtotal
            else: # Nếu số lượng <= 0, xóa khỏi giỏ
                del cart[product_id]

        except Product.DoesNotExist:
            # Nếu sản phẩm bị xóa, loại bỏ khỏi giỏ hàng
            if product_id in cart: # Thêm kiểm tra trước khi xóa
                del cart[product_id]
                messages.error(request, "Một sản phẩm trong giỏ không còn tồn tại và đã được xóa.")

    request.session['cart'] = cart # Lưu lại giỏ hàng nếu có thay đổi

    context = {
        'cart_items': detailed_cart_items,
        'total_price': total_price,
    }
    return render(request, 'store/cart.html', context)


# --- GĐ 9: Cập nhật Giỏ hàng ---
# (Hàm update_cart không thay đổi)
def update_cart(request, product_id):
    if request.method == 'POST':
        try:
            quantity = int(request.POST.get('quantity'))
        except (ValueError, TypeError):
            quantity = 1 # Hoặc có thể báo lỗi

        cart = request.session.get('cart', {})
        product = get_object_or_404(Product, id=product_id)
        product_id_str = str(product_id)

        if product_id_str in cart:
            if quantity <= 0:
                del cart[product_id_str]
                messages.success(request, f"Đã xóa '{product.name}' khỏi giỏ hàng.")
            elif quantity > product.stock:
                cart[product_id_str] = product.stock
                messages.warning(request, f"Số lượng '{product.name}' vượt quá tồn kho ({product.stock}), đã đặt tối đa.") # Sửa thông báo
            else:
                cart[product_id_str] = quantity
                messages.success(request, f"Đã cập nhật số lượng '{product.name}'.")

        request.session['cart'] = cart

    return redirect('cart_view')


# --- GĐ 20: Checkout (Xử lý Voucher + Đặt hàng) ---
# (Hàm checkout không thay đổi)
def checkout(request):
    cart = request.session.get('cart', {})
    if not cart:
        messages.error(request, "Giỏ hàng của bạn rỗng.")
        return redirect('home')

    # Lấy và kiểm tra lại giỏ hàng (giống cart_view)
    detailed_cart_items = []
    total_price = 0
    cart_changed = False # Cờ để biết giỏ hàng có bị thay đổi không
    for product_id, quantity in list(cart.items()):
        try:
            product = Product.objects.get(id=int(product_id))
            if quantity > product.stock:
                cart[product_id] = product.stock
                quantity = product.stock
                cart_changed = True
            if quantity <= 0:
                if product_id in cart: del cart[product_id] # Thêm kiểm tra
                cart_changed = True
                continue # Bỏ qua sản phẩm này

            subtotal = product.price * quantity
            detailed_cart_items.append({'product': product, 'quantity': quantity, 'subtotal': subtotal})
            total_price += subtotal
        except Product.DoesNotExist:
            if product_id in cart: del cart[product_id] # Thêm kiểm tra
            cart_changed = True

    # Nếu giỏ hàng bị thay đổi, lưu lại và báo lỗi
    if cart_changed:
        request.session['cart'] = cart
        messages.warning(request, "Giỏ hàng của bạn đã được cập nhật do thay đổi về sản phẩm hoặc tồn kho. Vui lòng kiểm tra lại.")
        if not cart: return redirect('home') # Nếu giỏ rỗng thì về home
        return redirect('checkout') # Tải lại checkout

    # Xử lý Voucher (lấy từ session nếu có)
    voucher_code = request.session.get('voucher_code')
    voucher = None
    discount_amount = 0
    if voucher_code:
        try:
            voucher = Voucher.objects.get(code__iexact=voucher_code)
            is_valid, message = voucher.is_valid(total_price)
            if is_valid:
                discount_amount = voucher.discount_amount
            else:
                messages.error(request, message)
                if 'voucher_code' in request.session: del request.session['voucher_code'] # Thêm kiểm tra
                voucher = None
        except Voucher.DoesNotExist:
            messages.error(request, "Mã giảm giá trong session không tồn tại.")
            if 'voucher_code' in request.session: del request.session['voucher_code'] # Thêm kiểm tra

    final_price = total_price - discount_amount

    # Xử lý POST requests
    if request.method == 'POST':
        action = request.POST.get('action')

        # --- Áp dụng / Xóa Voucher ---
        if action == 'apply_voucher':
            code_from_form = request.POST.get('voucher_code')
            if not code_from_form: messages.error(request, "Vui lòng nhập mã giảm giá."); return redirect('checkout')
            try:
                voucher_to_apply = Voucher.objects.get(code__iexact=code_from_form)
                is_valid, message = voucher_to_apply.is_valid(total_price)
                if is_valid:
                    request.session['voucher_code'] = voucher_to_apply.code
                    messages.success(request, f"Đã áp dụng mã '{voucher_to_apply.code}'.")
                else: messages.error(request, message)
            except Voucher.DoesNotExist: messages.error(request, "Mã giảm giá không tồn tại.")
            return redirect('checkout')

        elif action == 'remove_voucher':
            if 'voucher_code' in request.session: del request.session['voucher_code']; messages.success(request, "Đã xóa mã giảm giá.")
            return redirect('checkout')

        # --- Đặt hàng ---
        elif action == 'place_order':
            if not cart: messages.error(request, "Giỏ hàng rỗng, không thể đặt hàng."); return redirect('home')

            full_name = request.POST.get('full_name')
            email = request.POST.get('email')
            phone = request.POST.get('phone')
            address = request.POST.get('address')

            if not all([full_name, email, phone, address]):
                messages.error(request, "Vui lòng điền đầy đủ thông tin giao hàng.")
                return redirect('checkout')

            # Tạo Order
            order_data = {
                'full_name': full_name, 'email': email, 'phone': phone, 'address': address,
                'total_price': total_price, 'discount_amount': discount_amount, 'voucher': voucher,
            }
            if request.user.is_authenticated: order_data['user'] = request.user
            new_order = Order.objects.create(**order_data)

            # Tạo OrderItem và Trừ kho
            try:
                for item_data in detailed_cart_items:
                    product = item_data['product']
                    quantity = item_data['quantity']
                    # Kiểm tra tồn kho lần cuối trước khi trừ
                    # Reload product from db to get the latest stock count
                    product.refresh_from_db() 
                    if product.stock < quantity:
                        new_order.delete() 
                        messages.error(request, f"Xin lỗi, sản phẩm '{product.name}' đã hết hàng hoặc số lượng không đủ ({product.stock} còn lại). Vui lòng thử lại.")
                        if 'cart' in request.session: del request.session['cart']
                        if 'voucher_code' in request.session: del request.session['voucher_code']
                        return redirect('cart_view') # Quay về giỏ hàng thay vì home

                    OrderItem.objects.create(
                        order=new_order, product=product, quantity=quantity, price_at_purchase=product.price
                    )
                    # Cập nhật lại tồn kho
                    product.stock -= quantity
                    product.save()
            except Exception as e:
                 new_order.delete()
                 messages.error(request, f"Đã xảy ra lỗi khi xử lý đơn hàng: {e}. Vui lòng thử lại.")
                 return redirect('checkout')


            # Xóa giỏ hàng và voucher khỏi session
            del request.session['cart']
            if 'voucher_code' in request.session: del request.session['voucher_code']

            messages.success(request, "Đặt hàng thành công!") 
            return redirect('order_success') 

    # Nếu là GET, hiển thị trang checkout bình thường
    context = {
        'cart_items': detailed_cart_items,
        'total_price': total_price,
        'voucher': voucher,
        'discount_amount': discount_amount,
        'final_price': final_price,
    }
    return render(request, 'store/checkout.html', context)

# -----------------------------------------------------------------------------
# GĐ 10: Trang Cảm ơn
# -----------------------------------------------------------------------------
def order_success(request):
    return render(request, 'store/order_success.html')