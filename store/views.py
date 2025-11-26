# Imports từ Django
from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.db.models import Q, Avg # Import Avg để tính trung bình
from django.core.paginator import Paginator
from django.utils import timezone

# Import từ project của bạn
from .models import Product, Category, Order, OrderItem, Voucher, Review, Cart, CartItem # Import thêm Cart, CartItem

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
        query = search_query.lower().strip()
        filtered_products = []
        for p in products:
            name_lower = p.name.lower()
            desc_lower = p.description.lower() if p.description else ""
            if query in name_lower or query in desc_lower:
                filtered_products.append(p)
        products = filtered_products

    # Lọc theo danh mục
    if category_id:
        # Vì products có thể là list (sau khi search), cần filter theo cách khác nếu là list
        if isinstance(products, list):
             products = [p for p in products if p.category.id == int(category_id)]
        else:
             products = products.filter(category__id=category_id)

    # Sắp xếp (Chỉ sắp xếp nếu products là QuerySet, nếu là list thì sort bằng python)
    if not isinstance(products, list):
        if sort_by in ['price_asc', 'price_desc', '-id']:
            if sort_by == 'price_asc':
                products = products.order_by('price')
            elif sort_by == 'price_desc':
                products = products.order_by('-price')
            else:
                products = products.order_by('-id')
    else:
        # Sort list python
        if sort_by == 'price_asc':
            products.sort(key=lambda x: x.price)
        elif sort_by == 'price_desc':
            products.sort(key=lambda x: x.price, reverse=True)
        else:
            products.sort(key=lambda x: x.id, reverse=True)


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
# GĐ 21 (Sửa đổi logic GET và POST): Trang Chi tiết Sản phẩm
# -----------------------------------------------------------------------------
def product_detail(request, product_id):
    product = get_object_or_404(Product, id=product_id)
    reviews = product.reviews.all()
    average_rating = reviews.aggregate(Avg('rating'))['rating__avg']

    # ----- LOGIC KIỂM TRA ĐIỀU KIỆN REVIEW -----
    can_review = False 
    has_reviewed = False
    review_message = "" 

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
                can_review = True 
            else:
                review_message = "Bạn cần mua và nhận hàng thành công trước khi đánh giá."
    else:
        review_message = "Đăng nhập để đánh giá."

    # Xử lý POST để gửi review
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

    context = {
        'product': product,
        'reviews': reviews,
        'average_rating': average_rating,
        'can_review': can_review, 
        'has_reviewed': has_reviewed, 
        'review_message': review_message, 
    }
    return render(request, 'store/product_detail.html', context)

# -----------------------------------------------------------------------------
# GĐ 26: Thêm vào Giỏ hàng (Hỗ trợ DB Cart)
# -----------------------------------------------------------------------------
def add_to_cart(request, product_id):
    if request.method == 'POST' and request.POST.get('action') == 'add_to_cart':
        quantity = int(request.POST.get('quantity', 1))
        product = get_object_or_404(Product, id=product_id)

        # LOGIC MỚI: PHÂN LOẠI USER
        if request.user.is_authenticated:
            # --- User đã đăng nhập: Dùng Database ---
            cart, _ = Cart.objects.get_or_create(user=request.user)
            cart_item, created = CartItem.objects.get_or_create(cart=cart, product=product)
            
            if created:
                new_quantity = quantity
            else:
                new_quantity = cart_item.quantity + quantity

            if new_quantity <= product.stock:
                cart_item.quantity = new_quantity
                cart_item.save()
                messages.success(request, f"Đã thêm {quantity} '{product.name}' vào giỏ.")
            else:
                messages.warning(request, "Số lượng vượt quá tồn kho.")
        else:
            # --- Khách vãng lai: Dùng Session ---
            cart = request.session.get('cart', {})
            product_id_str = str(product_id)
            
            if quantity > 0 and product.stock > 0 : 
                current_quantity = cart.get(product_id_str, 0)
                new_quantity = current_quantity + quantity
                if new_quantity <= product.stock:
                    cart[product_id_str] = new_quantity
                    request.session['cart'] = cart
                    messages.success(request, f"Đã thêm {quantity} '{product.name}' vào giỏ hàng thành công!")
                else:
                    can_add = product.stock - current_quantity
                    if can_add > 0:
                        cart[product_id_str] = product.stock
                        request.session['cart'] = cart
                        messages.warning(request, f"Chỉ còn {product.stock} sản phẩm. Đã thêm tối đa {can_add} '{product.name}' vào giỏ.")
                    else:
                        messages.warning(request, f"Sản phẩm '{product.name}' đã ở mức tối đa trong giỏ của bạn.")
            elif product.stock <= 0:
                 messages.error(request, f"Sản phẩm '{product.name}' đã hết hàng.")
            else: 
                 messages.error(request, "Số lượng không hợp lệ.")

        return redirect('product_detail', product_id=product_id)
    
    return redirect('product_detail', product_id=product_id)


