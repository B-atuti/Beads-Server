from flask import Flask, request, jsonify
from flask_sqlalchemy import SQLAlchemy
from flask_jwt_extended import JWTManager, jwt_required, create_access_token, get_jwt_identity
from flask_cors import CORS
from datetime import datetime
from flask_migrate import Migrate
from models import db, Product, Sale, Order, User, Category, Color
from admin import admin_bp, create_admin_user
from flask_socketio import SocketIO 
import json 


app = Flask(__name__)
app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///inventory.db"
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
app.config["JWT_SECRET_KEY"] = "supersecretkey"

db.init_app(app)
migrate = Migrate(app, db)  
jwt = JWTManager(app)
CORS(app)
socketio = SocketIO(app, cors_allowed_origins="*")  

app.register_blueprint(admin_bp, url_prefix="/admin")

with app.app_context():
    create_admin_user() 
@app.route("/", methods=["GET"])
def home():
    return jsonify({"message": "Beads Inventory Management API Running!"})


@app.route("/products", methods=["GET"])
def get_products():
    """Get all products"""
    print("📩 Received GET /products request")  # ✅ Debugging

    try:
        products = Product.query.all()
        response = [{
            "id": p.id, "name": p.name, "category": p.category.name,
            "stock": p.stock_quantity, "price": p.selling_price
        } for p in products]

        print("✅ Returning Products:", response)
        return jsonify(response)
    except Exception as e:
        print("❌ Error in /products:", str(e))
        return jsonify({"error": "Server error"}), 500

@app.route("/products/<int:id>", methods=["GET"])
@jwt_required()
def get_product(id):
    """Get a specific product"""
    product = Product.query.get(id)
    if not product:
        return jsonify({"error": "Product not found"}), 404

    return jsonify({
        "id": product.id, "name": product.name, "category": product.category,
        "stock": product.stock_quantity, "price": product.selling_price
    })

@app.route("/products", methods=["POST"]) 
def add_product():
    """Add a new product with detailed logging"""
    data = request.json
    print("📥 Received Data:", json.dumps(data, indent=2))  
    
    if not data:
        print("❌ Error: No JSON data received")
        return jsonify({"error": "No data provided"}), 400
    
    required_fields = ["name", "category_id", "stock_quantity", "selling_price", "low_stock_threshold"]
    
    for field in required_fields:
        if field not in data:
            print(f"❌ Missing field: {field}")
            return jsonify({"error": f"Missing field: {field}"}), 400  

    try:
        new_product = Product(
            name=str(data["name"]),
            category_id=int(data["category_id"]),  
            stock_quantity=int(data["stock_quantity"]),
            selling_price=float(data["selling_price"]),
            low_stock_threshold=int(data.get("low_stock_threshold", 10)),  
        )


        db.session.add(new_product)
        db.session.commit()
        print("✅ Product added successfully!")
        return jsonify({"message": "Product added successfully"}), 201

    except ValueError as ve:
        print(f"❌ Data Type Error: {str(ve)}")
        return jsonify({"error": "Invalid data type", "details": str(ve)}), 422

    except Exception as e:
        print(f"❌ Unexpected Server Error: {str(e)}")
        return jsonify({"error": "Server error", "details": str(e)}), 500


@app.route("/products/<int:id>", methods=["PUT"])
@jwt_required()
def update_product(id):
    """Update product details"""
    product = Product.query.get(id)
    if not product:
        return jsonify({"error": "Product not found"}), 404

    data = request.json
    product.name = data.get("name", product.name)
    product.category = data.get("category", product.category)
    product.colors = data.get("colors", product.colors)
    product.size = data.get("size", product.size)
    product.stock_quantity = data.get("stock_quantity", product.stock_quantity)
    product.selling_price = data.get("selling_price", product.selling_price)

    db.session.commit()
    return jsonify({"message": "Product updated successfully"})

