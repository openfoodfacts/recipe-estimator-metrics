---
title: 'PEFAP : Estimating the environmental footprint of food products from packaging data'
tags:
  - Python
  - Open Food Facts
  - Food
  - Environment
  - Life Cycle Assessment
  - Ecolabelling
authors:
  - name: Gustave Coste
    orcid: 0000-0001-5867-0507
    affiliation: "1, 2, 3"
  - name: Arnaud Hélias
    orcid: 0000-0002-8652-5611
    affiliation: "2, 3"
affiliations:
 - name: INRAE, Univ Montpellier, LBE, 102 avenue des Etangs, 11100, Narbonne, France
   index: 1
 - name: ITAP, Univ Montpellier, INRAE, Institut Agro, Montpellier, France
   index: 2
 - name: ELSA, Research group for environmental life cycle sustainability assessment, Montpellier, France
   index: 3
date: 11 May 2021
bibliography: paper.bib
---

# Summary

Food consumption represents an important part of our ecological footprint [@JRC.2019], therefore changes in food consumption habits can greatly help to mitigate it. In order to help consumers to make more informed food consumption choices, several ecolabelling initiatives have been developed recently by institutional and private actors [@agribalyse-ecolabelling]. Most of these initiatives use a single environmental impact value for a given product type. This default value is constructed from a recipe (i.e. proportion of ingredients), a processing chain, and a supply chain that is considered an "average" scenario.This approach appears to be frugal in terms of data, but it is obviously limited. It does not allow for differentiation of products within a category. PEFAP (Product Environmental Footprint According to Packaging data) aims to fill this gap.It estimates the most likely impact for each product individually, based on the information on the packaging (ordered list of ingredients and nutritional composition) and the environmental impacts of the agricultural production of the ingredients. To the best of our knowledge, there is no such software available, whether open source or not. The users of this software are multiple: it allows researchers to assign environmental impacts to commercially available food products in environmental studies, but also as additional criteria in economic or nutritional studies. It allows actors in the food industry to automate and reduce the cost of calculating the impact of their products. It also offers the opportunity to third parties, such as independent organisations and consumer applications, to display an estimate of the environmental footprint of their products.


# Statement of need

Product environmental footprint is an eternal compromise: The assessment has to be specific, to best represent production and processing choices in the value chain. Unfortunately, this need for specific data quickly becomes an obstacle and makes the work too big to do on a large scale. In contrast, generic data offer a less expensive result, but these default values only allow for inter-category comparisons, so differentiating products within a category is impossible. This balance between specificity and simplicity needs to be overcome. 
The proportions of ingredients in food products are a determining factor for the environmental footprint and reveal intra-category discrepancies. The answer would be to adapt the results to industrial recipes, directly by the food industry. However, access to information and the costs of this approach make this difficult. A cost-effective solution is therefore necessary, for estimating the impact from free-access data, which is available on the package.
Based on the partial list of ingredients (an ordered list, but with often unknown proportions) and nutritional data available on packaging, the algorithm explores the range of possible recipes through a Monte Carlo approach. In each iteration, the masses of ingredients are randomly chosen according to the possible proportions of ingredients and ensuring the best possible preservation of nutrient contents (the nutrients of the product being considered as the sum of the nutrients of all its ingredients). PEFAP retrieves for each ingredient, the environmental impacts and the nutrient data. It finds the most likely footprint by the convergence of the result over Monte Carlo runs.
This offers a compromise between a "generic" assessment, which is not very accurate but already available, and a "specific" one, which is effective but expensive and impossible to perform by a third party. 

# Functionality

The algorithm used by this program is based on a Monte-Carlo approach to estimate the impact of a product. Its principle is to pick random possible recipes of the product with proportions that are consistent with the partial information in the ingredient list and whose combination corresponds to the displayed nutritional data (without deviating too substantially). The convergence is achieved by the stabilization of the geometric mean of the runs within a given confidence interval. The sampling of possible recipes is made as accurate as possible by using a nonlinear optimization solver [@scip], and Optimization-Based Bound Tightening to deduce the ranges of possible values of the mass of each ingredient respecting the nutritional constraints of the system. A more extensive explanation of the principles used is available in the documentation.

This program features a class based implementation of the impact estimation algorithm that can be integrated in Python projects. It also integrates a reporting tool to create HTML and PDF impact estimation reports of a product. To be functional, this program has been interfaced to the Open Food Facts database [@openfoodfacts] providing packaging information. It uses data from the Ciqual [@ciqual] and FCEN [@fcen] nutritional databases, and the Agribalyse [@agribalyse] environmental impact database. All these data are freely available and fit to a French context, but it could be easily adapted to other data sources.

# Example

The code sample below shows a simple example of getting a product from the Open Food Facts database, computing its Environmental Footprint and climate change impacts, and finally creating a HTML report of the result.

```python
from impacts_estimation import estimate_impacts
from openfoodfacts import get_product
from reporting import ProductImpactReport

product = get_product(barcode='3175681790285')['product']

impact_categories = ['EF single score',
                     'Climate change']
impact_estimation_result = estimate_impacts(product=product,
                                            impact_names=impact_categories)

for impact_category in impact_categories:
    print(f"{impact_category}: "
          f"{impact_estimation_result['impacts_geom_means'][impact_category]:.4} "
          f"{impact_estimation_result['impacts_units'][impact_category]}")
# EF single score: 0.03832 mPt
# Climate change: 0.3819 kg CO2 eq


# Generating an impact estimation report
reporter = ProductImpactReport(product=product)

reporter.to_html()
```

# Acknowledgements

This project has been funded by the European Union and the Occitanie (FR) region (operational program FEDER-FSE 2014-2020 - GEPETOs – 2015) and INRAE.

We acknowledge the Open Food Facts contributors for creating the database this tool relies on.

# References
