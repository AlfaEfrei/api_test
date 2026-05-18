"""Script utilisable dans une tâche planifiée PythonAnywhere.

Exemple Scheduled Task :
python3.13 /home/VOTRE_USER/ATELIER_AUTOMATISATION_TESTS/run_tests.py
"""

from pprint import pprint

from storage import init_db, save_run
from tester.runner import run_all_tests

if __name__ == "__main__":
    init_db()
    result = run_all_tests()
    run_id = save_run(result)
    print(f"Run enregistré avec id={run_id}")
    pprint(result["summary"])
