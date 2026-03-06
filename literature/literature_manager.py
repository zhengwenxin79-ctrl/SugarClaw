#!/usr/bin/env python3
"""
中国食物GI值文献库管理系统
"""

import os
import json
import requests
import time
from datetime import datetime
import re
import sys

class LiteratureManager:
    def __init__(self, base_dir="literature"):
        self.base_dir = base_dir
        self.pdf_dir = os.path.join(base_dir, "pdfs")
        self.summary_dir = os.path.join(base_dir, "summaries")
        self.metadata_dir = os.path.join(base_dir, "metadata")
        self.index_dir = os.path.join(base_dir, "index")
        
        # 确保目录存在
        for dir_path in [self.pdf_dir, self.summary_dir, self.metadata_dir, self.index_dir]:
            os.makedirs(dir_path, exist_ok=True)
        
        # 文献列表
        self.literature_list = [
            # 核心研究
            {
                "pmid": "20333793",
                "title": "Glycemic index and glycemic load of selected Chinese traditional foods",
                "authors": "Chen YJ, Sun FH, Wong SH, Huang YJ",
                "year": 2010,
                "journal": "World J Gastroenterol",
                "category": "core"
            },
            {
                "pmid": "20954285",
                "title": "Glycemic index, glycemic load and insulinemic index of Chinese starchy foods",
                "authors": "Lin MH, Wu MC, Lu S, Lin J",
                "year": 2010,
                "journal": "World J Gastroenterol",
                "category": "core"
            },
            {
                "pmid": "16733864",
                "title": "Glycemic index of cereals and tubers produced in China",
                "authors": "Yang YX, Wang HW, Cui HM, Wang Y, Yu LD, Xiang SX, Zhou SY",
                "year": 2006,
                "journal": "World J Gastroenterol",
                "category": "core"
            },
            {
                "pmid": "15565080",
                "title": "Postprandial glucose response to Chinese foods in patients with type 2 diabetes",
                "authors": "Chan EM, Cheng WM, Tiu SC, Wong LL",
                "year": 2004,
                "journal": "J Am Diet Assoc",
                "category": "core"
            },
            # 特定食物研究
            {
                "pmid": "37105123",
                "title": "The structure-glycemic index relationship of Chinese yam (Dioscorea opposita Thunb.) starch",
                "authors": "Zou J, Feng Y, Xu M, Yang P, Zhao X, Yang B",
                "year": 2023,
                "journal": "Food Chem",
                "category": "specific_food"
            },
            {
                "pmid": "35574202",
                "title": "Effects of high-amylose maize starch on the glycemic index of Chinese steamed buns (CSB)",
                "authors": "Haini N, Jau-Shya L, Mohd Rosli RG, Mamat H",
                "year": 2022,
                "journal": "Heliyon",
                "category": "specific_food"
            },
            {
                "pmid": "35751217",
                "title": "Main factors affecting the starch digestibility in Chinese steamed bread",
                "authors": "Shao S, Yi X, Li C",
                "year": 2022,
                "journal": "Food Chem",
                "category": "specific_food"
            },
            # 方法学研究
            {
                "pmid": "20151769",
                "title": "Evaluation of a glucose meter in determining the glycemic index of Chinese traditional foods",
                "authors": "Sun F, Wong SH, Chen Y, Huang Y",
                "year": 2010,
                "journal": "Diabetes Technol Ther",
                "category": "methodology"
            },
            {
                "pmid": "19548585",
                "title": "[In vitro regression model of glycemic index for carbohydrate-riched foods]",
                "authors": "Li J, Wang Z, Yang X, Liu J",
                "year": 2009,
                "journal": "Wei Sheng Yan Jiu",
                "category": "methodology"
            },
            # 流行病学研究
            {
                "pmid": "18039989",
                "title": "Prospective study of dietary carbohydrates, glycemic index, glycemic load, and incidence of type 2 diabetes mellitus in middle-aged Chinese women",
                "authors": "Villegas R, Liu S, Gao YT, Yang G, Li H, Zheng W, Shu XO",
                "year": 2007,
                "journal": "Arch Intern Med",
                "category": "epidemiology"
            },
            {
                "pmid": "28341844",
                "title": "Relevance of the dietary glycemic index, glycemic load and genetic predisposition for the glucose homeostasis of Chinese adults without diabetes",
                "authors": "Cheng G, Xue H, Luo J, Jia H, Zhang L, Dai J, Buyken AE",
                "year": 2017,
                "journal": "Sci Rep",
                "category": "epidemiology"
            },
            {
                "pmid": "27733400",
                "title": "Dietary glycemic index, glycemic load, and refined carbohydrates are associated with risk of stroke: a prospective cohort study in urban Chinese women",
                "authors": "Yu D, Zhang X, Shu XO, Cai H, Li H, Ding D, Hong Z, Xiang YB, Gao YT, Zheng W, Yang G",
                "year": 2016,
                "journal": "Am J Clin Nutr",
                "category": "epidemiology"
            },
            # 亚洲食物比较研究
            {
                "pmid": "29759105",
                "title": "The glycaemic index and insulinaemic index of commercially available breakfast and snack foods in an Asian population",
                "authors": "Tan WSK, Tan WJK, Ponnalagu SD, Koecher K, Menon R, Tan SY, Henry CJ",
                "year": 2018,
                "journal": "Br J Nutr",
                "category": "asian_comparison"
            },
            {
                "pmid": "25716365",
                "title": "Glycaemic index and glycaemic load of selected popular foods consumed in Southeast Asia",
                "authors": "Sun L, Lee DE, Tan WJ, Ranawana DV, Quek YC, Goh HJ, Henry CJ",
                "year": 2015,
                "journal": "Br J Nutr",
                "category": "asian_comparison"
            },
            # 临床干预研究
            {
                "pmid": "32327444",
                "title": "High or low glycemic index (GI) meals at dinner results in greater postprandial glycemia compared with breakfast: a randomized controlled trial",
                "authors": "Haldar S, Egli L, De Castro CA, Tay SL, Koh MXN, Darimont C, Mace K, Henry CJ",
                "year": 2020,
                "journal": "BMJ Open Diabetes Res Care",
                "category": "clinical_trial"
            },
            {
                "pmid": "26742058",
                "title": "Effect of Glycemic Index of Breakfast on Energy Intake at Subsequent Meal among Healthy People: A Meta-Analysis",
                "authors": "Sun FH, Li C, Zhang YJ, Wong SH, Wang L",
                "year": 2016,
                "journal": "Nutrients",
                "category": "clinical_trial"
            },
            # 其他重要研究
            {
                "pmid": "20962156",
                "title": "Dietary glycemic load and risk of colorectal cancer in Chinese women",
                "authors": "Li HL, Yang G, Shu XO, Xiang YB, Chow WH, Ji BT, Zhang X, Cai H, Gao J, Gao YT, Zheng W",
                "year": 2011,
                "journal": "Am J Clin Nutr",
                "category": "other"
            },
            {
                "pmid": "29204372",
                "title": "The impact of a low glycemic index (GI) breakfast and snack on daily blood glucose profiles and food intake in young Chinese adult males",
                "authors": "Kaur B, Ranawana V, Teh AL, Henry CJK",
                "year": 2015,
                "journal": "J Clin Transl Endocrinol",
                "category": "other"
            },
            {
                "pmid": "24885045",
                "title": "The use of different reference foods in determining the glycemic index of starchy and non-starchy test foods",
                "authors": "Venn BJ, Kataoka M, Mann J",
                "year": 2014,
                "journal": "Nutr J",
                "category": "methodology"
            },
            {
                "pmid": "40275625",
                "title": "Effects of pre-exercise snack bars with low- and high-glycemic index on soccer-specific performance: An application of continuous glucose monitoring",
                "authors": "Zuo Y, Poon ET, Zhang X, Zhang B, Zheng C, Sun F",
                "year": 2025,
                "journal": "J Sports Sci",
                "category": "clinical_trial"
            }
        ]
    
    def fetch_pubmed_abstract(self, pmid):
        """从PubMed获取摘要"""
        url = f"https://eutils.ncbi.nlm.nih.gov/entrez/eutils/efetch.fcgi"
        params = {
            "db": "pubmed",
            "id": pmid,
            "retmode": "xml",
            "rettype": "abstract"
        }
        
        try:
            response = requests.get(url, params=params, timeout=10)
            if response.status_code == 200:
                return response.text
            else:
                print(f"获取PMID {pmid}失败: HTTP {response.status_code}")
                return None
        except Exception as e:
            print(f"获取PMID {pmid}时出错: {e}")
            return None
    
    def extract_abstract_from_xml(self, xml_content):
        """从XML中提取摘要"""
        # 简化提取逻辑
        if not xml_content:
            return None
        
        # 查找摘要部分
        abstract_pattern = r'<AbstractText[^>]*>([^<]+)</AbstractText>'
        matches = re.findall(abstract_pattern, xml_content, re.IGNORECASE)
        
        if matches:
            return " ".join(matches)
        
        # 尝试其他模式
        abstract_pattern2 = r'<Abstract>.*?<AbstractText[^>]*>([^<]+)</AbstractText>.*?</Abstract>'
        match = re.search(abstract_pattern2, xml_content, re.DOTALL | re.IGNORECASE)
        if match:
            return match.group(1)
        
        return None
    
    def save_literature_metadata(self, literature):
        """保存文献元数据"""
        pmid = literature["pmid"]
        metadata_file = os.path.join(self.metadata_dir, f"{pmid}.json")
        
        # 获取摘要
        xml_content = self.fetch_pubmed_abstract(pmid)
        abstract = self.extract_abstract_from_xml(xml_content) if xml_content else None
        
        metadata = {
            "pmid": pmid,
            "title": literature["title"],
            "authors": literature["authors"],
            "year": literature["year"],
            "journal": literature["journal"],
            "category": literature["category"],
            "abstract": abstract,
            "added_date": datetime.now().isoformat(),
            "urls": {
                "pubmed": f"https://pubmed.ncbi.nlm.nih.gov/{pmid}/",
                "pmc": f"https://www.ncbi.nlm.nih.gov/pmc/articles/PMC{pmid}/" if literature.get("pmc_id") else None
            }
        }
        
        with open(metadata_file, 'w', encoding='utf-8') as f:
            json.dump(metadata, f, ensure_ascii=False, indent=2)
        
        print(f"已保存文献元数据: {pmid}")
        return metadata
    
    def create_summary_file(self, literature, metadata):
        """创建文献摘要文件"""
        pmid = literature["pmid"]
        summary_file = os.path.join(self.summary_dir, f"{pmid}.md")
        
        summary_content = f"""# {literature['title']}

## 基本信息
- **PMID**: {pmid}
- **作者**: {literature['authors']}
- **年份**: {literature['year']}
- **期刊**: {literature['journal']}
- **类别**: {literature['category']}
- **添加日期**: {metadata['added_date']}

## 摘要
{metadata.get('abstract', '摘要未获取到')}

## 关键发现
<!-- 在此处添加文献的关键发现 -->

## 对2型糖尿病管理的启示
<!-- 在此处添加对糖尿病管理的具体启示 -->

## 相关链接
- [PubMed链接]({metadata['urls']['pubmed']})
{f"- [PMC全文链接]({metadata['urls']['pmc']})" if metadata['urls']['pmc'] else ""}

## 笔记
<!-- 在此处添加个人笔记 -->

---
*最后更新: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}*
"""
        
        with open(summary_file, 'w', encoding='utf-8') as f:
            f.write(summary_content)
        
        print(f"已创建摘要文件: {pmid}.md")
    
    def create_index(self):
        """创建文献索引"""
        index_data = {
            "total_count": len(self.literature_list),
            "categories": {},
            "by_year": {},
            "last_updated": datetime.now().isoformat()
        }
        
        # 按类别统计
        for lit in self.literature_list:
            category = lit["category"]
            if category not in index_data["categories"]:
                index_data["categories"][category] = []
            index_data["categories"][category].append(lit["pmid"])
            
            # 按年份统计
            year = lit["year"]
            if year not in index_data["by_year"]:
                index_data["by_year"][year] = []
            index_data["by_year"][year].append(lit["pmid"])
        
        # 保存索引文件
        index_file = os.path.join(self.index_dir, "index.json")
        with open(index_file, 'w', encoding='utf-8') as f:
            json.dump(index_data, f, ensure_ascii=False, indent=2)
        
        # 创建可读的索引文件
        readable_index = os.path.join(self.index_dir, "README.md")
        with open(readable_index, 'w', encoding='utf-8') as f:
            f.write(f"""# 中国食物GI值文献库索引

## 概览
- **文献总数**: {index_data['total_count']}篇
- **最后更新**: {index_data['last_updated']}

## 按类别分类

### 核心研究 ({len(index_data['categories'].get('core', []))}篇)
{chr(10).join([f"- PMID: {pmid}" for pmid in index_data['categories'].get('core', [])])}

### 特定食物研究 ({len(index_data['categories'].get('specific_food', []))}篇)
{chr(10).join([f"- PMID: {pmid}" for pmid in index_data['categories'].get('specific_food', [])])}

### 流行病学研究 ({len(index_data['categories'].get('epidemiology', []))}篇)
{chr(10).join([f"- PMID: {pmid}" for pmid in index_data['categories'].get('epidemiology', [])])}

### 方法学研究 ({len(index_data['categories'].get('methodology', []))}篇)
{chr(10).join([f"- PMID: {pmid}" for pmid in index_data['categories'].get('methodology', [])])}

### 临床干预研究 ({len(index_data['categories'].get('clinical_trial', []))}篇)
{chr(10).join([f"- PMID: {pmid}" for pmid in index_data['categories'].get('clinical_trial', [])])}

### 亚洲食物比较研究 ({len(index_data['categories'].get('asian_comparison', []))}篇)
{chr(10).join([f"- PMID: {pmid}" for pmid in index_data['categories'].get('asian_comparison', [])])}

### 其他研究 ({len(index_data['categories'].get('other', []))}篇)
{chr(10).join([f"- PMID: {pmid}" for pmid in index_data['categories'].get('other', [])])}

## 按年份分类
{chr(10).join([f"- {year}年: {len(pmids)}篇" for year, pmids in sorted(index_data['by_year'].items())])}

## 使用说明
1. 文献元数据保存在 `metadata/` 目录
2. 文献摘要保存在 `summaries/` 目录
3. PDF文件保存在 `pdfs/` 目录（需要手动下载）
4. 使用 `literature_manager.py` 管理文献库

---
*自动生成于 {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}*
""")
        
        print("已创建文献索引")
    
    def initialize_library(self):
        """初始化文献库"""
        print("开始初始化中国食物GI值文献库...")
        print(f"共找到 {len(self.literature_list)} 篇文献")
        
        for i, literature in enumerate(self.literature_list, 1):
            print(f"\n[{i}/{len(self.literature_list)}] 处理文献: {literature['pmid']}")
            print(f"标题: {literature['title']}")
            
            # 保存元数据
            metadata = self.save_literature_metadata(literature)
            
            # 创建摘要文件
            if metadata:
                self.create_summary_file(literature, metadata)
            
            # 避免请求过快
            time.sleep(0.5)
        
        # 创建索引
        self.create_index()
        
        print(f"\n文献库初始化完成！")
        print(f"文献库位置: {os.path.abspath(self.base_dir)}")