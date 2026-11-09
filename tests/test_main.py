from fastapi.testclient import TestClient

from main import app


client = TestClient(app)


def test_read_root_returns_successful_response() -> None:
    response = client.get("/")

    assert response.status_code == 200
    assert response.json() == {"message": "急診決策輔助系統 Agent 後端服務正常運行中"}
