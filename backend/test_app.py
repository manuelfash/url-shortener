import pytest
from app import app

@pytest.fixture
def client():
    app.config['TESTING'] = True
    with app.test_client() as client:
        yield client

def test_health(client):
    response = client.get('/health')
    assert response.status_code == 200

def test_shorten_missing_url(client):
    response = client.post('/shorten', json={})
    assert response.status_code == 400

def test_shorten_invalid_code(client):
    response = client.get('/nonexistentcode123')
    assert response.status_code == 404