#!/usr/bin/env python3
"""
简化版文献库初始化脚本
"""

import os
import json
from datetime import datetime

# 文献列表
literature_list = [
    # 核心研究
    {
        "pmid": "20333793",
        "title": "Glycemic index and glycemic load of selected Chinese traditional foods",
        "authors": "Chen YJ, Sun FH, Wong SH, Huang YJ",
        "year": 2010,
        "journal": "World J Gastroenterol",
        "category": "core",
        "abstract": "研究了23种香港传统中国食物的GI和GL值，分为低、中、高GI三类。"
    },
    {
        "pmid": "20954285",
        "title": "Glycemic index, glycemic load and insulinemic index of Chinese starchy foods",
        "authors": "Lin MH, Wu MC, Lu S, Lin J",
        "year": 2010,
        "journal": "World J Gastroenterol",
        "category": "core",
        "abstract": "测定5种中国常见淀粉类食物的GI、GL和胰岛素指数：糙米(GI 82)、芋头(GI 69)、薏米(GI 55)、山药(GI 52)、绿豆粉丝(GI 28)。"
    },
    {
        "pmid": "16733864",
        "title": "Glycemic index of cereals and tubers produced in China",
        "authors": "Yang YX, Wang HW, Cui HM, Wang Y, Yu LD, Xiang SX, Zhou SY",
        "year": 2006,
        "journal": "World J Gastroenterol",
        "category": "core",
        "abstract": "测定中国产谷物和块茎的GI值，建立中国食物GI数据库。"
    },
    {
        "pmid": "15565080",
        "title": "Postprandial glucose response to Chinese foods in patients with type 2 diabetes",
        "authors": "Chan EM, Cheng WM, Tiu SC, Wong LL",
        "year": 2004,
        "journal": "J Am Diet Assoc",
        "category": "core",
        "abstract": "研究2型糖尿病患者对中国食物的血糖反应，发现粥比米饭和面条产生更高的血糖反应。"
    },
    # 特定食物研究
    {
        "pmid": "37105123",
        "title": "The structure-glycemic index relationship of Chinese yam (Dioscorea opposita Thunb.) starch",
        "authors": "Zou J, Feng Y, Xu M, Yang P, Zhao X, Yang B",
        "year": 2023,
        "journal": "Food Chem",
        "category": "specific_food",
        "abstract": "研究山药淀粉的低GI特性及其结构关系，中国山药淀粉显示最低的GI值。"
    },
    {
        "pmid": "35574202",
        "title": "Effects of high-amylose maize starch on the glycemic index of Chinese steamed buns (CSB)",
        "authors": "Haini N, Jau-Shya L, Mohd Rosli RG, Mamat H",
        "year": 2022,
        "journal": "Heliyon",
        "category": "specific_food",
        "abstract": "研究高直链玉米淀粉对馒头GI值的影响，添加抗性淀粉可降低GI值。"
    },
    {
        "pmid": "35751217",
        "title": "Main factors affecting the starch digestibility in Chinese steamed bread",
        "authors": "Shao S, Yi X, Li C",
        "year": 2022,
        "journal": "Food Chem",
        "category": "specific_food",
        "abstract": "综述影响馒头淀粉消化率的主要因素，馒头具有高GI值但可通过改进配方降低。"
    },
    # 方法学研究
    {
        "pmid": "20151769",
        "title": "Evaluation of a glucose meter in determining the glycemic index of Chinese traditional foods",
        "authors": "Sun F, Wong SH, Chen Y, Huang Y",
        "year": 2010,
        "journal": "Diabetes Technol Ther",
        "category": "methodology",
        "abstract": "评估血糖仪在测定中国传统食物GI值中的应用，血糖仪可用于GI值测定。"
    },
    # 流行病学研究
    {
        "pmid": "18039989",
        "title": "Prospective study of dietary carbohydrates, glycemic index, glycemic load, and incidence of type 2 diabetes mellitus in middle-aged Chinese women",
        "authors": "Villegas R, Liu S, Gao YT, Yang G, Li H, Zheng W, Shu XO",
        "year": 2007,
        "journal": "Arch Intern Med",
        "category": "epidemiology",
        "abstract": "中国中年女性膳食碳水化合物、GI、GL与2型糖尿病发病率的前瞻性研究。"
    },
    {
        "pmid": "28341844",
        "title": "Relevance of the dietary glycemic index, glycemic load and genetic predisposition for the glucose homeostasis of Chinese adults without diabetes",
        "authors": "Cheng G, Xue H, Luo J, Jia H, Zhang L, Dai J, Buyken AE",
        "year": 2017,
        "journal": "Sci Rep",
        "category": "epidemiology",
        "abstract": "研究膳食GI、GL和遗传易感性对中国非糖尿病人群葡萄糖稳态的影响。"
    },
    {
        "pmid": "27733400",
        "title": "Dietary glycemic index, glycemic load, and refined carbohydrates are associated with risk of stroke: a prospective cohort study in urban Chinese women",
        "authors": "Yu D, Zhang X, Shu XO, Cai H, Li H, Ding D, Hong Z, Xiang YB, Gao YT, Zheng W, Yang G",
        "year": 2016,
        "journal": "Am J Clin Nutr",
        "category": "epidemiology",
        "abstract": "研究膳食GI、GL和精制碳水化合物与中国城市女性卒中风险的关系。"
    },
    # 亚洲食物比较研究
    {
        "pmid": "29759105",
        "title": "The glycaemic index and insulinaemic index of commercially available breakfast and snack foods in an Asian population",
        "authors": "Tan WSK, Tan WJK, Ponnalagu SD, Koecher K, Menon R, Tan SY, Henry CJ",
        "year": 2018,
        "journal": "Br J Nutr",
        "category": "asian_comparison",
        "abstract": "研究亚洲人群早餐和零食食物的GI和胰岛素指数，亚洲早餐食物多为中高GI。"
    },
    {
        "pmid": "25716365",
        "title": "Glycaemic index and glycaemic load of selected popular foods consumed in Southeast Asia",
        "authors": "Sun L, Lee DE, Tan WJ, Ranawana DV, Quek YC, Goh HJ, Henry CJ",
        "year": 2015,
        "journal": "Br J Nutr",
        "category": "asian_comparison",
        "abstract": "研究东南亚流行食物的GI和GL值，15种食物中6种为低GI食物。"
    },
    # 临床干预研究
    {
        "pmid": "32327444",
        "title": "High or low glycemic index (GI) meals at dinner results in greater postprandial glycemia compared with breakfast: a randomized controlled trial",
        "authors": "Haldar S, Egli L, De Castro CA, Tay SL, Koh MXN, Darimont C, Mace K, Henry CJ",
        "year": 2020,
        "journal": "BMJ Open Diabetes Res Care",
        "category": "clinical_trial",
        "abstract": "研究晚餐高/低GI餐比早餐产生更大餐后血糖的随机对照试验。"
    },
    {
        "pmid": "26742058",
        "title": "Effect of Glycemic Index of Breakfast on Energy Intake at Subsequent Meal among Healthy People: A Meta-Analysis",
        "authors": "Sun FH, Li C, Zhang YJ, Wong SH, Wang L",
        "year": 2016,
        "journal": "Nutrients",
        "category": "clinical_trial",
        "abstract": "早餐GI对健康人群后续能量摄入影响的Meta分析，低GI早餐可减少后续食物摄入。"
    },
    # 其他重要研究
    {
        "pmid": "20962156",
        "title": "Dietary glycemic load and risk of colorectal cancer in Chinese women",
        "authors": "Li HL, Yang G, Shu XO, Xiang YB, Chow WH, Ji BT, Zhang X, Cai H, Gao J, Gao YT, Zheng W",
        "year": 2011,
        "journal": "Am J Clin Nutr",
        "category": "other",
        "abstract": "研究膳食GL与中国女性结直肠癌风险的关系。"
    },
    {
        "pmid": "29204372",
        "title": "The impact of a low glycemic index (GI) breakfast and snack on daily blood glucose profiles and food intake in young Chinese adult males",
        "authors": "Kaur B, Ranawana V, Teh AL, Henry CJK",
        "year": 2015,
        "journal": "J Clin Transl Endocrinol",
        "category": "other",
        "abstract": "研究低GI早餐和零食对中国年轻男性日常血糖谱和食物摄入的影响。"
    },
    {
        "pmid": "24885045",
        "title": "The use of different reference foods in determining the glycemic index of starchy and non-starchy test foods",
        "authors": "Venn BJ, Kataoka M, Mann J",
        "year": 2014,
        "journal": "Nutr J",
        "category": "methodology",
        "abstract": "研究不同参考食物在测定淀粉和非淀粉食物GI值中的应用。"
    },
    {
        "pmid": "40275625",
        "title": "Effects of pre-exercise snack bars with low- and high-glycemic index on soccer-specific performance: An application of continuous glucose monitoring",
        "authors": "Zuo Y, Poon ET, Zhang X, Zhang B, Zheng C, Sun F",
        "year": 2025,
        "journal": "J Sports Sci",
        "category": "clinical_trial",
        "abstract": "研究运动前低/高GI零食对足球专项表现的影响，低GI零食导致更稳定的血糖水平。"
    }
]

