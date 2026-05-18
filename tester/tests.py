from dataclasses import asdict, dataclass
from typing import Any, Callable, Dict, List, Optional

from tester.client import ApiClient


@dataclass
class TestResult:
    name: str
    status: str
    latency_ms: Optional[float]
    details: str
    status_code: Optional[int]

    @property
    def passed(self) -> bool:
        return self.status == "PASS"

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


def _pass(name: str, response: Dict[str, Any], details: str = "OK") -> TestResult:
    return TestResult(name, "PASS", response.get("latency_ms"), details, response.get("status_code"))


def _fail(name: str, response: Dict[str, Any], details: str) -> TestResult:
    return TestResult(name, "FAIL", response.get("latency_ms"), details, response.get("status_code"))


def _is_json(response: Dict[str, Any]) -> bool:
    return "json" in (response.get("content_type") or "").lower() and response.get("json") is not None


def test_single_rate_contract(client: ApiClient) -> TestResult:
    name = "Contrat: GET /rate/EUR/USD"
    response = client.get("/rate/EUR/USD")
    data = response.get("json")

    if response.get("status_code") != 200:
        return _fail(name, response, "HTTP 200 attendu")
    if not _is_json(response):
        return _fail(name, response, "Content-Type JSON attendu")
    if not isinstance(data, dict):
        return _fail(name, response, "Objet JSON attendu")

    expected = {"date": str, "base": str, "quote": str, "rate": (int, float)}
    for field, expected_type in expected.items():
        if field not in data:
            return _fail(name, response, f"Champ manquant: {field}")
        if not isinstance(data[field], expected_type):
            return _fail(name, response, f"Type invalide pour {field}")

    if data["base"] != "EUR" or data["quote"] != "USD" or data["rate"] <= 0:
        return _fail(name, response, "Valeurs inattendues pour EUR/USD")
    return _pass(name, response, "Schéma Rate valide")


def test_rates_collection_filter(client: ApiClient) -> TestResult:
    name = "Contrat: GET /rates?base=EUR&quotes=USD,GBP"
    response = client.get("/rates", params={"base": "EUR", "quotes": "USD,GBP"})
    data = response.get("json")

    if response.get("status_code") != 200:
        return _fail(name, response, "HTTP 200 attendu")
    if not isinstance(data, list):
        return _fail(name, response, "Liste JSON attendue")
    quotes = {item.get("quote") for item in data if isinstance(item, dict)}
    if not {"USD", "GBP"}.issubset(quotes):
        return _fail(name, response, "Les devises USD et GBP doivent être présentes")
    for item in data:
        if not isinstance(item.get("rate"), (int, float)) or item.get("rate", 0) <= 0:
            return _fail(name, response, "Chaque taux doit être un nombre positif")
    return _pass(name, response, "Filtre base/quotes valide")


def test_historical_rate_date(client: ApiClient) -> TestResult:
    name = "Contrat: taux historique au 2024-01-15"
    response = client.get("/rates", params={"date": "2024-01-15", "base": "EUR", "quotes": "USD"})
    data = response.get("json")

    if response.get("status_code") != 200:
        return _fail(name, response, "HTTP 200 attendu")
    if not isinstance(data, list) or not data:
        return _fail(name, response, "Liste non vide attendue")
    item = data[0]
    if item.get("date") != "2024-01-15" or item.get("base") != "EUR" or item.get("quote") != "USD":
        return _fail(name, response, "Date/base/quote inattendues")
    return _pass(name, response, "Date historique respectée")


def test_currencies_contract(client: ApiClient) -> TestResult:
    name = "Contrat: GET /currencies"
    response = client.get("/currencies")
    data = response.get("json")

    if response.get("status_code") != 200:
        return _fail(name, response, "HTTP 200 attendu")
    if not isinstance(data, list) or len(data) < 2:
        return _fail(name, response, "Liste de devises attendue")

    by_code = {item.get("iso_code"): item for item in data if isinstance(item, dict)}
    for code in ("EUR", "USD"):
        currency = by_code.get(code)
        if not currency:
            return _fail(name, response, f"Devise absente: {code}")
        if not isinstance(currency.get("name"), str):
            return _fail(name, response, f"Nom invalide pour {code}")
    return _pass(name, response, "EUR et USD présents")


def test_providers_contract(client: ApiClient) -> TestResult:
    name = "Contrat: GET /providers"
    response = client.get("/providers")
    data = response.get("json")

    if response.get("status_code") != 200:
        return _fail(name, response, "HTTP 200 attendu")
    if not isinstance(data, list) or not data:
        return _fail(name, response, "Liste de providers attendue")

    provider = data[0]
    for field in ("key", "name", "currencies"):
        if field not in provider:
            return _fail(name, response, f"Champ provider manquant: {field}")
    if not isinstance(provider.get("currencies"), list):
        return _fail(name, response, "currencies doit être une liste")
    return _pass(name, response, "Schéma Provider valide")


def test_invalid_currency_expected_error(client: ApiClient) -> TestResult:
    name = "Robustesse: devise invalide /currency/ZZZ"
    response = client.get("/currency/ZZZ")
    data = response.get("json")

    if response.get("status_code") != 404:
        return _fail(name, response, "HTTP 404 attendu pour une devise inconnue")
    if not isinstance(data, dict) or not isinstance(data.get("message"), str):
        return _fail(name, response, "Message JSON d'erreur attendu")
    return _pass(name, response, "Erreur attendue correctement gérée")


def test_invalid_date_expected_error(client: ApiClient) -> TestResult:
    name = "Robustesse: date invalide"
    response = client.get("/rates", params={"date": "not-a-date"})
    data = response.get("json")

    if response.get("status_code") not in (400, 422):
        return _fail(name, response, "HTTP 400 ou 422 attendu pour une date invalide")
    if not isinstance(data, dict):
        return _fail(name, response, "Objet JSON d'erreur attendu")
    return _pass(name, response, "Entrée invalide rejetée proprement")


TESTS: List[Callable[[ApiClient], TestResult]] = [
    test_single_rate_contract,
    test_rates_collection_filter,
    test_historical_rate_date,
    test_currencies_contract,
    test_providers_contract,
    test_invalid_currency_expected_error,
    test_invalid_date_expected_error,
]
