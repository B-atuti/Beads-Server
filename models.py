from flask_sqlalchemy import SQLAlchemy
from datetime import datetime

db = SQLAlchemy()

# Association Table for Many-to-Many Relationship between Orders & Products
order_product = db.Table(
    "order_product",
    db.Column("order_id", db.Integer, db.ForeignKey("order.id"), primary_key=True),
    db.Column("product_id", db.Integer, db.ForeignKey("product.id"), primary_key=True),
    db.Column("quantity", db.Integer, nullable=False, default=1),
)

class User(db.Model):
    """User Model for Authentication"""
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(50), unique=True, nullable=False)
    password = db.Column(db.String(255), nullable=False)
    role = db.Column(db.String(10), default="admin")  # "admin" or "user"

class Category(db.Model):
    """Category Model for Product Categories"""
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False, unique=True)
    description = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # ✅ Relationship to Products
    products = db.relationship("Product", back_populates="category")

class Product(db.Model):
    """Product Model for Bead Inventory"""
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    category_id = db.Column(db.Integer, db.ForeignKey("category.id"), nullable=False)  # ✅ Foreign Key to Category
    size = db.Column(db.String(20))
    stock_quantity = db.Column(db.Integer, nullable=False)
    selling_price = db.Column(db.Float, nullable=False)
    low_stock_threshold = db.Column(db.Integer, default=10)

    # ✅ Relationships
    category = db.relationship("Category", back_populates="products")  # Link to Category
    sales = db.relationship("Sale", back_populates="product", cascade="all, delete")  # One Product → Many Sales
    orders = db.relationship("Order", secondary=order_product, back_populates="products")  # Many-to-Many with Orders

class Sale(db.Model):
    """Sales Model for Tracking Sales"""
    id = db.Column(db.Integer, primary_key=True)
    product_id = db.Column(db.Integer, db.ForeignKey("product.id"), nullable=False)
    quantity_sold = db.Column(db.Integer, nullable=False)
    sale_date = db.Column(db.DateTime, default=datetime.utcnow)
    total_price = db.Column(db.Float, nullable=False)
    payment_method = db.Column(db.String(50))
    sale_status = db.Column(db.String(20), default="pending")

    # ✅ Relationship
    product = db.relationship("Product", back_populates="sales")  # Link to Product

class Order(db.Model):
    """Order Model for Customer Orders"""
    id = db.Column(db.Integer, primary_key=True)
    customer_name = db.Column(db.String(100), nullable=False)
    order_status = db.Column(db.String(20), default="pending")
    order_date = db.Column(db.DateTime, default=datetime.utcnow)
    shipping_info = db.Column(db.String(255))

    # ✅ Many-to-Many Relationship with Products
    products = db.relationship("Product", secondary=order_product, back_populates="orders")

class Color(db.Model):
    """Color Model for Managing Product Colors"""
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(50), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
