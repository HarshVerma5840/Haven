import hashlib
import json
import networkx as nx
from fastapi import APIRouter, Depends
from app.database.models import User
from app.security.dependencies import require_hr_admin
from app.services.cache_service import CacheService, get_cache_service
from app.config import get_settings

router = APIRouter(prefix="/api/v1/analytics", tags=["analytics"])

def _hash_filters(filters: str) -> str:
    try:
        # Standardize JSON string to ensure same dict = same hash
        parsed = json.loads(filters)
        standardized = json.dumps(parsed, sort_keys=True)
        return hashlib.sha256(standardized.encode()).hexdigest()[:16]
    except Exception:
        return hashlib.sha256(filters.encode()).hexdigest()[:16]

@router.get("/dashboard")
def get_dashboard_summary(
    department: str = "Engineering",
    start_date: str = "2023-01-01",
    end_date: str = "2023-12-31",
    filters: str = "{}",
    model_version: str = "1.0",
    current_user: User = Depends(require_hr_admin),
    cache_service: CacheService = Depends(get_cache_service)
):
    settings = get_settings()
    filters_hash = _hash_filters(filters)
    cache_key = f"analytics:dashboard:{department}:{start_date}:{end_date}:{filters_hash}:{model_version}"
    
    cached_data = cache_service.get(cache_key)
    if cached_data:
        return cached_data
        
    response_data = {
        "department": department,
        "date_range": {"start": start_date, "end": end_date},
        "metrics": {"total_employees": 100, "high_risk_count": 15},
        "model_version": model_version
    }
    
    cache_service.set(cache_key, response_data, settings.cache_ttl_dashboard)
    return response_data

@router.get("/network")
def get_network_analysis(
    graph_type: str = "collaboration",
    start_date: str = "2023-01-01",
    end_date: str = "2023-12-31",
    filters: str = "{}",
    analysis_version: str = "1.0",
    current_user: User = Depends(require_hr_admin),
    cache_service: CacheService = Depends(get_cache_service)
):
    settings = get_settings()
    filters_hash = _hash_filters(filters)
    cache_key = f"analytics:graph:{graph_type}:{start_date}:{end_date}:{filters_hash}:{analysis_version}"
    
    cached_data = cache_service.get(cache_key)
    if cached_data:
        return cached_data
        
    # Simulate network analysis
    G = nx.Graph()
    G.add_edge("Alice", "Bob", weight=0.8)
    G.add_edge("Bob", "Charlie", weight=0.5)
    
    centrality = nx.degree_centrality(G)
    
    response_data = {
        "graph_type": graph_type,
        "analysis_version": analysis_version,
        "nodes": list(G.nodes()),
        "edges": [{"source": u, "target": v, "weight": d["weight"]} for u, v, d in G.edges(data=True)],
        "centrality": centrality
    }
    
    cache_service.set(cache_key, response_data, settings.cache_ttl_analytics)
    return response_data

