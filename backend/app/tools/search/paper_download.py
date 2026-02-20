from typing import Dict, Any, List
from app.tools.base import BaseTool
from app.application.services.document_service import document_service
from app.infrastructure.logging.config import logger
import requests
import asyncio
import random
import re
from app.core.config import settings


class PaperDownloadTool(BaseTool):
    name = "PaperDownloadTool"
    description = "下载论文 PDF 并保存到文档系统。可以与 SearchTool 或 FilterTool 配合使用"
    parameters = {
        "papers": {"type": "array", "description": "论文列表（若本步骤紧接在 SearchTool 或 FilterTool 之后，可不传，系统自动使用上一步结果）", "required": True},
        "max_downloads": {"type": "integer", "description": "最大下载数量", "default": 3},
        "user_id": {"type": "string", "description": "用户ID（可选，用于关联文档到用户）", "default": ""},
        "max_concurrent": {"type": "integer", "description": "最大并发下载数", "default": 2}
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

    def _get_headers(self) -> Dict[str, str]:
        user_agents = [
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:121.0) Gecko/20100101 Firefox/121.0",
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.2 Safari/605.1.15"
        ]
        return {
            "User-Agent": random.choice(user_agents),
            "Accept": "application/pdf,text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
            "Accept-Language": "en-US,en;q=0.9,zh-CN;q=0.8,zh;q=0.7",
            "Accept-Encoding": "gzip, deflate, br",
            "Connection": "keep-alive",
            "Upgrade-Insecure-Requests": "1",
            "Referer": "https://scholar.google.com/"
        }

    async def _download_single_paper(self, paper: Dict, user_id: str, semaphore: asyncio.Semaphore) -> Dict:
        async with semaphore:
            pdf_url = paper.get("pdfUrl")
            if not pdf_url:
                return {
                    "success": False,
                    "title": paper.get("title", "未知标题"),
                    "error": "无 PDF 链接"
                }

            title = paper.get("title", "unknown_paper")
            year = paper.get("year", "")
            cited_by = paper.get("citedBy", paper.get("citations", 0))

            safe_title = re.sub(r'[^\w\-_ ]', '_', title)
            safe_title = re.sub(r'\s+', ' ', safe_title).strip()
            
            if year:
                filename = f"{year}_{safe_title}.pdf"
            else:
                filename = f"{safe_title}.pdf"

            try:
                existing_doc = document_service.find_existing_paper(user_id, pdf_url=pdf_url, title=title)
                if existing_doc:
                    logger.info(f"论文已存在，跳过下载: {title}")
                    return {
                        "success": True,
                        "cached": True,
                        "doc_id": existing_doc["id"],
                        "title": title,
                        "year": year,
                        "cited_by": cited_by,
                        "pdf_url": pdf_url,
                        "file_name": existing_doc.get("original_name", filename),
                        "file_size": existing_doc.get("file_size", 0),
                        "message": "使用缓存，未重新下载"
                    }
                
                logger.info(f"正在下载: {title}")
                
                headers = self._get_headers()
                
                response = requests.get(
                    pdf_url, 
                    timeout=30, 
                    headers=headers,
                    allow_redirects=True,
                    verify=False
                )
                response.raise_for_status()
                
                content_type = response.headers.get("content-type", "")
                if "pdf" not in content_type.lower() and len(response.content) > 0:
                    logger.warning(f"响应类型不是 PDF: {content_type}, 但将尝试使用")
                
                pdf_content = response.content

                doc = document_service.upload_document(
                    user_id=user_id,
                    filename=filename,
                    file_content=pdf_content
                )

                logger.info(f"下载成功: {title}")
                return {
                    "success": True,
                    "cached": False,
                    "doc_id": doc["id"],
                    "title": title,
                    "year": year,
                    "cited_by": cited_by,
                    "pdf_url": pdf_url,
                    "file_name": doc.get("file_name", filename),
                    "file_size": doc.get("file_size", 0)
                }

            except requests.exceptions.RequestException as e:
                logger.error(f"下载失败: {title}, 错误: {e}")
                return {
                    "success": False,
                    "title": title,
                    "pdf_url": pdf_url,
                    "error": str(e)
                }
            except Exception as e:
                logger.error(f"保存文档失败: {title}, 错误: {e}", exc_info=True)
                return {
                    "success": False,
                    "title": title,
                    "pdf_url": pdf_url,
                    "error": str(e)
                }

    async def run(self, **kwargs) -> Dict[str, Any]:
        papers = kwargs.get("papers", [])
        max_downloads = kwargs.get("max_downloads", 3)
        user_id = kwargs.get("user_id", "")
        max_concurrent = kwargs.get("max_concurrent", 2)

        logger.info(f"开始下载 {len(papers)} 篇论文, 最大 {max_downloads} 篇, 并发 {max_concurrent} 篇")

        if not papers or not isinstance(papers, list):
            return {
                "success": False,
                "error": "无效的论文列表"
            }

        if not user_id:
            user_id = "system"

        papers_to_download = papers[:max_downloads]
        semaphore = asyncio.Semaphore(max_concurrent)
        
        tasks = [
            self._download_single_paper(paper, user_id, semaphore)
            for paper in papers_to_download
            if isinstance(paper, dict) and paper.get("pdfUrl")
        ]
        
        results = await asyncio.gather(*tasks)

        downloaded_docs = []
        failed_downloads = []
        
        for result in results:
            if result.get("success"):
                downloaded_docs.append({
                    "doc_id": result["doc_id"],
                    "title": result["title"],
                    "year": result["year"],
                    "cited_by": result["cited_by"],
                    "pdf_url": result["pdf_url"],
                    "file_name": result["file_name"],
                    "file_size": result["file_size"]
                })
            else:
                failed_downloads.append({
                    "title": result["title"],
                    "pdf_url": result.get("pdf_url", ""),
                    "error": result.get("error", "未知错误")
                })

        return {
            "success": True,
            "downloaded_docs": downloaded_docs,
            "failed_downloads": failed_downloads,
            "total_downloaded": len(downloaded_docs),
            "total_failed": len(failed_downloads),
            "message": f"下载完成：成功 {len(downloaded_docs)} 篇，失败 {len(failed_downloads)} 篇"
        }
