"""Automated tests for the backend.

Run from the repo root:   python -m unittest discover -s backend -v
"""
import os
import sys
import tempfile
import unittest

# Settings must be in place BEFORE app.py is imported.
os.environ["REVOLT_FAKE_MODEL"] = "1"      # tests must not depend on Person A's model
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import app as app_module
import database
from sample_data import get_sample_data

GOOD_BATTERY = {"cycle_number": 120, "avg_voltage": 3.65, "avg_current": -1.8,
                "avg_temperature": 32.5, "discharge_time": 2800}


def sim_request(**changes):
    data = get_sample_data()
    body = {"battery_capacity_kwh": 10, "soh_percent": 78.4, "initial_soc": 0.5,
            "solar_kw": data["solar_kw"], "load_kw": data["load_kw"]}
    body.update(changes)
    return body


class ApiTestCase(unittest.TestCase):
    def setUp(self):
        # A brand-new empty database for every test.
        self.tmp = tempfile.TemporaryDirectory()
        database.DB_PATH = os.path.join(self.tmp.name, "test.db")
        database.init_db()
        self.client = app_module.app.test_client()

    def tearDown(self):
        self.tmp.cleanup()


class SampleDataTests(ApiTestCase):
    def test_returns_24_hours_of_solar_and_load(self):
        data = self.client.get("/api/sample-data").get_json()
        self.assertEqual(len(data["solar_kw"]), 24)
        self.assertEqual(len(data["load_kw"]), 24)
        self.assertEqual(data["solar_kw"][0], 0)          # no sun at midnight
        self.assertEqual(data["solar_kw"][12], max(data["solar_kw"]))  # peak at midday


class AssessTests(ApiTestCase):
    def test_example_from_contract(self):
        resp = self.client.post("/api/battery/assess", json=GOOD_BATTERY)
        body = resp.get_json()
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(body["soh_percent"], 78.4)
        self.assertEqual(body["category"], "needs_assessment")
        self.assertIn("not a safety certification", body["disclaimer"])
        for key in ("remaining_capacity_ah", "rated_capacity_ah"):
            self.assertIn(key, body)

    def test_missing_field_is_400(self):
        bad = dict(GOOD_BATTERY)
        del bad["avg_voltage"]
        resp = self.client.post("/api/battery/assess", json=bad)
        self.assertEqual(resp.status_code, 400)
        self.assertIn("avg_voltage", resp.get_json()["error"])

    def test_text_instead_of_number_is_400(self):
        resp = self.client.post("/api/battery/assess", json={**GOOD_BATTERY, "cycle_number": "abc"})
        self.assertEqual(resp.status_code, 400)

    def test_not_json_is_400(self):
        resp = self.client.post("/api/battery/assess", data="hello")
        self.assertEqual(resp.status_code, 400)

    def test_value_error_from_ml_module_becomes_400(self):
        original = app_module.predict_soh
        def picky_model(features):
            raise ValueError("avg_voltage out of range")
        app_module.predict_soh = picky_model
        try:
            resp = self.client.post("/api/battery/assess", json=GOOD_BATTERY)
        finally:
            app_module.predict_soh = original
        self.assertEqual(resp.status_code, 400)
        self.assertEqual(resp.get_json()["error"], "avg_voltage out of range")

    def test_missing_model_files_is_503(self):
        original = app_module.predict_soh
        def no_files(features):
            raise FileNotFoundError("ml/model.pkl")
        app_module.predict_soh = no_files
        try:
            resp = self.client.post("/api/battery/assess", json=GOOD_BATTERY)
        finally:
            app_module.predict_soh = original
        self.assertEqual(resp.status_code, 503)

    def test_categories(self):
        def category(cycles):
            r = self.client.post("/api/battery/assess", json={**GOOD_BATTERY, "cycle_number": cycles})
            return r.get_json()["category"]
        self.assertEqual(category(50), "candidate_for_testing")   # SOH 91
        self.assertEqual(category(120), "needs_assessment")       # SOH 78.4
        self.assertEqual(category(300), "recycle")                # SOH 46


class HistoryTests(ApiTestCase):
    def test_history_starts_empty(self):
        body = self.client.get("/api/history").get_json()
        self.assertEqual(body, {"count": 0, "assessments": []})

    def test_assessments_are_saved_newest_first(self):
        self.client.post("/api/battery/assess", json={**GOOD_BATTERY, "cycle_number": 50})
        self.client.post("/api/battery/assess", json={**GOOD_BATTERY, "cycle_number": 120})
        body = self.client.get("/api/history").get_json()
        self.assertEqual(body["count"], 2)
        newest = body["assessments"][0]
        self.assertEqual(newest["inputs"]["cycle_number"], 120)
        self.assertEqual(newest["category"], "needs_assessment")
        self.assertIn("created_at", newest)
        self.assertGreater(newest["id"], body["assessments"][1]["id"])

    def test_failed_assessments_are_not_saved(self):
        self.client.post("/api/battery/assess", json={"cycle_number": 1})
        self.assertEqual(self.client.get("/api/history").get_json()["count"], 0)

    def test_limit(self):
        for _ in range(3):
            self.client.post("/api/battery/assess", json=GOOD_BATTERY)
        self.assertEqual(self.client.get("/api/history?limit=2").get_json()["count"], 2)
        self.assertEqual(self.client.get("/api/history?limit=abc").status_code, 400)
        self.assertEqual(self.client.get("/api/history?limit=0").status_code, 400)


