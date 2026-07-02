from __future__ import annotations

import asyncio
import hashlib
import logging
from datetime import datetime

import httpx

from app.core.settings import Settings
from app.models.schemas import EvidenceDocument, SourceType, TrustTier
from app.retrieval.sources import cdc, clinicaltrials, fda, nih, pubmed

logger = logging.getLogger(__name__)


def _id(condition: str, source: str, title: str) -> str:
    digest = hashlib.sha256(f"{condition}:{source}:{title}".encode()).hexdigest()[:16]
    return f"ev_{digest}"


def _doc(
    condition: str,
    source_type: SourceType,
    title: str,
    text: str,
    url: str,
    trust_tier: TrustTier,
    score: float,
    metadata: dict,
) -> EvidenceDocument:
    return EvidenceDocument(
        id=_id(condition, source_type.value, title),
        condition=condition,
        source_type=source_type,
        title=title,
        text=text,
        url=url,
        trust_tier=trust_tier,
        score=score,
        published_at=datetime.utcnow(),
        metadata=metadata,
    )


class ExternalRetrievalService:
    """Async retrieval facade. Pulls live data from NIH/CDC (treatment & diagnosis
    guidance) and FDA/PubMed (drug information and research literature), falling
    back to deterministic offline fixtures per-source if a live call fails so the
    briefing pipeline never breaks."""

    def __init__(self, settings: Settings) -> None:
        self.settings = settings

    async def fetch_guidelines(self, condition: str) -> list[EvidenceDocument]:
        if not self.settings.use_live_external_apis:
            return [self._offline_nih_fixture(condition), self._offline_cdc_fixture(condition)]

        async with httpx.AsyncClient(timeout=self.settings.external_api_timeout_seconds) as client:
            nih_result, cdc_results = await asyncio.gather(
                self._safe(nih.fetch(condition, self.settings, client), "nih_medlineplus"),
                self._safe(cdc.fetch(condition, self.settings, client), "cdc"),
            )

        docs = []
        if nih_result:
            docs.append(
                _doc(
                    condition,
                    SourceType.guideline,
                    nih_result["title"],
                    nih_result["text"],
                    nih_result["url"],
                    TrustTier.high,
                    0.92,
                    {"provider": "nih_medlineplus", "retrieval_mode": "live"},
                )
            )
        else:
            docs.append(self._offline_nih_fixture(condition))

        if cdc_results:
            for item in cdc_results:
                docs.append(
                    _doc(
                        condition,
                        SourceType.guideline,
                        item["title"],
                        item["text"],
                        item["url"],
                        TrustTier.high,
                        0.9,
                        {"provider": "cdc", "retrieval_mode": "live"},
                    )
                )
        else:
            docs.append(self._offline_cdc_fixture(condition))

        return docs

    async def fetch_literature(self, condition: str) -> list[EvidenceDocument]:
        if not self.settings.use_live_external_apis:
            return [self._offline_literature_fixture(condition)]

        async with httpx.AsyncClient(timeout=self.settings.external_api_timeout_seconds) as client:
            articles = await self._safe(pubmed.fetch(condition, self.settings, client), "pubmed")

        if not articles:
            return [self._offline_literature_fixture(condition)]

        return [
            _doc(
                condition,
                SourceType.literature,
                article["title"],
                article["text"],
                article["url"],
                TrustTier.high,
                0.88,
                {"provider": "pubmed", "retrieval_mode": "live"},
            )
            for article in articles
        ]

    async def fetch_drug_information(self, condition: str) -> list[EvidenceDocument]:
        if not self.settings.use_live_external_apis:
            return [self._offline_drug_fixture(condition)]

        async with httpx.AsyncClient(timeout=self.settings.external_api_timeout_seconds) as client:
            labels = await self._safe(fda.fetch(condition, self.settings, client), "openfda")

        if not labels:
            return [self._offline_drug_fixture(condition)]

        return [
            _doc(
                condition,
                SourceType.drug_label,
                label["title"],
                label["text"],
                label["url"],
                TrustTier.high,
                0.9,
                {"provider": "openfda", "retrieval_mode": "live"},
            )
            for label in labels
        ]

    async def fetch_trials(self, condition: str) -> list[EvidenceDocument]:
        """Fetch from ClinicalTrials.gov (Standard of Care section source)."""
        if not self.settings.use_live_external_apis:
            return [self._offline_trials_fixture(condition)]

        async with httpx.AsyncClient(timeout=self.settings.external_api_timeout_seconds) as client:
            trials = await self._safe(clinicaltrials.fetch(condition, self.settings, client), "clinicaltrials_gov")

        if not trials:
            return [self._offline_trials_fixture(condition)]

        return [
            _doc(
                condition,
                SourceType.trial,
                trial["title"],
                trial["text"],
                trial["url"],
                TrustTier.medium,
                0.85,
                {
                    "provider": "clinicaltrials_gov",
                    "retrieval_mode": "live",
                    "nct_id": trial.get("nct_id"),
                    "sponsor": trial.get("sponsor"),
                    "phase": trial.get("phase"),
                    "status": trial.get("status"),
                },
            )
            for trial in trials
        ]

    async def fetch_companies_and_institutions(self, condition: str) -> list[EvidenceDocument]:
        """Fetch from PubMed + ClinicalTrials.gov (Companies and Institutions section source)."""
        if not self.settings.use_live_external_apis:
            return [self._offline_company_fixture(condition)]

        async with httpx.AsyncClient(timeout=self.settings.external_api_timeout_seconds) as client:
            pubmed_results, trial_results = await asyncio.gather(
                self._safe(pubmed.fetch(condition, self.settings, client), "pubmed_institutions"),
                self._safe(clinicaltrials.fetch(condition, self.settings, client), "clinicaltrials_companies"),
            )

        docs: list[EvidenceDocument] = []

        # Sponsor/institution data extracted from ClinicalTrials.gov
        if trial_results:
            sponsors = list(dict.fromkeys(t["sponsor"] for t in trial_results if t.get("sponsor")))
            sponsor_text = ", ".join(sponsors) if sponsors else f"sponsors active in {condition}"
            trial_detail = " | ".join(
                f"{t.get('sponsor', 'Unknown')} ({t.get('phase', '')}): {t['title']}"
                for t in trial_results[:5]
            )
            docs.append(
                _doc(
                    condition,
                    SourceType.company,
                    f"Clinical trial sponsors and institutions for {condition}",
                    f"Active clinical trial sponsors: {sponsor_text}. Trials: {trial_detail}",
                    "https://clinicaltrials.gov/",
                    TrustTier.medium,
                    0.84,
                    {
                        "provider": "clinicaltrials_gov",
                        "retrieval_mode": "live",
                        "companies": sponsors,
                    },
                )
            )
        else:
            docs.append(self._offline_company_fixture(condition))

        # Author/institution data from PubMed research articles
        if pubmed_results:
            for article in pubmed_results[:2]:
                docs.append(
                    _doc(
                        condition,
                        SourceType.company,
                        f"Research institutions: {article['title']}",
                        article["text"],
                        article["url"],
                        TrustTier.high,
                        0.82,
                        {"provider": "pubmed", "retrieval_mode": "live"},
                    )
                )

        return docs

    async def fetch_all(self, condition: str, include_trials: bool, include_companies: bool) -> list[EvidenceDocument]:
        tasks = [
            self.fetch_guidelines(condition),
            self.fetch_literature(condition),
            self.fetch_drug_information(condition),
        ]
        if include_trials:
            tasks.append(self.fetch_trials(condition))
        if include_companies:
            tasks.append(self.fetch_companies_and_institutions(condition))
        batches = await asyncio.gather(*tasks)
        return [doc for batch in batches for doc in batch]

    @staticmethod
    async def _safe(coro, provider: str):
        try:
            return await coro
        except Exception:
            logger.warning("Live fetch failed for provider=%s; falling back to offline fixture", provider, exc_info=True)
            return None

    @staticmethod
    def _offline_trials_fixture(condition: str) -> EvidenceDocument:
        return _doc(
            condition,
            SourceType.trial,
            f"ClinicalTrials.gov development pipeline for {condition}",
            (
                f"Development programs for {condition} include mid- and late-stage studies that "
                "often evaluate disease activity, functional outcomes, biomarkers, safety, and "
                "healthcare utilization. Trial status, enrollment criteria, and endpoints should "
                "be verified in ClinicalTrials.gov before using any asset in a strategy recommendation."
            ),
            "https://clinicaltrials.gov/",
            TrustTier.medium,
            0.84,
            {"provider": "offline_clinicaltrials_fixture", "retrieval_mode": "offline_fallback"},
        )

    @staticmethod
    def _offline_company_fixture(condition: str) -> EvidenceDocument:
        return _doc(
            condition,
            SourceType.company,
            f"Company and institution ecosystem for {condition}",
            (
                f"Organizations active in {condition} clinical development include sponsors, "
                "academic medical centers, and biotechnology companies. The knowledge graph "
                "should map company, asset, mechanism, development phase, approval status, "
                "institution, principal investigator, and evidence source. Verify using "
                "ClinicalTrials.gov and recent PubMed literature."
            ),
            "https://clinicaltrials.gov/",
            TrustTier.medium,
            0.82,
            {"provider": "offline_company_fixture", "retrieval_mode": "offline_fallback"},
        )

    @staticmethod
    def _offline_nih_fixture(condition: str) -> EvidenceDocument:
        return _doc(
            condition,
            SourceType.guideline,
            f"Current standard of care overview for {condition}",
            (
                f"Clinical management of {condition} typically starts with diagnosis confirmation, "
                "risk stratification, non-pharmacologic interventions where appropriate, approved "
                "first-line therapies, escalation pathways, monitoring, shared decision making, "
                "and payer access considerations. Strategy teams should separate guideline-endorsed "
                "care from investigational approaches."
            ),
            "https://www.ncbi.nlm.nih.gov/books/",
            TrustTier.high,
            0.92,
            {"provider": "offline_nih_fixture", "retrieval_mode": "offline_fallback"},
        )

    @staticmethod
    def _offline_cdc_fixture(condition: str) -> EvidenceDocument:
        return _doc(
            condition,
            SourceType.guideline,
            f"CDC public health guidance overview for {condition}",
            (
                f"CDC guidance for {condition} typically covers case definitions, diagnostic testing "
                "recommendations, treatment considerations for at-risk populations, prevention "
                "measures, and surveillance reporting. Strategy teams should track updates to "
                "guidance versioning and effective dates."
            ),
            "https://www.cdc.gov/",
            TrustTier.high,
            0.9,
            {"provider": "offline_cdc_fixture", "retrieval_mode": "offline_fallback"},
        )

    @staticmethod
    def _offline_literature_fixture(condition: str) -> EvidenceDocument:
        return _doc(
            condition,
            SourceType.literature,
            f"Recent peer-reviewed treatment landscape for {condition}",
            (
                f"Recent literature on {condition} emphasizes therapeutic segmentation, measurable "
                "endpoints, safety surveillance, and durability of response. Emerging modalities "
                "should be interpreted by phase of development, trial design, comparator choice, "
                "and patient-selection criteria."
            ),
            "https://pubmed.ncbi.nlm.nih.gov/",
            TrustTier.high,
            0.88,
            {"provider": "offline_pubmed_fixture", "retrieval_mode": "offline_fallback"},
        )

    @staticmethod
    def _offline_drug_fixture(condition: str) -> EvidenceDocument:
        return _doc(
            condition,
            SourceType.drug_label,
            f"FDA-approved drug label overview for {condition}",
            (
                f"FDA-approved therapies for {condition} carry labeled indications, dosing, boxed "
                "warnings where applicable, and post-market safety surveillance requirements. "
                "Strategy teams should distinguish on-label from off-label use and track label "
                "updates from the regulatory record."
            ),
            "https://www.fda.gov/drugs",
            TrustTier.high,
            0.9,
            {"provider": "offline_fda_fixture", "retrieval_mode": "offline_fallback"},
        )