@app.route("/products/<int:id>", methods=["DELETE"])
# @jwt_required()
def delete_product(id):
    """Delete a product"""
    product = Product.query.get(id)
    if not product:
        return jsonify({"error": "Product not found"}), 404

    db.session.delete(product)
    db.session.commit()
    return jsonify({"message": "Product deleted successfully"})

@app.route("/products/category/<int:category_id>", methods=["GET"])
def get_products_by_category(category_id):
    """Get products filtered by category"""
    print(f"📩 Received GET /products/category/{category_id} request")
    
    try:
        category = Category.query.get(category_id)
        if not category:
            print(f"❌ Category not found: ID {category_id}")
            return jsonify({"error": "Category not found"}), 404
            
        # Query products belonging to this category
        products = Product.query.filter_by(category_id=category_id).all()
        
        if not products:
            print(f"ℹ️ No products found for category ID {category_id}")
            return jsonify([]), 200
            
        # Format the response similar to existing /products route
        response = [{
            "id": p.id,
            "name": p.name,
            "category": p.category.name,
            "stock": p.stock_quantity,
            "price": p.selling_price
        } for p in products]
        
        print(f"✅ Returning {len(products)} products for category {category.name}")
        return jsonify(response), 200
    except Exception as e:
        print(f"❌ Error in /products/category/{category_id}: {str(e)}")
        return jsonify({"error": "Server error", "details": str(e)}), 500

# ================== STOCK MANAGEMENT ==================
@app.route("/inventory", methods=["GET"])
@jwt_required()  # ✅ Ensure authentication
def get_inventory():
    """Fetch inventory data"""
    try:
        print("\n📩 Incoming request for inventory data")

        inventory = Product.query.all()
        inventory_data = [
            {"id": item.id, "name": item.name, "stock_quantity": item.stock_quantity} for item in inventory
        ]

        print("✅ Sending inventory data:", inventory_data)
        return jsonify(inventory_data), 200

    except Exception as e:
        print("❌ Error fetching inventory:", str(e))
        return jsonify({"error": "Server error", "details": str(e)}), 500

@app.route("/inventory/<int:id>/stock", methods=["PATCH"])
@jwt_required()
def update_stock(id):
    """Update stock quantity for a product"""
    data = request.json
    product = Product.query.get(id)

    if not product:
        return jsonify({"error": "Product not found"}), 404

    product.stock_quantity += data["quantity"]
    db.session.commit()
    return jsonify({"message": "Stock updated successfully"})

@app.route("/inventory/update", methods=["POST"])
def update_inventory():
    """Update product stock & notify clients"""
    data = request.json
    product = Product.query.get(data["id"])

    if not product:
        return jsonify({"error": "Product not found"}), 404

    product.stock_quantity = data["stock"]
    db.session.commit()

    # ✅ Notify all clients about stock updates
    socketio.emit("stock_update", {
        "id": product.id, "name": product.name,
        "stock": product.stock_quantity
    })

    # ✅ Emit a low stock alert if stock is below 10
    if product.stock_quantity < 10:
        socketio.emit("low_stock_alert", {
            "id": product.id, "name": product.name,
            "stock": product.stock_quantity,
            "message": f"⚠️ Low Stock: {product.name} has only {product.stock_quantity} left!"
        })

    return jsonify({"message": "Stock updated successfully"}), 200

