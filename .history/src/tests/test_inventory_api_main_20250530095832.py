import pytest
from inventory_api_main import app

@pytest.fixture(autouse=True)
def client():
    # Ensure clean state before each test
    with app.test_client() as client:
        client.delete("/v1/stocks")  # resets stocks & sales & logs
        yield client

# --- Tests for /v1/stocks endpoints ---

def test_add_and_get_stock(client):
    # Add stock
    resp = client.post("/v1/stocks", json={"name": "aaa", "amount": 5})
    assert resp.status_code == 200
    data = resp.get_json()
    assert data == {"name": "aaa", "amount": 5}

    # Retrieve single stock
    resp = client.get("/v1/stocks/aaa")
    assert resp.status_code == 200
    assert resp.get_json() == {"aaa": 5}


def test_get_all_stocks(client):
    # Add multiple
    client.post("/v1/stocks", json={"name": "bbb"})         # default amount=1
    client.post("/v1/stocks", json={"name": "ccc", "amount": 2})

    # Retrieve all, sorted by name
    resp = client.get("/v1/stocks")
    assert resp.status_code == 200
    # Expect only items with amount>0, in alphabetical order
    assert resp.get_json() == {"aaa": 5, "bbb": 1, "ccc": 2}


def test_add_stock_invalid(client):
    # Invalid name (too long)
    resp = client.post("/v1/stocks", json={"name": "toolongname", "amount": 1})
    assert resp.status_code == 400
    assert resp.get_json() == {"message": "ERROR"}

    # Invalid amount (negative)
    resp = client.post("/v1/stocks", json={"name": "aaa", "amount": -3})
    assert resp.status_code == 400

# --- Tests for /v1/sales endpoints ---

def test_create_sale_and_get_sales(client):
    # Prepare stock
    client.post("/v1/stocks", json={"name": "xxx", "amount": 10})

    # Sell with price
    resp = client.post("/v1/sales", json={"name": "xxx", "amount": 3, "price": 2.5})
    assert resp.status_code == 200
    assert resp.get_json() == {"name": "xxx", "amount": 3}

    # Stock decreased
    resp = client.get("/v1/stocks/xxx")
    assert resp.get_json() == {"xxx": 7}

    # Sales total updated: 2.5 * 3 = 7.5
    resp = client.get("/v1/sales")
    assert resp.get_json() == {"sales": 7.5}


def test_create_sale_without_price(client):
    # Prepare stock
    client.post("/v1/stocks", json={"name": "yyy", "amount": 2})

    # Sell without price: sales should remain 0
    resp = client.post("/v1/sales", json={"name": "yyy", "amount": 1})
    assert resp.status_code == 200
    assert resp.get_json() == {"name": "yyy", "amount": 1}

    resp = client.get("/v1/sales")
    assert resp.get_json() == {"sales": 0.0}


def test_create_sale_invalid(client):
    # Selling more than in stock
    client.post("/v1/stocks", json={"name": "zzz", "amount": 1})
    resp = client.post("/v1/sales", json={"name": "zzz", "amount": 5})
    assert resp.status_code == 400

# --- Test reset endpoint ---

def test_reset_clears_all(client):
    # Add and sell to populate both stocks and sales
    client.post("/v1/stocks", json={"name": "a", "amount": 2})
    client.post("/v1/sales", json={"name": "a", "amount": 1, "price": 10})

    # Reset
    resp = client.delete("/v1/stocks")
    assert resp.status_code == 204

    # Stocks empty
    resp = client.get("/v1/stocks")
    assert resp.get_json() == {}

    # Sales reset to zero
    resp = client.get("/v1/sales")
    assert resp.get_json() == {"sales": 0.0}
