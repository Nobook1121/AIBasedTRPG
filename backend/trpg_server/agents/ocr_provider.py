"""Lazy PaddleOCR adapter for scanned document pages."""
from __future__ import annotations
class OcrError(RuntimeError): pass
class PaddleOcrProvider:
    def __init__(self, lang="ch"): self.lang=lang; self._engine=None
    @property
    def available(self):
        try: import paddleocr, paddle  # noqa: F401
        except Exception: return False
        return True
    def _load(self):
        if self._engine is None:
            try:
                from paddleocr import PaddleOCR
                self._engine=PaddleOCR(lang=self.lang, use_doc_orientation_classify=False, use_doc_unwarping=False, use_textline_orientation=False)
            except Exception as exc: raise OcrError("PaddleOCR 未安装或模型不可用") from exc
        return self._engine
    def extract(self, image_or_path):
        result=self._load().predict(image_or_path); rows=[]
        for item in result or []:
            data=item if isinstance(item,dict) else getattr(item,"json",lambda: {})()
            for text, score in zip(data.get("rec_texts",[]), data.get("rec_scores",[])): rows.append({"text":text,"confidence":float(score)})
        return rows
