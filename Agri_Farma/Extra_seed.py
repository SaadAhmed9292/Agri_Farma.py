
# extra_seed.py - add larger demo dataset
from app import app, db, User, Category, ForumThread, ForumPost, BlogPost, Product

with app.app_context():
    # Products 20+
    shop_cats = {c.name: c for c in Category.query.filter_by(module='shop').all()}
    def ensure_cat(name):
        if name not in shop_cats:
            from models import Category
            c = Category(name=name, module='shop')
            db.session.add(c); db.session.flush(); shop_cats[name]=c
        return shop_cats[name]
    data_products = [
        ('DAP Fertilizer 50kg', 'Phosphate fertilizer', 12500, 'fertilizers'),
        ('NPK 15-15-15 50kg', 'Balanced nutrients', 13200, 'fertilizers'),
        ('Wheat Seeds 10kg', 'Certified seed', 4800, 'seeds'),
        ('Rice Seeds 10kg', 'Basmati hybrid', 8200, 'seeds'),
        ('Pruning Shears', 'Stainless steel', 1500, 'tools'),
        ('Drip Kit 100m', 'Water saving kit', 18500, 'tools'),
        ('Bio Pesticide 1L', 'Organic pest control', 2200, 'pesticides'),
        ('Greenhouse Film 200µ', 'UV stabilized', 26000, 'tools'),
        ('Compost 25kg', 'Organic compost', 2300, 'fertilizers'),
        ('Potash 50kg', 'MOP granular', 11000, 'fertilizers'),
        ('Tractor Oil 4L', 'Engine oil', 4200, 'tools'),
        ('pH Meter', 'Soil pH tester', 3500, 'tools'),
        ('Corn Seeds 5kg', 'Hybrid high yield', 6900, 'seeds'),
        ('Cotton Seeds 5kg', 'Bt variety', 9100, 'seeds'),
        ('Knapsack Sprayer 20L', 'With lance', 7200, 'tools'),
        ('Irrigation Timer', 'Automatic control', 5600, 'tools'),
        ('Neem Oil 1L', 'Natural insecticide', 1800, 'pesticides'),
        ('Tomato Seeds 250g', 'High yield', 2100, 'seeds'),
        ('Sickle', 'Harvesting tool', 900, 'tools'),
        ('Shovel', 'Steel shovel', 1400, 'tools'),
    ]

    for name, desc, price, cname in data_products:
        cat = ensure_cat(cname.capitalize())
        if not Product.query.filter_by(name=name).first():
            db.session.add(Product(name=name, description=desc, price=price, image='/static/images/placeholder.png', category_id=cat.id, rating=4))

    # Blog posts 8 total
    admin = User.query.filter_by(email='admin@agrifarma.com').first()
    kb_cat = Category.query.filter_by(module='knowledge').first()
    for i in range(3, 11):
        title = f'Farming Guide #{i}'
        if not BlogPost.query.filter_by(title=title).first():
            db.session.add(BlogPost(category_id=kb_cat.id, user_id=admin.id, title=title, content='Helpful content...', tags='guide,farming'))

    # Threads 10 total
    forum_cat = Category.query.filter_by(module='forum').first()
    farmer = User.query.filter_by(email='farmer@agrifarma.com').first()
    for i in range(2, 12):
        t = f'Issue Discussion #{i}'
        if not ForumThread.query.filter_by(title=t).first():
            db.session.add(ForumThread(category_id=forum_cat.id, user_id=farmer.id, title=t, content='What is the solution?'))

    db.session.commit()
    print('✅ Extra seed inserted (20+ products, 8 blogs, 10 threads)')