# ================== SALES MANAGEMENT ==================
@app.route("/sales", methods=["POST"])
def create_sale():
    """Record a sale with improved error handling and stock management"""
    print("📩 Received POST /sales request")
    
    try:
        data = request.json
        if not data:
            print("❌ Error: No JSON data received")
            return jsonify({"error": "No data provided"}), 400
            
        # Validate required fields
        required_fields = ["product_id", "quantity_sold", "total_price", "payment_method", "sale_status"]
        for field in required_fields:
            if field not in data:
                print(f"❌ Missing field: {field}")
                return jsonify({"error": f"Missing field: {field}"}), 400
                
        # Check if product exists
        product = Product.query.get(data["product_id"])
        if not product:
            print(f"❌ Product not found: ID {data['product_id']}")
            return jsonify({"error": "Product not found"}), 404
            
        # Check if sufficient stock is available
        if product.stock_quantity < data["quantity_sold"]:
            print(f"❌ Insufficient stock for product {product.name}: {product.stock_quantity} available, {data['quantity_sold']} requested")
            return jsonify({
                "error": "Insufficient stock", 
                "available": product.stock_quantity,
                "requested": data["quantity_sold"]
            }), 400
            
        try:
            # Start transaction
            product.stock_quantity -= data["quantity_sold"]
            sale = Sale(
                product_id=data["product_id"], 
                quantity_sold=data["quantity_sold"],
                total_price=data["total_price"], 
                payment_method=data["payment_method"],
                sale_status=data["sale_status"]
            )
            db.session.add(sale)
            db.session.commit()
            
            # Notify clients about the sale and updated stock
            socketio.emit("sale_completed", {
                "id": sale.id,
                "product_id": product.id,
                "product_name": product.name,
                "quantity_sold": data["quantity_sold"],
                "total_price": data["total_price"],
                "remaining_stock": product.stock_quantity
            })
            
            # Emit low stock alert if needed
            if product.stock_quantity < product.low_stock_threshold:
                socketio.emit("low_stock_alert", {
                    "id": product.id, 
                    "name": product.name,
                    "stock": product.stock_quantity,
                    "message": f"⚠️ Low Stock: {product.name} has only {product.stock_quantity} left!"
                })
                
            print(f"✅ Sale recorded successfully: {data['quantity_sold']} units of product {product.name}")
            return jsonify({"message": "Sale recorded successfully", "sale_id": sale.id}), 201
            
        except Exception as e:
            # Rollback transaction on error
            db.session.rollback()
            print(f"❌ Database error during sale: {str(e)}")
            return jsonify({"error": "Database error", "details": str(e)}), 500
            
    except Exception as e:
        print(f"❌ Unexpected error in /sales POST: {str(e)}")
        return jsonify({"error": "Server error", "details": str(e)}), 500

@app.route("/sales", methods=["GET"])
def get_sales():
    """Retrieve sales history"""
    print("📩 Received GET /sales request")  # ✅ Debugging

    try:
        sales = Sale.query.all()
        response = [{
            "id": s.id, "product_name": s.product_id, "quantity": s.quantity_sold,
            "total_price": s.total_price, "sale_date": s.sale_date.strftime("%Y-%m-%d %H:%M:%S")
        } for s in sales]

        print("✅ Returning Sales:", response)
        return jsonify(response)
    except Exception as e:
        print("❌ Error in /sales:", str(e))
        return jsonify({"error": "Server error"}), 500
        
@app.route("/sales/product/<int:product_id>", methods=["GET"])
@jwt_required()
def get_product_sales(product_id):
    """Retrieve sales history for a specific product"""
    print(f"📩 Received GET /sales/product/{product_id} request")
    
    try:
        # First check if the product exists
        product = Product.query.get(product_id)
        if not product:
            print(f"❌ Product not found: ID {product_id}")
            return jsonify({"error": "Product not found"}), 404
            
        # Query sales for this product
        sales = Sale.query.filter_by(product_id=product_id).all()
        
        if not sales:
            print(f"ℹ️ No sales found for product ID {product_id}")
            return jsonify([]), 200
            
        # Format the response
        response = [{
            "id": s.id,
            "product_id": s.product_id,
            "product_name": product.name,
            "quantity_sold": s.quantity_sold,
            "total_price": s.total_price,
            "payment_method": s.payment_method,
            "sale_status": s.sale_status,
            "sale_date": s.sale_date
        } for s in sales]
        
        # Calculate total units sold and revenue
        total_units = sum(s.quantity_sold for s in sales)
        total_revenue = sum(s.total_price for s in sales)
        
        result = {
            "product_id": product_id,
            "product_name": product.name,
            "total_units_sold": total_units,
            "total_revenue": total_revenue,
            "sales": response
        }
        
        print(f"✅ Returning {len(sales)} sales for product {product.name}")
        return jsonify(result), 200
        
    except Exception as e:
        print(f"❌ Error in /sales/product/{product_id}: {str(e)}")
        return jsonify({"error": "Server error", "details": str(e)}), 500

