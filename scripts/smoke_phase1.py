"""Phase-one smoke test against a running EduMate deployment.

Usage:
    python scripts/smoke_phase1.py --base-url http://127.0.0.1:8001 \
        --web-url http://127.0.0.1:8080 --with-rag

The script expects demo data from ``scripts/seed_demo.py``.
"""

from __future__ import annotations

import argparse
import os
import sys

import httpx

DEFAULT_PASSWORD = "EduMate@2026"


class Smoke:
    def __init__(self, base_url: str, web_url: str | None, password: str, with_rag: bool):
        self.base_url = base_url.rstrip("/")
        self.web_url = web_url.rstrip("/") if web_url else None
        self.password = password
        self.with_rag = with_rag
        self.failures: list[str] = []
        self.client = httpx.Client(timeout=30)

    def check(self, name: str, condition: bool, detail: str = "") -> None:
        if condition:
            print(f"[PASS] {name}")
        else:
            suffix = f" ({detail})" if detail else ""
            print(f"[FAIL] {name}{suffix}")
            self.failures.append(name)

    def request(self, method: str, path: str, **kwargs):
        return self.client.request(method, f"{self.base_url}{path}", **kwargs)

    def login(self, username: str) -> dict[str, str]:
        response = self.request(
            "POST",
            "/api/v1/auth/login",
            json={"username": username, "password": self.password},
        )
        self.check(f"login {username}", response.status_code == 200, response.text[:200])
        if response.status_code != 200:
            return {}
        return {"Authorization": f"Bearer {response.json()['data']['access_token']}"}

    def run(self) -> int:
        live = self.request("GET", "/api/v1/health/live")
        self.check("health live", live.status_code == 200)
        ready = self.request("GET", "/api/v1/health/ready")
        ready_data = ready.json().get("data", {}) if ready.status_code == 200 else {}
        self.check(
            "health ready",
            ready.status_code == 200 and ready_data.get("checks", {}).get("database") == "ok",
            str(ready_data),
        )

        admin = self.login("admin")
        teacher = self.login("teacher")
        student = self.login("student")
        if not (admin and teacher and student):
            self.client.close()
            return 1

        stats = self.request("GET", "/api/v1/admin/stats", headers=admin)
        self.check(
            "admin stats with demo users",
            stats.status_code == 200 and stats.json()["data"]["total_users"] >= 5,
            stats.text[:200],
        )
        roles = self.request("GET", "/api/v1/admin/roles", headers=admin)
        self.check("admin roles", roles.status_code == 200)
        policy = self.request("GET", "/api/v1/admin/review-policy", headers=admin)
        self.check("admin review policy", policy.status_code == 200)
        audits = self.request("GET", "/api/v1/admin/audit-logs?page_size=5", headers=admin)
        self.check("admin audit logs", audits.status_code == 200)

        courses = self.request("GET", "/api/v1/courses?page_size=100", headers=teacher)
        self.check(
            "teacher demo courses",
            courses.status_code == 200 and courses.json()["data"]["total"] >= 2,
            courses.text[:200],
        )
        materials = self.request("GET", "/api/v1/materials?page_size=100", headers=teacher)
        self.check(
            "teacher demo materials",
            materials.status_code == 200 and materials.json()["data"]["total"] >= 1,
            materials.text[:200],
        )

        home = self.request("GET", "/api/v1/home/overview", headers=student)
        self.check("student home", home.status_code == 200)
        if home.status_code == 200:
            self.check(
                "student enrolled courses",
                home.json()["data"]["stats"]["course_count"] >= 1,
                str(home.json()["data"]["stats"]),
            )
        student_courses = self.request("GET", "/api/v1/courses?page_size=100", headers=student)
        self.check("student courses", student_courses.status_code == 200)
        student_materials = self.request("GET", "/api/v1/materials?page_size=100", headers=student)
        self.check("student materials", student_materials.status_code == 200)
        recommendations = self.request("GET", "/api/v1/recommendations", headers=student)
        self.check("student recommendations", recommendations.status_code == 200)
        kbs = self.request("GET", "/api/v1/knowledge-bases", headers=student)
        self.check("student knowledge bases", kbs.status_code == 200)
        history = self.request("GET", "/api/v1/qa/history", headers=student)
        self.check("student QA history", history.status_code == 200)

        if self.with_rag:
            rag = self.request("GET", "/api/v1/materials/rag-health", headers=student)
            rag_data = rag.json().get("data", {}) if rag.status_code == 200 else {}
            self.check(
                "real RAG healthy",
                rag.status_code == 200 and rag_data.get("status") == "ok",
                str(rag_data),
            )

        if self.web_url:
            web = self.client.get(self.web_url)
            self.check("web SPA", web.status_code == 200)
            web_login = self.client.get(f"{self.web_url}/login")
            self.check("web login route", web_login.status_code == 200)
            web_health = self.client.get(f"{self.web_url}/healthz")
            self.check("web nginx health", web_health.status_code == 200)

        self.client.close()
        if self.failures:
            print(f"\n{len(self.failures)} smoke check(s) failed.")
            return 1
        print("\nAll phase-one smoke checks passed.")
        return 0


def main() -> None:
    parser = argparse.ArgumentParser(description="EduMate phase-one smoke test")
    parser.add_argument("--base-url", default="http://127.0.0.1:8001")
    parser.add_argument("--web-url", default=os.getenv("EDUMATE_WEB_URL", ""))
    parser.add_argument(
        "--password",
        default=os.getenv("SEED_DEMO_PASSWORD", DEFAULT_PASSWORD),
    )
    parser.add_argument("--with-rag", action="store_true")
    args = parser.parse_args()
    smoke = Smoke(args.base_url, args.web_url or None, args.password, args.with_rag)
    raise SystemExit(smoke.run())


if __name__ == "__main__":
    sys.exit(main())