# -----------------------------------------------------------------------------
# GĐ 26: Xem Giỏ hàng (Hỗ trợ DB Cart)
# -----------------------------------------------------------------------------
def cart_view(request):
    detailed_cart_items = []
    total_price = 0

    if request.user.is_authenticated:
        # --- Dùng Database ---
        cart, _ = Cart.objects.get_or_create(user=request.user)
        db_items = cart.cart_items.all()
        for item in db_items:
            # Kiểm tra tồn kho thực tế
            if item.quantity > item.product.stock:
                item.quantity = item.product.stock
                item.save()
                messages.warning(request, f"Số lượng '{item.product.name}' đã được cập nhật do thay đổi tồn kho.")
            
            if item.quantity > 0:
                detailed_cart_items.append({
                    'product': item.product,
                    'quantity': item.quantity,
                    'subtotal': item.subtotal
                })
                total_price += item.subtotal
            else:
                item.delete()
    else:
        # --- Dùng Session ---
        cart = request.session.get('cart', {})
        for product_id, quantity in list(cart.items()):
            try:
                product = Product.objects.get(id=int(product_id))
                if quantity > product.stock:
                    cart[product_id] = product.stock
                    quantity = product.stock
                    messages.warning(request, f"Số lượng '{product.name}' đã được cập nhật do thay đổi tồn kho.")

                if quantity > 0:
                    subtotal = product.price * quantity
                    detailed_cart_items.append({
                        'product': product,
                        'quantity': quantity,
                        'subtotal': subtotal,
                    })
                    total_price += subtotal
                else:
                    del cart[product_id]
            except Product.DoesNotExist:
                del cart[product_id]
        
        request.session['cart'] = cart # Lưu lại session cart nếu có thay đổi

    context = {
        'cart_items': detailed_cart_items,
        'total_price': total_price,
    }
    return render(request, 'store/cart.html', context)


# -----------------------------------------------------------------------------
# GĐ 26: Cập nhật Giỏ hàng (Hỗ trợ DB Cart)
# -----------------------------------------------------------------------------
def update_cart(request, product_id):
    if request.method == 'POST':
        try:
            quantity = int(request.POST.get('quantity'))
        except (ValueError, TypeError):
            quantity = 1

        product = get_object_or_404(Product, id=product_id)

        if request.user.is_authenticated:
            # --- Dùng Database ---
            cart, _ = Cart.objects.get_or_create(user=request.user)
            if quantity > 0:
                if quantity <= product.stock:
                    cart_item, _ = CartItem.objects.get_or_create(cart=cart, product=product)
                    cart_item.quantity = quantity
                    cart_item.save()
                    messages.success(request, "Đã cập nhật.")
                else:
                    messages.warning(request, "Quá tồn kho.")
            else:
                # Xóa
                CartItem.objects.filter(cart=cart, product=product).delete()
                messages.success(request, "Đã xóa sản phẩm.")
        else:
            # --- Dùng Session ---
            cart = request.session.get('cart', {})
            product_id_str = str(product_id)
            if product_id_str in cart:
                if quantity <= 0:
                    del cart[product_id_str]
                    messages.success(request, f"Đã xóa '{product.name}' khỏi giỏ hàng.")
                elif quantity > product.stock:
                    cart[product_id_str] = product.stock
                    messages.warning(request, f"Số lượng '{product.name}' vượt quá tồn kho ({product.stock}), đã đặt tối đa.")
                else:
                    cart[product_id_str] = quantity
                    messages.success(request, f"Đã cập nhật số lượng '{product.name}'.")
            request.session['cart'] = cart

    return redirect('cart_view')