@app.route("/sales/<int:sale_id>", methods=["GET"])
@jwt_required()
def get_sale_details(sale_id):
    """Retrieve detailed information for a specific sale"""
    print(f"📩 Received GET /sales/{sale_id} request")
    
    try:
        # Get the sale by ID
        sale = Sale.query.get(sale_id)
        if not sale:
            print(f"❌ Sale not found: ID {sale_id}")
            return jsonify({"error": "Sale not found"}), 404
            
        # Get the associated product
        product = Product.query.get(sale.product_id)
        if not product:
            print(f"❌ Product not found for sale ID {sale_id}: Product ID {sale.product_id}")
            return jsonify({"error": "Associated product not found"}), 404
            
        # Calculate unit price and profit
        unit_price = sale.total_price / sale.quantity_sold if sale.quantity_sold > 0 else 0
        profit = sale.total_price - (product.cost_price * sale.quantity_sold)
        
        # Format the response
        response = {
            "sale_id": sale.id,
            "sale_date": sale.sale_date,
            "quantity_sold": sale.quantity_sold,
            "total_price": sale.total_price,
            "payment_method": sale.payment_method,
            "sale_status": sale.sale_status,
            "unit_price": unit_price,
            "profit": profit,
            "product": {
                "id": product.id,
                "name": product.name,
                "description": product.description,
                "category_id": product.category_id,
                "price_per_unit": product.price_per_unit,
                "stock_quantity": product.stock_quantity
            }
        }
        
        print(f"✅ Returning details for sale ID {sale_id}")
        return jsonify(response), 200
        
    except Exception as e:
        print(f"❌ Error in /sales/{sale_id}: {str(e)}")
        return jsonify({"error": "Server error", "details": str(e)}), 500

@app.route("/sales/all", methods=["GET"])
def get_all_sales():
    """Retrieve all sales with filtering, pagination and product details"""
    print("📩 Received GET /sales/all request")
    
    try:
        # Get and validate query parameters
        page = request.args.get('page', 1, type=int)
        per_page = request.args.get('per_page', 10, type=int)
        
        # Limit per_page to reasonable values
        if per_page > 100:
            per_page = 100
        
        # Get filter parameters
        start_date = request.args.get('start_date')
        end_date = request.args.get('end_date')
        product_id = request.args.get('product_id', type=int)
        payment_method = request.args.get('payment_method')
        sale_status = request.args.get('sale_status')
        
        print(f"🔍 Filter params: start_date={start_date}, end_date={end_date}, product_id={product_id}, "
              f"payment_method={payment_method}, sale_status={sale_status}")
        print(f"📄 Pagination: page={page}, per_page={per_page}")
        
        # Build the query with filters
        query = Sale.query
        
        # Apply filters if provided
        if start_date:
            try:
                start_datetime = datetime.strptime(start_date, "%Y-%m-%d")
                query = query.filter(Sale.sale_date >= start_datetime)
            except ValueError:
                print(f"❌ Invalid start_date format: {start_date}")
                return jsonify({"error": "Invalid date format. Use YYYY-MM-DD"}), 400
                
        if end_date:
            try:
                # Add one day to include the end date fully
                end_datetime = datetime.strptime(end_date, "%Y-%m-%d")
                end_datetime = datetime(end_datetime.year, end_datetime.month, end_datetime.day)
                query = query.filter(Sale.sale_date <= end_datetime)
            except ValueError:
                print(f"❌ Invalid end_date format: {end_date}")
                return jsonify({"error": "Invalid date format. Use YYYY-MM-DD"}), 400
                
        if product_id:
            query = query.filter_by(product_id=product_id)
            
        if payment_method:
            query = query.filter_by(payment_method=payment_method)
            
        if sale_status:
            query = query.filter_by(sale_status=sale_status)
        
        # Order by most recent sales first
        query = query.order_by(Sale.sale_date.desc())
        
        # Get total count before pagination
        total_count = query.count()
        
        # Apply pagination
        paginated_sales = query.paginate(page=page, per_page=per_page, error_out=False)
        
        # Format the response
        sales_list = []
        for sale in paginated_sales.items:
            # Get associated product
            product = Product.query.get(sale.product_id)
            
            # Calculate unit price and profit
            unit_price = sale.total_price / sale.quantity_sold if sale.quantity_sold > 0 else 0
            profit = sale.total_price - (product.selling_price * sale.quantity_sold) if product else 0
            
            sale_data = {
                "id": sale.id,
                "sale_date": sale.sale_date,
                "quantity_sold": sale.quantity_sold,
                "total_price": sale.total_price,
                "payment_method": sale.payment_method,
                "sale_status": sale.sale_status,
                "unit_price": unit_price,
                "profit": profit,
                "product": {
                    "id": product.id,
                    "name": product.name,
                    "category_id": product.category_id,
                    "category_name": product.category.name if product.category else None,
                    "selling_price": product.selling_price,
                    "stock_quantity": product.stock_quantity
                } if product else None
            }
            sales_list.append(sale_data)
        
        # Prepare pagination info
        pagination = {
            "total_items": total_count,
            "total_pages": paginated_sales.pages,
            "current_page": page,
            "per_page": per_page,
            "has_next": paginated_sales.has_next,
            "has_prev": paginated_sales.has_prev,
            "next_page": paginated_sales.next_num if paginated_sales.has_next else None,
            "prev_page": paginated_sales.prev_num if paginated_sales.has_prev else None
        }
        
        response = {
            "sales": sales_list,
            "pagination": pagination
        }
        
        print(f"✅ Returning {len(sales_list)} sales (page {page}/{paginated_sales.pages})")
        return jsonify(response), 200
         
    except Exception as e:
        print(f"❌ Error in /sales/all: {str(e)}")
        return jsonify({"error": "Server error", "details": str(e)}), 500

