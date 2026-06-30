import unittest

from app import app


class ApiFlaskTests(unittest.TestCase):
    def test_root_endpoint_returns_status_message(self):
        client = app.test_client()
        response = client.get("/")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.get_json(), {"message": "Meka RPA API is running."})

    def test_condominios_route_returns_csv_entries(self):
        client = app.test_client()
        response = client.get("/condominios")

        self.assertEqual(response.status_code, 200)
        self.assertGreaterEqual(len(response.get_json()), 1)
        self.assertIn("CONDOMINIO ALAMEDA EUROPA", response.get_json()[0]["nome"])


if __name__ == "__main__":
    unittest.main()
