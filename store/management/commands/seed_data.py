import random
from django.core.management.base import BaseCommand
from store.models import Category, Product

# Danh sách link ảnh mẫu (để trông cho đa dạng)
IMAGE_LINKS = {
    'ao': [
        'https://assets.adidas.com/images/h_840,f_auto,q_auto,fl_lossy,c_fill,g_auto/51dfb0069a3741369d273756858c6e0a_9366/Ao_au_san_nha_Real_Madrid_24-25_Mau_trang_IX8730_01_layover.jpg',
        'https://assets.adidas.com/images/h_840,f_auto,q_auto,fl_lossy,c_fill,g_auto/29f03127889e4c6c9e2bce228f418d1a_9366/Ao_au_san_nha_Arsenal_24-25_Mau_do_IS8132_01_layover.jpg',
        'https://assets.adidas.com/images/h_840,f_auto,q_auto,fl_lossy,c_fill,g_auto/7101aba58e1c45c28f328f481cfa068e_9366/Ao_au_san_nha_Manchester_United_24-25_Mau_do_IY7711_01_layover.jpg'
    ],
    'giay': [
        # Đã thay thế link Nike hỏng bằng link Adidas
        'https://assets.adidas.com/images/h_840,f_auto,q_auto,fl_lossy,c_fill,g_auto/2d9ea1825dc949988b0a1d48b111a43a_9366/Giay_a_Bong_Predator_Elite_Firm_Ground_DJen_IF3207_01_standard.jpg',
        'https://assets.adidas.com/images/h_840,f_auto,q_auto,fl_lossy,c_fill,g_auto/531c79c0a6d04d96a70e7a4b64f3366c_9366/Giay_a_Bong_Co_Thap_F50_League_Firm_Ground_Mau_trang_IG3557_01_standard.jpg'
    ],
    'bong': [
        # Đã thay thế link Nike hỏng bằng link Adidas
        'https://assets.adidas.com/images/h_840,f_auto,q_auto,fl_lossy,c_fill,g_auto/c2a7133f114c48979d1da42a5c938c53_9366/UEFA_Champions_League_Pro_Ball_Mau_trang_IN9336_01_standard.jpg',
        'https://assets.adidas.com/images/h_840,f_auto,q_auto,fl_lossy,c_fill,g_auto/116e25f8287e4d828d11afd100f913e2_9366/Bong_Euro_24_Pro_Mau_trang_IQ3687_01_standard.jpg'
    ],
    'gang_tay': [
        # Link này đã là Adidas, vẫn hoạt động
        'https://assets.adidas.com/images/h_840,f_auto,q_auto,fl_lossy,c_fill,g_auto/9d7367664f3c467a83efb1ab68334465_9366/Gang_tay_Thu_mon_Predator_Pro_DJen_IY7730_01_standard.jpg'
    ],
    'phu_kien': [
        # Đã thay thế 2 link Nike hỏng bằng 2 link Adidas
        'https://assets.adidas.com/images/h_840,f_auto,q_auto,fl_lossy,c_fill,g_auto/1e309f30b96740c08796af1401053421_9366/Tat_adizero_Traxion_Mau_trang_HN8841_03_standard.jpg',
        'https://assets.adidas.com/images/h_840,f_auto,q_auto,fl_lossy,c_fill,g_auto/e211df639f754b29ba39adb200f60741_9366/Boc_Ong_Dong_Tiro_League_Mau_trang_HS9759_01_standard.jpg'
    ]
}


class Command(BaseCommand):
    help = 'Bơm (seed) dữ liệu mẫu vào database'

    def handle(self, *args, **options):
        self.stdout.write('Đang xóa dữ liệu cũ...')
        # Xóa sạch trước khi tạo
        Product.objects.all().delete()
        Category.objects.all().delete()

        self.stdout.write('Đang tạo dữ liệu mới...')

        # --- Tạo Danh mục ---
        cat_ao = Category.objects.create(name="Áo đấu")
        cat_giay = Category.objects.create(name="Giày")
        cat_bong = Category.objects.create(name="Bóng")
        cat_gang = Category.objects.create(name="Găng tay thủ môn")
        cat_pk = Category.objects.create(name="Phụ kiện")

        # --- Tạo 20 Áo đấu ---
        for i in range(1, 21):
            Product.objects.create(
                name=f"Áo đấu mẫu #{i}",
                description=f"Đây là mô tả cho mẫu áo đấu #{i}. Chất liệu cao cấp, thoáng khí.",
                price=random.randint(500, 1000) * 1000, # Giá ngẫu nhiên từ 500k-1tr
                image=random.choice(IMAGE_LINKS['ao']),
                stock=random.randint(20, 100),
                category=cat_ao
            )

        # --- Tạo 20 Giày ---
        for i in range(1, 21):
            Product.objects.create(
                name=f"Giày đá bóng mẫu #{i}",
                description=f"Mô tả cho giày mẫu #{i}. Đế FG/AG bám sân tốt.",
                price=random.randint(1500, 3000) * 1000, # Giá ngẫu nhiên từ 1tr5-3tr
                image=random.choice(IMAGE_LINKS['giay']),
                stock=random.randint(10, 50),
                category=cat_giay
            )

        # --- Tạo 20 Quả bóng ---
        for i in range(1, 21):
            Product.objects.create(
                name=f"Bóng đá mẫu #{i}",
                description=f"Mô tả cho bóng mẫu #{i}. Chuẩn thi đấu.",
                price=random.randint(300, 1500) * 1000, # Giá ngẫu nhiên
                image=random.choice(IMAGE_LINKS['bong']),
                stock=random.randint(30, 80),
                category=cat_bong
            )

        # --- Tạo 20 Găng tay ---
        for i in range(1, 21):
            Product.objects.create(
                name=f"Găng tay thủ môn mẫu #{i}",
                description=f"Mô tả găng tay #{i}. Mút dày, bám dính tốt.",
                price=random.randint(700, 2000) * 1000, # Giá ngẫu nhiên
                image=random.choice(IMAGE_LINKS['gang_tay']),
                stock=random.randint(15, 40),
                category=cat_gang
            )

        # --- Tạo 20 Phụ kiện ---
        for i in range(1, 21):
            Product.objects.create(
                name=f"Phụ kiện mẫu #{i}",
                description=f"Mô tả phụ kiện #{i}. (Tất, bọc ống đồng...)",
                price=random.randint(100, 400) * 1000, # Giá ngẫu nhiên
                image=random.choice(IMAGE_LINKS['phu_kien']),
                stock=random.randint(50, 200),
                category=cat_pk
            )
            
        self.stdout.write(self.style.SUCCESS(f'Tạo thành công 5 danh mục và 100 sản phẩm mẫu!'))