# ================== ORDER MANAGEMENT ==================
@app.route("/orders", methods=["POST"])
@jwt_required()
def create_order():
    """Create a customer order"""
    data = request.json
    order = Order(
        customer_name=data["customer_name"], products_ordered=data["products_ordered"],
        order_status=data["order_status"], shipping_info=data["shipping_info"]
    )
    db.session.add(order)
    db.session.commit()
    return jsonify({"message": "Order created successfully"}), 201

@app.route("/orders", methods=["GET"])
@jwt_required()
def get_orders():
    """Retrieve all customer orders"""
    orders = Order.query.all()
    return jsonify([{
        "id": o.id, "customer_name": o.customer_name, "products_ordered": o.products_ordered,
        "order_status": o.order_status, "order_date": o.order_date
    } for o in orders])

@app.route("/categories", methods=["GET"])
# @jwt_required()
def get_categories():
    """Get all categories"""
    print("📩 Received GET /categories request")
 
    try:
        categories = Category.query.all()
        response = [{
            "id": c.id,
            "name": c.name,
            "description": c.description,
            "created_at": c.created_at,
            "updated_at": c.updated_at
        } for c in categories]
 
        print("✅ Returning Categories:", response)
        return jsonify(response)
    except Exception as e:
        print("❌ Error in /categories:", str(e))
        return jsonify({"error": "Server error"}), 500
 