class SimulateTests(ApiTestCase):
    def run_sim(self, **changes):
        resp = self.client.post("/api/simulate", json=sim_request(**changes))
        self.assertEqual(resp.status_code, 200, resp.get_json())
        return resp.get_json()

    def test_shape_matches_contract(self):
        body = self.run_sim()
        self.assertEqual(body["hours"], list(range(24)))
        for key in ("soc", "charge_kw", "discharge_kw", "grid_import_kw", "solar_wasted_kw"):
            self.assertEqual(len(body[key]), 24, key)
        self.assertIn("solar_utilisation_percent", body["summary"])
        self.assertIn("grid_import_kwh", body["summary"])
        self.assertTrue(3 <= len(body["summary"]["recommendations"]) <= 4)

    def test_energy_balance_every_hour(self):
        """Solar + battery + grid must exactly cover load + charging + waste."""
        data = get_sample_data()
        body = self.run_sim()
        for h in range(24):
            supply = data["solar_kw"][h] + body["discharge_kw"][h] + body["grid_import_kw"][h]
            use = data["load_kw"][h] + body["charge_kw"][h] + body["solar_wasted_kw"][h]
            self.assertAlmostEqual(supply, use, places=2, msg=f"hour {h}")

    def test_soc_stays_between_10_and_90_percent(self):
        for soh in (100, 78.4, 40):
            body = self.run_sim(soh_percent=soh, initial_soc=0.5)
            self.assertTrue(all(0.10 - 1e-4 <= s <= 0.90 + 1e-4 for s in body["soc"]), soh)

    def test_never_charges_and_discharges_in_same_hour(self):
        body = self.run_sim()
        for c, d in zip(body["charge_kw"], body["discharge_kw"]):
            self.assertTrue(c == 0 or d == 0)

    def test_no_solar_means_everything_from_grid_after_battery_empties(self):
        body = self.run_sim(solar_kw=[0] * 24)
        self.assertEqual(body["summary"]["solar_utilisation_percent"], 0)
        usable_window = 10 * 0.784 * 0.8 * 0.5   # starts at 50% -> 40% above the 10% floor
        total_load = sum(get_sample_data()["load_kw"])
        self.assertAlmostEqual(body["summary"]["grid_import_kwh"], total_load - usable_window, delta=0.05)

    def test_big_battery_wastes_nothing_and_tiny_battery_wastes_a_lot(self):
        big = self.run_sim(battery_capacity_kwh=100)
        tiny = self.run_sim(battery_capacity_kwh=0.5)
        self.assertEqual(big["summary"]["solar_wasted_kwh"], 0)
        self.assertGreater(tiny["summary"]["solar_wasted_kwh"], 5)
        self.assertLess(tiny["summary"]["solar_utilisation_percent"],
                        big["summary"]["solar_utilisation_percent"])

    def test_older_battery_holds_less(self):
        healthy = self.run_sim(soh_percent=100)
        old = self.run_sim(soh_percent=50)
        self.assertEqual(healthy["summary"]["usable_capacity_kwh"], 10.0)
        self.assertEqual(old["summary"]["usable_capacity_kwh"], 5.0)
        self.assertGreater(old["summary"]["grid_import_kwh"], healthy["summary"]["grid_import_kwh"])

    def test_zero_health_battery_does_not_crash(self):
        body = self.run_sim(soh_percent=0)
        self.assertEqual(body["soc"], [0.0] * 24)
        self.assertEqual(sum(body["charge_kw"]), 0)

    def test_initial_soc_outside_limits_is_clamped(self):
        body = self.run_sim(initial_soc=1.0, solar_kw=[0] * 24)
        # 100% is above the 90% ceiling, so hour 0 must start from 90%, not 100%.
        self.assertLessEqual(body["soc"][0], 0.90)

    def test_bad_requests(self):
        cases = {
            "23 solar values": sim_request(solar_kw=[1] * 23),
            "negative load": sim_request(load_kw=[-1] + [1] * 23),
            "text in list": sim_request(solar_kw=["x"] * 24),
            "soh over 100": sim_request(soh_percent=120),
            "negative soh": sim_request(soh_percent=-5),
            "soc over 1": sim_request(initial_soc=1.5),
            "zero capacity": sim_request(battery_capacity_kwh=0),
            "text capacity": sim_request(battery_capacity_kwh="big"),
        }
        for label, body in cases.items():
            resp = self.client.post("/api/simulate", json=body)
            self.assertEqual(resp.status_code, 400, label)
            self.assertIn("error", resp.get_json(), label)

    def test_missing_field_is_400(self):
        body = sim_request()
        del body["load_kw"]
        resp = self.client.post("/api/simulate", json=body)
        self.assertEqual(resp.status_code, 400)
        self.assertIn("load_kw", resp.get_json()["error"])


class GeneralTests(ApiTestCase):
    def test_cors_headers_and_preflight(self):
        resp = self.client.get("/api/sample-data")
        self.assertEqual(resp.headers["Access-Control-Allow-Origin"], "*")
        pre = self.client.options("/api/simulate", headers={
            "Origin": "http://localhost:5173",
            "Access-Control-Request-Method": "POST",
            "Access-Control-Request-Headers": "Content-Type"})
        self.assertIn(pre.status_code, (200, 204))
        self.assertEqual(pre.headers["Access-Control-Allow-Origin"], "*")
        self.assertIn("Content-Type", pre.headers["Access-Control-Allow-Headers"])

    def test_unknown_url_returns_json_404(self):
        resp = self.client.get("/api/nope")
        self.assertEqual(resp.status_code, 404)
        self.assertIn("error", resp.get_json())

    def test_health(self):
        self.assertEqual(self.client.get("/api/health").get_json(), {"status": "ok", "model": "fake"})


if __name__ == "__main__":
    unittest.main()
