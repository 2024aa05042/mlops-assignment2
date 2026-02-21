"""Run pytest and produce JUnit XML and an HTML report in `reports/`.

Usage:
  python scripts/run_tests.py

Reports:
  - reports/junit.xml
  - reports/report.html
"""
import os
import shutil
import pytest


def main():
    reports_dir = os.path.join(os.getcwd(), "reports")
    if os.path.exists(reports_dir):
        shutil.rmtree(reports_dir)
    os.makedirs(reports_dir, exist_ok=True)

    junit_path = os.path.join(reports_dir, "junit.xml")
    html_path = os.path.join(reports_dir, "report.html")

    # run pytest with coverage, junit xml and html report
    cov_xml = os.path.join(reports_dir, "coverage.xml")
    cov_html = os.path.join(reports_dir, "coverage_html")
    args = [
      "-q",
      f"--junitxml={junit_path}",
      f"--html={html_path}",
      "--self-contained-html",
      "--cov=src",
      f"--cov-report=xml:{cov_xml}",
      f"--cov-report=html:{cov_html}",
    ]
    print("Running pytest and writing reports to:")
    print(" -", junit_path)
    print(" -", html_path)
    rc = pytest.main(args)
    if rc == 0:
        print("Tests passed")
    else:
        print(f"Tests finished with return code: {rc}")


if __name__ == "__main__":
    main()