def create_directories():
    """创建目录结构"""
    directories = ["pdfs", "summaries", "metadata", "index"]
    for dir_name in directories:
        os.makedirs(os.path.join("literature", dir_name), exist_ok=True)
    print("目录结构创建完成")

def save_metadata(literature):
    """保存文献元数据"""
    pmid = literature["pmid"]
    metadata_file = os.path.join("literature", "metadata", f"{pmid}.json")
    
    metadata = {
        "pmid": pmid,
        "title": literature["title"],
        "authors": literature["authors"],
        "year": literature["year"],
        "journal": literature["journal"],
        "category": literature["category"],
        "abstract": literature.get("abstract", ""),
        "added_date": datetime.now().isoformat(),
        "urls": {
            "pubmed": f"https://pubmed.ncbi.nlm.nih.gov/{pmid}/",
            "pmc": f"https://www.ncbi.nlm.nih.gov/pmc/articles/PMC{pmid}/"
        }
    }
    
    with open(metadata_file, 'w', encoding='utf-8') as f:
        json.dump(metadata, f, ensure_ascii=False, indent=2)
    
    return metadata

def create_summary(literature, metadata):
    """创建文献摘要"""
    pmid = literature["pmid"]
    summary_file = os.path.join("literature", "summaries", f"{pmid}.md")
    
    summary_content = f"""# {literature['title']}

## 基本信息
- **PMID**: {pmid}
- **作者**: {literature['authors']}
- **年份**: {literature['year']}
- **期刊**: {literature['journal']}
- **类别**: {literature['category']}
- **添加日期**: {metadata['added_date']}

## 摘要
{metadata.get('abstract', '')}

## 关键发现
<!-- 在此处添加文献的关键发现 -->

## 对2型糖尿病管理的启示
<!-- 在此处添加对糖尿病管理的具体启示 -->

## 相关链接
- [PubMed链接]({metadata['urls']['pubmed']})
- [PMC全文链接]({metadata['urls']['pmc']})

## 笔记
<!-- 在此处添加个人笔记 -->

---
*最后更新: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}*
"""
    
    with open(summary_file, 'w', encoding='utf-8') as f:
        f.write(summary_content)