@app.route("/categories", methods=["POST"])
def add_category():
    """Add a new category with detailed logging"""
    
    # Ensure request is JSON
    if not request.is_json:
        print("❌ Error: Request content-type is not JSON")
        return jsonify({"error": "Invalid content type. Expected application/json"}), 400

    try:
        data = request.get_json()
        print("📥 Received Data:", json.dumps(data, indent=2))

        if not data:
            return jsonify({"error": "No data provided"}), 400

        # Validate required fields
        required_fields = ["name"]
        missing_fields = [field for field in required_fields if field not in data]

        if missing_fields:
            print(f"❌ Missing fields: {missing_fields}")
            return jsonify({"error": "Missing required fields", "missing": missing_fields}), 400

        # Create new category
        new_category = Category(
            name=str(data["name"]),
            description=str(data.get("description", ""))  # Default empty description
        )

        db.session.add(new_category)
        db.session.commit()
        print("✅ Category added successfully!")

        return jsonify({"message": "Category added successfully", "category_id": new_category.id}), 201

    except ValueError as ve:
        print(f"❌ Data Type Error: {str(ve)}")
        return jsonify({"error": "Invalid data type", "details": str(ve)}), 422

    except Exception as e:
        if "UNIQUE constraint failed" in str(e):
            return jsonify({"error": "Category name must be unique"}), 409  # Conflict error

        print(f"❌ Unexpected Server Error: {str(e)}")
        return jsonify({"error": "Server error", "details": str(e)}), 500
 
@app.route("/categories/<int:id>", methods=["PUT"])
@jwt_required()
def update_category(id):
    """Update category details"""
    category = Category.query.get(id)
    if not category:
        return jsonify({"error": "Category not found"}), 404
 
    data = request.json
    category.name = data.get("name", category.name)
    category.description = data.get("description", category.description)
 
    db.session.commit()
    return jsonify({"message": "Category updated successfully"})
 
@app.route("/categories/<int:id>", methods=["DELETE"])
@jwt_required()
def delete_category(id):
    """Delete a category"""
    category = Category.query.get(id)
    if not category:
        return jsonify({"error": "Category not found"}), 404
 
    db.session.delete(category)
    db.session.commit()
    return jsonify({"message": "Category deleted successfully"})
 
@app.route("/stock_levels", methods=["GET"])
def get_stock_levels():
    """Get stock levels for all products"""
    try:
        products = Product.query.all()
        response = [{
            "name": p.name,
            "category": p.category.name,
            "stock_quantity": p.stock_quantity
        } for p in products]

        return jsonify(response), 200
    except Exception as e:
        return jsonify({"error": "Server error", "details": str(e)}), 500

@app.route("/best_selling_product", methods=["GET"])
def get_best_selling_product():
    """Get the best selling product details"""
    try:
        # Calculate total quantities sold and cumulative price for each product
        sales_data = db.session.query(
            Product.id,
            Product.name,
            Product.category_id,
            db.func.sum(Sale.quantity_sold).label("total_quantity_sold"),
            db.func.sum(Sale.total_price).label("cumulative_price")
        ).join(Sale).group_by(Product.id).order_by(db.desc("total_quantity_sold")).first()

        if not sales_data:
            return jsonify({"message": "No sales data available"}), 404

        product = Product.query.get(sales_data.id)
        response = {
            "name": product.name,
            "category": product.category.name,
            "cumulative_price": sales_data.cumulative_price,
            "quantities_sold": sales_data.total_quantity_sold,
            "stock_quantity": product.stock_quantity
        }

        return jsonify(response), 200
    except Exception as e:
        return jsonify({"error": "Server error", "details": str(e)}), 500

@app.route("/colors", methods=["GET"])
def get_colors():
    """Get all colors"""
    try:
        colors = Color.query.all()
        response = [{
            "id": c.id,
            "name": c.name,
            "created_at": c.created_at,
            "updated_at": c.updated_at
        } for c in colors]

        return jsonify(response), 200
    except Exception as e:
        return jsonify({"error": "Server error", "details": str(e)}), 500

@app.route("/colors", methods=["POST"])
def add_color():
    """Add a new color"""
    data = request.json
    if not data or "name" not in data:
        return jsonify({"error": "Name is required"}), 400

    try:
        new_color = Color(name=data["name"])
        db.session.add(new_color)
        db.session.commit()
        return jsonify({"message": "Color added successfully", "color_id": new_color.id}), 201
    except Exception as e:
        return jsonify({"error": "Server error", "details": str(e)}), 500

# ================== RUN APPLICATION ==================
if __name__ == "__main__":
    socketio.run(app, debug=True)

