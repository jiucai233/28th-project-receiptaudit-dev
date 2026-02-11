from __future__ import annotations

import json
from datetime import datetime


class AuditService:
    def _rule_fallback(self, receipt_data: dict) -> dict:
        violations = []
        banned = ["참이슬", "소주", "맥주", "와인", "카스", "담배"]

        for item in receipt_data.get("items", []):
            name = str(item.get("name", ""))
            if any(k in name for k in banned):
                violations.append(
                    {
                        "item_id": item.get("id", 0),
                        "reason": "금지 품목 구매 의심",
                        "policy_reference": "제3조 금지 품목",
                    }
                )

        hour = None
        dt_text = str(receipt_data.get("date", ""))
        for fmt in ("%Y-%m-%d %H:%M", "%Y-%m-%d", "%Y.%m.%d %H:%M"):
            try:
                hour = datetime.strptime(dt_text.replace("/", "-").replace(".", "-"), fmt).hour
                break
            except ValueError:
                continue

        if hour is not None and (hour < 8 or hour >= 22):
            violations.append(
                {
                    "item_id": 0,
                    "reason": "허용 시간 외 결제 의심",
                    "policy_reference": "제4조 허용 시간",
                }
            )

        if violations:
            return {
                "audit_decision": "Anomaly Detected",
                "violation_score": min(1.0, 0.75 + 0.05 * len(violations)),
                "violations": violations,
                "reasoning": "규칙 기반 점검에서 위반 가능성이 확인되었습니다.",
            }

        return {
            "audit_decision": "Pass",
            "violation_score": 0.08,
            "violations": [],
            "reasoning": "규칙 기반 점검에서 명확한 위반 항목이 확인되지 않았습니다.",
        }

    def check(self, receipt_data: dict) -> dict:
        try:
            from core.audit_agent.reasoning import AuditReasoning
            from core.rag_engine.embedder import RegulationEmbedder
            from core.rag_engine.vector_db import VectorDBManager

            embedder = RegulationEmbedder()
            db = VectorDBManager()
            docs = db.search_rules(
                json.dumps(receipt_data, ensure_ascii=False),
                embedder.get_embedding_model(),
                k=3,
            )
            rules_text = "\n\n".join(doc.page_content for doc in docs)
            if not rules_text:
                return self._rule_fallback(receipt_data)

            result = AuditReasoning().analyze(receipt_data, rules_text)
            result.setdefault("audit_decision", "Pass")
            result.setdefault("violation_score", 0.2)
            result.setdefault("violations", [])
            result.setdefault("reasoning", "LLM 기반 판단")
            return result
        except Exception:
            return self._rule_fallback(receipt_data)
