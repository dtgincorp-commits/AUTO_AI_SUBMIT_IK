import os

try:
    import chromadb
    from chromadb.utils.embedding_functions import DefaultEmbeddingFunction
    _CHROMADB_AVAILABLE = True
except ImportError:
    _CHROMADB_AVAILABLE = False

CHROMA_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), "knowledge_base", "chroma_db")

_client = None
_ef = None
_collections = {}


def _get_client():
    global _client, _ef
    if _client is None:
        _client = chromadb.PersistentClient(path=CHROMA_PATH)
        _ef = DefaultEmbeddingFunction()
    return _client, _ef


def is_rag_available() -> bool:
    if not _CHROMADB_AVAILABLE:
        return False
    if not os.path.exists(CHROMA_PATH):
        return False
    try:
        client, ef = _get_client()
        collections = [c.name for c in client.list_collections()]
        return "car_specs" in collections
    except Exception:
        return False


def _get_collection(name: str):
    global _collections
    if name not in _collections:
        client, ef = _get_client()
        _collections[name] = client.get_collection(name, embedding_function=ef)
    return _collections[name]


def query_rag(query: str, collection_name: str, n_results: int = 3,
              filters: dict = None) -> list[str]:
    try:
        col = _get_collection(collection_name)
        kwargs = {"query_texts": [query], "n_results": min(n_results, col.count())}
        if filters:
            kwargs["where"] = filters
        results = col.query(**kwargs)
        return results["documents"][0] if results["documents"] else []
    except Exception:
        return []


def query_car_specs(make: str, model: str, n_results: int = 2) -> list[str]:
    return query_rag(
        f"{make} {model} specs features reliability",
        "car_specs",
        n_results=n_results,
        filters={"make": make} if make else None,
    )


def query_market_data(make: str, model: str, location: str, n_results: int = 2) -> list[str]:
    return query_rag(
        f"{make} {model} price market value {location}",
        "market_data",
        n_results=n_results,
    )


def query_dealer_data(city: str, state: str, n_results: int = 3) -> list[str]:
    return query_rag(
        f"car dealer {city} {state}",
        "dealer_data",
        n_results=n_results,
    )


def query_market_trends(make: str, location: str, n_results: int = 2) -> list[str]:
    return query_rag(
        f"{make} market trends {location}",
        "market_trends",
        n_results=n_results,
    )
