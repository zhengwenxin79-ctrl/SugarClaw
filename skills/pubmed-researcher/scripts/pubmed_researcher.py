#!/usr/bin/env python3
"""
SugarClaw PubMed Researcher — NCBI E-Utilities 检索引擎
用于糖尿病决策引擎的文献检索，输出结构化的 [标题] [核心结论摘要] [PubMed链接]。
支持 Rate Limiting 异常处理与医学严谨的空结果反馈。
"""

import argparse
import json
import sys
import time
import urllib.error
import urllib.parse
import urllib.request

BASE = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils"

# NCBI 无 API Key 限制: 3 req/s，留余量
REQUEST_INTERVAL = 0.4
_last_request_time = 0.0


def _rate_limit():
    """Enforce minimum interval between requests to respect NCBI rate limits."""
    global _last_request_time
    elapsed = time.time() - _last_request_time
    if elapsed < REQUEST_INTERVAL:
        time.sleep(REQUEST_INTERVAL - elapsed)
    _last_request_time = time.time()


def _http_get(url, timeout=20, retries=2):
    """HTTP GET with retry on 429/5xx and rate limiting."""
    for attempt in range(retries + 1):
        _rate_limit()
        try:
            req = urllib.request.Request(url, headers={
                "User-Agent": "SugarClaw-PubMed-Researcher/1.0"
            })
            with urllib.request.urlopen(req, timeout=timeout) as resp:
                return resp.read()
        except urllib.error.HTTPError as e:
            if e.code == 429 or e.code >= 500:
                wait = 2 ** attempt
                sys.stderr.write(
                    f"[WARN] HTTP {e.code}, retrying in {wait}s "
                    f"(attempt {attempt+1}/{retries+1})\n"
                )
                time.sleep(wait)
                continue
            raise
        except urllib.error.URLError as e:
            if attempt < retries:
                sys.stderr.write(
                    f"[WARN] Network error: {e.reason}, retrying...\n"
                )
                time.sleep(1)
                continue
            raise
    sys.stderr.write("[ERROR] Max retries exceeded.\n")
    sys.exit(1)


def esearch(query, max_results=5, sort="relevance", api_key=None):
    """Search PubMed, return list of PMIDs."""
    params = {
        "db": "pubmed",
        "term": query,
        "retmax": max_results,
        "retmode": "json",
        "sort": sort,
    }
    if api_key:
        params["api_key"] = api_key
    url = f"{BASE}/esearch.fcgi?{urllib.parse.urlencode(params)}"
    data = json.loads(_http_get(url))
    result = data.get("esearchresult", {})
    count = int(result.get("count", 0))
    pmids = result.get("idlist", [])
    return pmids, count


def esummary(pmids, api_key=None):
    """Fetch article summaries (title, authors, journal, date)."""
    if not pmids:
        return []
    params = {
        "db": "pubmed",
        "id": ",".join(pmids),
        "retmode": "json",
    }
    if api_key:
        params["api_key"] = api_key
    url = f"{BASE}/esummary.fcgi?{urllib.parse.urlencode(params)}"
    data = json.loads(_http_get(url))
    result = data.get("result", {})
    summaries = []
    for pmid in pmids:
        info = result.get(pmid, {})
        authors_list = info.get("authors", [])
        if len(authors_list) > 3:
            authors_str = ", ".join(
                a.get("name", "") for a in authors_list[:3]
            ) + " et al."
        else:
            authors_str = ", ".join(
                a.get("name", "") for a in authors_list
            )
        summaries.append({
            "pmid": pmid,
            "title": info.get("title", "N/A"),
            "authors": authors_str,
            "journal": info.get("fulljournalname", info.get("source", "")),
            "pubdate": info.get("pubdate", ""),
            "url": f"https://pubmed.ncbi.nlm.nih.gov/{pmid}/",
        })
    return summaries


def efetch_abstracts(pmids, api_key=None):
    """Fetch full abstracts as plain text."""
    if not pmids:
        return ""
    params = {
        "db": "pubmed",
        "id": ",".join(pmids),
        "rettype": "abstract",
        "retmode": "text",
    }
    if api_key:
        params["api_key"] = api_key
    url = f"{BASE}/efetch.fcgi?{urllib.parse.urlencode(params)}"
    return _http_get(url, timeout=30).decode("utf-8", errors="replace")


def format_no_results(query):
    """医学严谨的无结果反馈。"""
    return (
        f"[PubMed Researcher] 未检索到与 \"{query}\" 相关的文献。\n\n"
        "可能原因：\n"
        "  1. 检索词过于具体或拼写有误，建议使用 MeSH 标准术语重新检索。\n"
        "  2. 该领域尚无已发表的同行评审文献。\n"
        "  3. 相关研究可能使用不同术语发表，建议扩大关键词范围。\n\n"
        "建议操作：\n"
        "  - 尝试使用英文 MeSH 术语（如 \"Blood Glucose\" 替代 \"血糖\"）\n"
        "  - 使用布尔运算组合多个关键词（如 term1 AND term2）\n"
        "  - 放宽时间范围或去除出版类型限制\n\n"
        "声明：检索结果不构成临床诊断或治疗建议，仅供科研与数据参考。"
    )