# -----------------------------------------------------------------------------
# GĐ 26: Checkout (Hỗ trợ DB Cart)
# -----------------------------------------------------------------------------
def checkout(request):
    detailed_cart_items = []
    total_price = 0
    
    # --- Lấy giỏ hàng (DB hoặc Session) ---
    if request.user.is_authenticated:
        cart_db, _ = Cart.objects.get_or_create(user=request.user)
        db_items = cart_db.cart_items.all()
        if not db_items:
             messages.error(request, "Giỏ hàng của bạn rỗng.")
             return redirect('home')
        for item in db_items:
             # Kiểm tra tồn kho
             if item.quantity > item.product.stock:
                 item.quantity = item.product.stock
                 item.save()
             detailed_cart_items.append({'product': item.product, 'quantity': item.quantity, 'subtotal': item.subtotal})
             total_price += item.subtotal
    else:
        cart_session = request.session.get('cart', {})
        if not cart_session:
            messages.error(request, "Giỏ hàng của bạn rỗng.")
            return redirect('home')
        
        for product_id, quantity in list(cart_session.items()):
            try:
                product = Product.objects.get(id=int(product_id))
                if quantity > product.stock:
                    cart_session[product_id] = product.stock
                    quantity = product.stock
                subtotal = product.price * quantity
                detailed_cart_items.append({'product': product, 'quantity': quantity, 'subtotal': subtotal})
                total_price += subtotal
            except Product.DoesNotExist:
                del cart_session[product_id]
        request.session['cart'] = cart_session

    # 1. Lấy dữ liệu form đã lưu tạm trong session
    form_data = request.session.get('checkout_form_data', {
        'full_name': '',
        'email': '',
        'phone': '',
        'address': ''
    })
    if request.user.is_authenticated and not form_data['email']:
        form_data['email'] = request.user.email

    # --- Xử lý Voucher ---
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
                del request.session['voucher_code']
                voucher = None
        except Voucher.DoesNotExist:
            messages.error(request, "Mã giảm giá không tồn tại.")
            del request.session['voucher_code']

    final_price = total_price - discount_amount

    # --- XỬ LÝ POST ---
    if request.method == 'POST':
        action = request.POST.get('action')

        form_data = {
            'full_name': request.POST.get('full_name', ''),
            'email': request.POST.get('email', ''),
            'phone': request.POST.get('phone', ''),
            'address': request.POST.get('address', ''),
        }
        request.session['checkout_form_data'] = form_data

        if action == 'apply_voucher':
            code_from_form = request.POST.get('voucher_code_input')
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

        elif action == 'place_order':
            full_name = form_data['full_name']
            email = form_data['email']
            phone = form_data['phone']
            address = form_data['address']

            if not all([full_name, email, phone, address]):
                messages.error(request, "Vui lòng điền đầy đủ thông tin giao hàng.")
                return redirect('checkout')

            order_data = {
                'full_name': full_name, 'email': email, 'phone': phone, 'address': address,
                'total_price': total_price, 'discount_amount': discount_amount, 'voucher': voucher,
            }
            if request.user.is_authenticated: order_data['user'] = request.user
            new_order = Order.objects.create(**order_data)

            try:
                for item_data in detailed_cart_items:
                    product = item_data['product']
                    quantity = item_data['quantity']
                    product.refresh_from_db()
                    if product.stock < quantity:
                        new_order.delete()
                        messages.error(request, f"Sản phẩm '{product.name}' không đủ hàng.")
                        return redirect('cart_view')
                    
                    OrderItem.objects.create(
                        order=new_order, product=product, quantity=quantity, price_at_purchase=product.price
                    )
                    product.stock -= quantity
                    product.save()
            except Exception as e:
                 new_order.delete()
                 messages.error(request, f"Lỗi: {e}")
                 return redirect('checkout')

            # Dọn dẹp sau khi thành công
            if request.user.is_authenticated:
                cart_db.delete() # Xóa giỏ hàng trong DB
            else:
                del request.session['cart'] # Xóa giỏ hàng Session
                
            if 'voucher_code' in request.session: del request.session['voucher_code']
            if 'checkout_form_data' in request.session: del request.session['checkout_form_data']

            messages.success(request, "Đặt hàng thành công!")
            return redirect('order_success')

    context = {
        'cart_items': detailed_cart_items,
        'total_price': total_price,
        'voucher': voucher,
        'discount_amount': discount_amount,
        'final_price': final_price,
        'form_data': form_data,
    }
    return render(request, 'store/checkout.html', context)

# -----------------------------------------------------------------------------
# GĐ 10: Trang Cảm ơn
# -----------------------------------------------------------------------------
def order_success(request):
    return render(request, 'store/order_success.html')

# -----------------------------------------------------------------------------
# GĐ 0: Trang Giới thiệu
# -----------------------------------------------------------------------------
def landing_page(request):
    featured_products = Product.objects.all().order_by('-id')[:4]
    context = {
        'featured_products': featured_products
    }
    return render(request, 'store/landing_page.html', context)