def create_index():
    """创建文献索引"""
    index_data = {
        "total_count": len(literature_list),
        "categories": {},
        "by_year": {},
        "last_updated": datetime.now().isoformat()
    }
    
    # 统计分类
    for lit in literature_list:
        category = lit["category"]
        if category not in index_data["categories"]:
            index_data["categories"][category] = []
        index_data["categories"][category].append(lit["pmid"])
        
        year = lit["year"]
        if year not in index_data["by_year"]:
            index_data["by_year"][year] = []
        index_data["by_year"][year].append(lit["pmid"])
    
    # 保存索引
    index_file = os.path.join("literature", "index", "index.json")
    with open(index_file, 'w', encoding='utf-8') as f:
        json.dump(index_data, f, ensure_ascii=False, indent=2)
    
    # 创建可读索引
    readable_index = os.path.join("literature", "index", "README.md")
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

---
*自动生成于 {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}*
""")

def main():
    """主函数"""
    print("开始初始化中国食物GI值文献库...")
    print(f"共找到 {len(literature_list)} 篇文献")
    
    # 创建目录
    create_directories()
    
    # 处理每篇文献
    for i, literature in enumerate(literature_list, 1):
        print(f"\n[{i}/{len(literature_list)}] 处理文献: {literature['pmid']}")
        print(f"标题: {literature['title'][:80]}...")
        
        # 保存元数据
        metadata = save_metadata(literature)
        
        # 创建摘要
        create_summary(literature, metadata)
    
    # 创建索引
    create_index()
    
    print(f"\n文献库初始化完成！")
    print(f"文献库位置: {os.path.abspath('literature')}")
    print(f"\n文献摘要保存在: literature/summaries/")
    print(f"文献元数据保存在: literature/metadata/")
    print(f"文献索引保存在: literature/index/")

if __name__ == "__main__":
    main()