def format_results(summaries, abstracts_text=None):
    """格式化输出: [标题] [核心结论摘要] [PubMed链接]"""
    lines = []
    lines.append(f"[PubMed Researcher] 检索到 {len(summaries)} 篇相关文献：\n")

    for i, s in enumerate(summaries, 1):
        lines.append(f"{'─' * 60}")
        lines.append(f"[{i}] 标题: {s['title']}")
        lines.append(f"    作者: {s['authors']}")
        lines.append(f"    期刊: {s['journal']} ({s['pubdate']})")
        lines.append(f"    链接: {s['url']}")

    lines.append(f"{'─' * 60}")

    if abstracts_text:
        lines.append("\n[摘要详情]")
        lines.append(abstracts_text)

    lines.append(
        "\n声明：以上文献检索结果仅供科研与数据参考，不构成临床诊断或治疗建议。"
        "涉及药物或治疗方案调整，请咨询主治医师。"
    )
    return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser(
        description="SugarClaw PubMed Researcher — 糖尿病文献智能检索"
    )
    parser.add_argument("query", help="检索关键词（支持 PubMed 语法）")
    parser.add_argument(
        "--max", type=int, default=5, help="最大返回条数 (默认 5)"
    )
    parser.add_argument(
        "--sort", default="relevance",
        choices=["relevance", "date"],
        help="排序方式: relevance(相关性) 或 date(时间)"
    )
    parser.add_argument(
        "--abstract", action="store_true",
        help="同时获取完整摘要"
    )
    parser.add_argument(
        "--json", action="store_true", dest="json_out",
        help="以 JSON 格式输出"
    )
    parser.add_argument(
        "--api-key", default=None,
        help="NCBI API Key（可选，提升频率限制至 10 req/s）"
    )
    # 预设的 SugarClaw 检索模板
    parser.add_argument(
        "--mode", default=None,
        choices=["food-impact", "therapy", "cgm", "mental"],
        help="SugarClaw 预设模式: food-impact(食物血糖影响), "
             "therapy(最新疗法), cgm(CGM研究), mental(心理干预)"
    )
    args = parser.parse_args()

    query = args.query

    # 预设模式：自动扩展查询词
    mode_templates = {
        "food-impact": (
            '("{q}"[tiab] AND ("glycemic index"[mh] OR "blood glucose"[mh] '
            'OR "postprandial"[tiab]) AND "diabetes"[mh])'
        ),
        "therapy": (
            '("{q}"[tiab] AND "diabetes mellitus"[mh] AND '
            '("therapy"[sh] OR "treatment"[tiab]) '
            'AND ("Clinical Trial"[pt] OR "Review"[pt] OR "Meta-Analysis"[pt]))'
        ),
        "cgm": (
            '("{q}"[tiab] AND ("continuous glucose monitoring"[tiab] OR '
            '"CGM"[tiab]) AND "diabetes"[mh])'
        ),
        "mental": (
            '("{q}"[tiab] AND ("diabetes distress"[tiab] OR '
            '"adherence"[tiab] OR "self-management"[tiab] OR '
            '"psychological"[tiab]) AND "diabetes"[mh])'
        ),
    }

    if args.mode and args.mode in mode_templates:
        query = mode_templates[args.mode].format(q=query)

    try:
        pmids, total_count = esearch(query, args.max, args.sort, args.api_key)
    except Exception as e:
        sys.stderr.write(f"[ERROR] 检索失败: {e}\n")
        sys.exit(1)

    if not pmids:
        print(format_no_results(args.query))
        sys.exit(0)

    try:
        summaries = esummary(pmids, args.api_key)
    except Exception as e:
        sys.stderr.write(f"[ERROR] 获取文献摘要失败: {e}\n")
        sys.exit(1)

    abstracts_text = None
    if args.abstract:
        try:
            abstracts_text = efetch_abstracts(pmids, args.api_key)
        except Exception as e:
            sys.stderr.write(f"[WARN] 获取完整摘要失败: {e}\n")

    if args.json_out:
        output = {
            "query": args.query,
            "mode": args.mode,
            "total_count": total_count,
            "results": summaries,
        }
        if abstracts_text:
            output["abstracts_raw"] = abstracts_text
        print(json.dumps(output, indent=2, ensure_ascii=False))
    else:
        print(format_results(summaries, abstracts_text))


if __name__ == "__main__":
    main()
