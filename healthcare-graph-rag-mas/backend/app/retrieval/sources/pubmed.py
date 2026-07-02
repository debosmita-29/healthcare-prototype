from __future__ import annotations

from xml.etree import ElementTree

import httpx

from app.core.settings import Settings


def _text(element) -> str:
    return " ".join("".join(element.itertext()).split())


async def fetch(condition: str, settings: Settings, client: httpx.AsyncClient, limit: int = 3) -> list[dict]:
    """Fetch recent PubMed literature on `condition` treatment via NCBI E-utilities."""
    search_params = {
        "db": "pubmed",
        "term": f"{condition} treatment",
        "retmax": limit,
        "sort": "relevance",
        "retmode": "json",
    }
    if settings.ncbi_api_key:
        search_params["api_key"] = settings.ncbi_api_key

    search_response = await client.get(f"{settings.pubmed_eutils_base_url}/esearch.fcgi", params=search_params)
    search_response.raise_for_status()
    pmids = search_response.json().get("esearchresult", {}).get("idlist", [])
    if not pmids:
        return []

    fetch_params = {"db": "pubmed", "id": ",".join(pmids), "rettype": "abstract", "retmode": "xml"}
    if settings.ncbi_api_key:
        fetch_params["api_key"] = settings.ncbi_api_key

    fetch_response = await client.get(f"{settings.pubmed_eutils_base_url}/efetch.fcgi", params=fetch_params)
    fetch_response.raise_for_status()
    root = ElementTree.fromstring(fetch_response.text)

    items = []
    for article in root.findall(".//PubmedArticle"):
        pmid = article.findtext(".//PMID")
        title_el = article.find(".//ArticleTitle")
        abstract_els = article.findall(".//Abstract/AbstractText")
        if pmid is None or title_el is None or not abstract_els:
            continue
        title = _text(title_el)
        abstract = " ".join(_text(el) for el in abstract_els)
        items.append(
            {
                "title": title,
                "text": abstract,
                "url": f"https://pubmed.ncbi.nlm.nih.gov/{pmid}/",
            }
        )
    return items
