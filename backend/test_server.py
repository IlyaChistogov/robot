from server import app
import json

def test():
    client = app.test_client()

    # 1. Test status
    r1 = client.get("/api/status")
    assert r1.status_code == 200, f"Status failed: {r1.status_code}"
    print("[OK] GET /api/status:", r1.json)

    # 2. Test telemetry
    r2 = client.get("/api/telemetry")
    assert r2.status_code == 200, f"Telemetry failed: {r2.status_code}"
    data = r2.json
    print(f"[OK] GET /api/telemetry: Battery={data['battery']['voltage']}V, Lidar={len(data['lidar']['ranges'])} points")

    # 3. Test drive
    r3 = client.post("/api/drive", json={"linear": 0.5, "angular": 0.2})
    assert r3.status_code == 200, f"Drive failed: {r3.status_code}"
    print("[OK] POST /api/drive:", r3.json)

    # 4. Test E-Stop
    r4 = client.post("/api/stop")
    assert r4.status_code == 200
    print("[OK] POST /api/stop:", r4.json)

    # 5. Check E-stop status in telemetry
    r5 = client.get("/api/telemetry")
    assert r5.json["status"]["emergency_stop"] is True
    print("[OK] Telemetry reflects Emergency Stop state!")

    # 6. Reset E-stop
    r6 = client.post("/api/reset_stop")
    assert r6.status_code == 200
    print("[OK] Reset Stop:", r6.json)

    print("\n ВСЕ СЕРВЕРНЫЕ ТЕСТЫ ПРОЙДЕНЫ УСПЕШНО!")

if __name__ == "__main__":
    test()
