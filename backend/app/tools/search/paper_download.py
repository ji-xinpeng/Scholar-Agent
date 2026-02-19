from typing import Dict, Any, List
from app.tools.base import BaseTool
from app.application.services.document_service import document_service
from app.infrastructure.logging.config import logger
import requests
import os
from app.core.config import settings


class PaperDownloadTool(BaseTool):
    name = "PaperDownloadTool"
    description = "下载论文 PDF 并保存到文档系统。可以与 SearchTool 或 FilterTool 配合使用"
    parameters = {
        "papers": {"type": "array", "description": "论文列表（若本步骤紧接在 SearchTool 或 FilterTool 之后，可不传，系统自动使用上一步结果）", "required": True},
        "max_downloads": {"type": "integer", "description": "最大下载数量", "default": 3},
        "user_id": {"type": "string", "description": "用户ID（可选，用于关联文档到用户）", "default": ""}
    }

    def resolve_params(self, params: Dict[str, Any], previous_results: Dict[str, Any]) -> Dict[str, Any]:
        params = dict(params) if params else {}
        if not params.get("papers") or params.get("papers") == []:
            for prev_tool in ("FilterTool", "SearchTool"):
                if prev_tool in previous_results:
                    prev_result = previous_results[prev_tool]
                    if isinstance(prev_result, dict) and prev_result.get("success"):
                        papers = prev_result.get("papers")
                        if isinstance(papers, list) and papers:
                            params["papers"] = papers
                            logger.info(f"{self.name} 自动使用 {prev_tool} 的结果（{len(papers)} 篇论文）")
                            break
        return params

    async def run(self, **kwargs) -> Dict[str, Any]:
        papers = kwargs.get("papers", [])
        max_downloads = kwargs.get("max_downloads", 3)
        user_id = kwargs.get("user_id", "")

        if not papers or not isinstance(papers, list):
            return {
                "success": False,
                "error": "无效的论文列表"
            }

        if not user_id:
            user_id = "system"

        downloaded_docs = []
        failed_downloads = []

        try:
            download_count = 0
            for paper in papers:
                if download_count >= max_downloads:
                    break

                if not isinstance(paper, dict):
                    continue

                pdf_url = paper.get("pdfUrl")
                if not pdf_url:
                    logger.warning(f"论文无 PDF 链接，跳过: {paper.get('title', '未知标题')}")
                    continue

                title = paper.get("title", "unknown_paper")
                year = paper.get("year", "")
                cited_by = paper.get("citedBy", paper.get("citations", 0))

                safe_title = "".join([c if c.isalnum() or c in (' ', '-', '_') else '_' for c in title])
                filename = f"{safe_title}.pdf"
                if year:
                    filename = f"{year}_{filename}"

                try:
                    logger.info(f"正在下载: {title}")
                    response = requests.get(pdf_url, timeout=30, headers={
                        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
                    })
                    response.raise_for_status()

                    pdf_content = response.content

                    doc = document_service.upload_document(
                        user_id=user_id,
                        filename=filename,
                        file_content=pdf_content
                    )

                    downloaded_docs.append({
                        "doc_id": doc["id"],
                        "title": title,
                        "year": year,
                        "cited_by": cited_by,
                        "pdf_url": pdf_url,
                        "file_name": doc["file_name"],
                        "file_size": doc["file_size"]
                    })

                    download_count += 1
                    logger.info(f"下载成功: {title}")

                except requests.exceptions.RequestException as e:
                    logger.error(f"下载失败: {title}, 错误: {e}")
                    failed_downloads.append({
                        "title": title,
                        "pdf_url": pdf_url,
                        "error": str(e)
                    })
                except Exception as e:
                    logger.error(f"保存文档失败: {title}, 错误: {e}", exc_info=True)
                    failed_downloads.append({
                        "title": title,
                        "pdf_url": pdf_url,
                        "error": str(e)
                    })

            return {
                "success": True,
                "downloaded_docs": downloaded_docs,
                "failed_downloads": failed_downloads,
                "total_downloaded": len(downloaded_docs),
                "total_failed": len(failed_downloads),
                "message": f"下载完成：成功 {len(downloaded_docs)} 篇，失败 {len(failed_downloads)} 篇"
            }
        except Exception as e:
            logger.error(f"PaperDownloadTool 执行失败: {e}", exc_info=True)
            return {
                "success": False,
                "error": f"下载失败: {str(e)}"
            }
