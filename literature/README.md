# 中国食物GI值文献库

## 概述
本文献库收集了20篇关于中国食物血糖生成指数(GI值)的重要研究文献，专门为2型糖尿病患者的饮食管理提供科学依据。

## 文献来源
所有文献均来自PubMed数据库，涵盖以下领域：
- 中国传统食物的GI值测定
- 中国淀粉类食物的血糖反应
- 2型糖尿病患者对中国食物的血糖反应
- 食物加工对GI值的影响
- 流行病学研究

## 文献列表

### 核心研究 (4篇)
1. **PMID 20333793** - Glycemic index and glycemic load of selected Chinese traditional foods
2. **PMID 20954285** - Glycemic index, glycemic load and insulinemic index of Chinese starchy foods
3. **PMID 16733864** - Glycemic index of cereals and tubers produced in China
4. **PMID 15565080** - Postprandial glucose response to Chinese foods in patients with type 2 diabetes

### 特定食物研究 (3篇)
5. **PMID 37105123** - The structure-glycemic index relationship of Chinese yam starch
6. **PMID 35574202** - Effects of high-amylose maize starch on the glycemic index of Chinese steamed buns
7. **PMID 35751217** - Main factors affecting the starch digestibility in Chinese steamed bread

### 流行病学研究 (3篇)
8. **PMID 18039989** - Prospective study of dietary carbohydrates, glycemic index, glycemic load, and incidence of type 2 diabetes in middle-aged Chinese women
9. **PMID 28341844** - Relevance of the dietary glycemic index, glycemic load and genetic predisposition for the glucose homeostasis of Chinese adults without diabetes
10. **PMID 27733400** - Dietary glycemic index, glycemic load, and refined carbohydrates are associated with risk of stroke in urban Chinese women

### 方法学研究 (3篇)
11. **PMID 20151769** - Evaluation of a glucose meter in determining the glycemic index of Chinese traditional foods
12. **PMID 19548585** - In vitro regression model of glycemic index for carbohydrate-riched foods
13. **PMID 24885045** - The use of different reference foods in determining the glycemic index of starchy and non-starchy test foods

### 临床干预研究 (3篇)
14. **PMID 32327444** - High or low glycemic index meals at dinner results in greater postprandial glycemia compared with breakfast
15. **PMID 26742058** - Effect of Glycemic Index of Breakfast on Energy Intake at Subsequent Meal among Healthy People
16. **PMID 40275625** - Effects of pre-exercise snack bars with low- and high-glycemic index on soccer-specific performance

### 亚洲食物比较研究 (2篇)
17. **PMID 29759105** - The glycaemic index and insulinaemic index of commercially available breakfast and snack foods in an Asian population
18. **PMID 25716365** - Glycaemic index and glycaemic load of selected popular foods consumed in Southeast Asia

### 其他重要研究 (2篇)
19. **PMID 20962156** - Dietary glycemic load and risk of colorectal cancer in Chinese women
20. **PMID 29204372** - The impact of a low glycemic index breakfast and snack on daily blood glucose profiles in young Chinese adult males

## 关键发现总结

### 中国食物GI值特点
1. **范围广泛**: 从低GI(28)到高GI(85)
2. **低GI食物**: 绿豆粉丝(GI 28)、山药(GI 52)、薏米(GI 55)
3. **高GI食物**: 糙米(GI 82)、糯米制品、肠粉
4. **影响因素**: 烹饪方法、食品加工、食物组合

### 对2型糖尿病管理的启示
1. **个人化反应**: 不同个体对相同食物的血糖反应差异显著
2. **食物组合**: 蛋白质、脂肪和纤维可降低整体GI
3. **时间效应**: 晚餐的GI影响可能比早餐更大
4. **监测重要性**: 建立个人食物血糖反应数据库

## 使用方法

### 1. 初始化文献库
```bash
cd literature
./manage_literature.sh
```

### 2. 查看文献摘要
所有文献摘要保存在 `summaries/` 目录，格式为Markdown，方便阅读和笔记。

### 3. 文献元数据
文献元数据保存在 `metadata/` 目录，包含作者、年份、期刊、摘要等信息。

### 4. PDF文件管理
由于版权限制，PDF文件需要手动下载到 `pdfs/` 目录。可以从以下来源获取：
- PubMed Central (PMC)
- 期刊官网
- 学术数据库

### 5. 文献索引
完整的文献索引保存在 `index/` 目录，包括按类别和年份的分类。

## 文件结构
```
literature/
├── literature_manager.py    # Python管理脚本
├── manage_literature.sh     # Shell管理脚本
├── README.md               # 本文档
├── pdfs/                   # PDF文件目录
├── summaries/              # 文献摘要目录
├── metadata/               # 文献元数据目录
└── index/                  # 索引目录
```

## 扩展建议

### 1. 添加新文献
编辑 `literature_manager.py` 中的 `literature_list`，添加新的PMID和文献信息。

### 2. 个性化笔记
在 `summaries/` 目录的文献摘要文件中添加个人笔记和关键发现。

### 3. 建立个人数据库
基于这些文献，建立个人的食物血糖反应数据库，记录：
- 食物名称和分量
- 餐后血糖变化
- 个人感受和反应

### 4. 定期更新
定期检查PubMed是否有新的相关研究，更新文献库。

## 注意事项
1. 本文献库仅供个人学习和研究使用
2. 尊重版权，合理使用文献
3. 医学建议请咨询专业医生
4. 个体差异显著，建议结合个人血糖监测

## 联系信息
如有问题或建议，请联系文献库维护者。

---
*最后更新: 2026-03-06*