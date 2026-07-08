import unittest

from app import app


class ApiFlaskTests(unittest.TestCase):
    def test_root_endpoint_returns_status_message(self):
        client = app.test_client()
        response = client.get("/")

        self.assertEqual(response.status_code, 200)
        self.assertIn(b"Meka RPA", response.data)

    def test_condominios_route_returns_csv_entries(self):
        client = app.test_client()
        response = client.get("/condominios")

        self.assertEqual(response.status_code, 200)
        self.assertGreaterEqual(len(response.get_json()), 1)
        self.assertIn("nome", response.get_json()[0])


if __name__ == "__main__":
    unittest.main()
