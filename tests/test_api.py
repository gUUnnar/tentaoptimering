from __future__ import annotations

import unittest

from tentaoptimering.api import create_app


class ApiTest(unittest.TestCase):
    def test_api_exposes_required_local_contract(self) -> None:
        app = create_app()
        routes = {route.path for route in app.routes}
        self.assertTrue({
            "/api/parameters", "/api/scenarios", "/api/preparation", "/api/simulations",
            "/api/jobs/{job_id}", "/api/runs", "/api/runs/{run_id}",
            "/api/runs/{run_id}/validation", "/api/runs/compare",
        }.issubset(routes))
        self.assertEqual(app.title, "Tentaoptimering")
