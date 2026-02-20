from typing import Dict, Any, List
from app.tools.base import BaseTool
from app.infrastructure.logging.config import logger


class FilterTool(BaseTool):
    name = "FilterTool"
    description = "筛选与排序检索结果，支持多种筛选条件和排序方式。支持根据用户知识水平进行个性化筛选和排序。"
    parameters = {
        "papers": {"type": "array", "description": "论文列表（若本步骤紧接在 SearchTool 或 FilterTool 之后，可不传，系统自动使用上一步结果）", "required": True},
        "sort_by": {"type": "string", "description": "排序字段：citations（引用数）/year（年份）/title（标题）/relevance（相关性）", "default": "relevance"},
        "sort_order": {"type": "string", "description": "排序顺序：desc（降序）/asc（升序）", "default": "desc"},
        "min_citations": {"type": "integer", "description": "最小引用数", "default": 0},
        "max_citations": {"type": "integer", "description": "最大引用数（可选，0表示不限制）", "default": 0},
        "year_from": {"type": "integer", "description": "起始年份", "default": 0},
        "year_to": {"type": "integer", "description": "结束年份（可选，0表示不限制）", "default": 0},
        "title_contains": {"type": "string", "description": "标题包含关键词（可选）", "default": ""},
        "abstract_contains": {"type": "string", "description": "摘要包含关键词（可选）", "default": ""},
        "publication_contains": {"type": "string", "description": "出版信息包含关键词（可选，用于筛选会议/期刊）", "default": ""},
        "user_id": {"type": "string", "description": "用户ID，用于根据用户知识水平进行个性化筛选", "default": ""}
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
        """筛选和排序论文"""
        papers = kwargs.get("papers", [])
        sort_by = kwargs.get("sort_by", "relevance")
        sort_order = kwargs.get("sort_order", "desc")
        min_citations = kwargs.get("min_citations", 0)
        max_citations = kwargs.get("max_citations", 0)
        year_from = kwargs.get("year_from", 0)
        year_to = kwargs.get("year_to", 0)
        title_contains = kwargs.get("title_contains", "")
        abstract_contains = kwargs.get("abstract_contains", "")
        publication_contains = kwargs.get("publication_contains", "")
        user_id = kwargs.get("user_id", "")
        
        if not papers or not isinstance(papers, list):
            return {
                "success": False,
                "error": "无效的论文列表"
            }
        
        # 获取用户资料用于个性化筛选
        user_profile = None
        knowledge_level = "intermediate"
        research_field = ""
        if user_id:
            try:
                from app.application.services.user_service import user_service
                user_profile = user_service.get_profile(user_id)
                knowledge_level = user_profile.get("knowledge_level", "intermediate")
                research_field = user_profile.get("research_field", "")
                logger.info(f"FilterTool 获取到用户资料: user_id={user_id}, knowledge_level={knowledge_level}")
            except Exception as e:
                logger.warning(f"FilterTool 获取用户资料失败: {e}")
        
        # 根据知识水平调整筛选和排序策略
        if knowledge_level == "beginner":
            # 初学者：优先考虑综述类、基础类论文，引用数适中，年份较新
            if min_citations == 0:
                min_citations = 10
            if max_citations == 0:
                max_citations = 500
            if sort_by == "relevance":
                sort_by = "year"
            logger.info(f"FilterTool 应用初学者策略: min_citations={min_citations}, max_citations={max_citations}, sort_by={sort_by}")
        elif knowledge_level == "advanced":
            # 高级用户：优先考虑高引用、前沿论文
            if min_citations == 0:
                min_citations = 50
            if sort_by == "relevance":
                sort_by = "citations"
            logger.info(f"FilterTool 应用高级用户策略: min_citations={min_citations}, sort_by={sort_by}")

        try:
            filtered_papers = []
            for paper in papers:
                if not isinstance(paper, dict):
                    continue
                    
                # 安全地获取值，处理 None 情况
                cited_by = paper.get("citedBy", paper.get("citations"))
                if cited_by is None:
                    cited_by = 0
                year = paper.get("year")
                if year is None:
                    year = 0
                title = paper.get("title", "")
                abstract = paper.get("abstract", paper.get("snippet", ""))
                publication_info = paper.get("publicationInfo", "")
                
                # 引用数筛选 - 如果论文没有引用数，且设置了最小引用数，则跳过
                if min_citations > 0 and cited_by < min_citations:
                    continue
                if max_citations > 0 and cited_by > max_citations:
                    continue
                
                # 年份筛选 - 如果论文没有年份，且设置了年份范围，则跳过
                if year_from > 0 and year < year_from:
                    continue
                if year_to > 0 and year > year_to:
                    continue
                
                # 关键词筛选
                if title_contains and title_contains.lower() not in str(title).lower():
                    continue
                if abstract_contains and abstract_contains.lower() not in str(abstract).lower():
                    continue
                if publication_contains and publication_contains.lower() not in str(publication_info).lower():
                    continue
                
                filtered_papers.append(paper)
            
            # 排序 - 安全处理 None 值
            sorted_papers = filtered_papers.copy()
            reverse = sort_order == "desc"
            
            def get_citations_safe(x):
                val = x.get("citedBy", x.get("citations"))
                return val if val is not None else 0
            
            def get_year_safe(x):
                val = x.get("year")
                return val if val is not None else 0
            
            def get_title_safe(x):
                return str(x.get("title", "")).lower()
            
            if sort_by == "citations":
                sorted_papers.sort(key=get_citations_safe, reverse=reverse)
            elif sort_by == "year":
                sorted_papers.sort(key=get_year_safe, reverse=reverse)
            elif sort_by == "title":
                sorted_papers.sort(key=get_title_safe, reverse=reverse)
            
            # 生成筛选条件描述
            filter_desc = []
            if min_citations > 0:
                filter_desc.append(f"引用≥{min_citations}")
            if max_citations > 0:
                filter_desc.append(f"引用≤{max_citations}")
            if year_from > 0:
                filter_desc.append(f"年份≥{year_from}")
            if year_to > 0:
                filter_desc.append(f"年份≤{year_to}")
            if title_contains:
                filter_desc.append(f"标题含'{title_contains}'")
            if abstract_contains:
                filter_desc.append(f"摘要含'{abstract_contains}'")
            if publication_contains:
                filter_desc.append(f"出版含'{publication_contains}'")
            
            filter_info = " | ".join(filter_desc) if filter_desc else "无额外筛选"
            sort_info = f"{sort_by} {sort_order}"
            
            return {
                "success": True,
                "papers": sorted_papers,
                "sort_by": sort_by,
                "sort_order": sort_order,
                "filter_info": filter_info,
                "total_count": len(sorted_papers),
                "knowledge_level": knowledge_level,
                "user_profile_used": user_profile is not None,
                "message": f"筛选完成，共 {len(sorted_papers)} 篇论文 | 排序: {sort_info} | 筛选: {filter_info}"
            }
        except Exception as e:
            logger.error(f"FilterTool 执行失败: {e}", exc_info=True)
            return {
                "success": False,
                "error": f"筛选失败: {str(e)}"
            }
