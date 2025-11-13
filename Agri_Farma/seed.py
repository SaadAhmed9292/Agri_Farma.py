
# seed.py - Populate the database with initial data for local testing
from app import app
from models import db, Role, User, Profile, Category, ForumThread, ForumPost, BlogPost, BlogComment, Product, Order, OrderItem

with app.app_context():
    db.create_all()

    # Roles
    admin_role = Role.query.filter_by(name='admin').first() or Role(name='admin')
    user_role = Role.query.filter_by(name='user').first() or Role(name='user')
    consultant_role = Role.query.filter_by(name='consultant').first() or Role(name='consultant')
    farmer_role = Role.query.filter_by(name='farmer').first() or Role(name='farmer')
    db.session.add_all([admin_role, user_role, consultant_role, farmer_role])

    # Users
    if not User.query.filter_by(email='admin@agrifarma.com').first():
        admin = User(name='Admin User', email='admin@agrifarma.com')
        admin.set_password('admin123')
        admin.roles.append(admin_role)
        db.session.add(admin)
        db.session.flush()
        db.session.add(Profile(user_id=admin.id, city='Lahore', state='Punjab', country='PK', profession='other', expertise='expert'))

    if not User.query.filter_by(email='farmer@agrifarma.com').first():
        farmer = User(name='Demo Farmer', email='farmer@agrifarma.com')
        farmer.set_password('farmer123')
        farmer.roles.append(user_role)
        farmer.roles.append(farmer_role)
        db.session.add(farmer)
        db.session.flush()
        db.session.add(Profile(user_id=farmer.id, city='Faisalabad', state='Punjab', country='PK', profession='farmer', expertise='intermediate'))

    if not User.query.filter_by(email='consultant@agrifarma.com').first():
        consultant = User(name='Agri Consultant', email='consultant@agrifarma.com')
        consultant.set_password('consult123')
        consultant.roles.append(user_role)
        consultant.roles.append(consultant_role)
        db.session.add(consultant)
        db.session.flush()
        db.session.add(Profile(user_id=consultant.id, city='Multan', state='Punjab', country='PK', profession='consultant', expertise='expert'))

    db.session.commit()

    # Categories
    def cat(name, module, desc=''):
        c = Category.query.filter_by(name=name, module=module).first()
        if not c:
            c = Category(name=name, module=module, description=desc)
            db.session.add(c)
            db.session.flush()
        return c

    fert = cat('Fertilizers', 'shop', 'Soil nutrients and fertilizers')
    seeds = cat('Seeds', 'shop', 'Quality seeds')
    tools = cat('Tools', 'shop', 'Farming tools')

    kb_practices = cat('Best Practices', 'knowledge', 'Farming practices and tips')
    kb_success = cat('Success Stories', 'knowledge', 'Farmer experiences')

    forum_crop = cat('Crop Management', 'forum', 'Discuss crop issues')

    db.session.commit()

    # Products
    if Product.query.count() == 0:
        db.session.add_all([
            Product(name='Urea Fertilizer 50kg', description='High quality urea', price=9500, image='/static/images/urea.jpg', category_id=fert.id, rating=4),
            Product(name='Hybrid Corn Seeds 5kg', description='High yield variety', price=6500, image='/static/images/corn.jpg', category_id=seeds.id, rating=5),
            Product(name='Hand Sprayer 16L', description='Durable sprayer for pesticides', price=5200, image='/static/images/sprayer.jpg', category_id=tools.id, rating=3),
        ])

    db.session.commit()

    # Blog posts
    admin = User.query.filter_by(email='admin@agrifarma.com').first()
    farmer = User.query.filter_by(email='farmer@agrifarma.com').first()

    if BlogPost.query.count() == 0:
        post1 = BlogPost(category_id=kb_practices.id, user_id=admin.id, title='Soil Testing Basics', content='Content about soil testing...', tags='soil,testing')
        post2 = BlogPost(category_id=kb_success.id, user_id=farmer.id, title='Wheat Yield Improvement', content='Content about yield...', tags='wheat,success')
        db.session.add_all([post1, post2])

    db.session.commit()

    # Forum threads and posts
    if ForumThread.query.count() == 0:
        th = ForumThread(category_id=forum_crop.id, user_id=farmer.id, title='Pest attack on cotton', content='Seeing whiteflies on leaves, what to do?')
        db.session.add(th)
        db.session.flush()
        db.session.add_all([
            ForumPost(thread_id=th.id, user_id=admin.id, content='Consider using recommended IPM practices.'),
            ForumPost(thread_id=th.id, user_id=farmer.id, content='Thanks! Will try yellow sticky traps.')
        ])

    db.session.commit()
    print('✅ Seed data inserted')
