Estimating product impact
=========================

The estimation the environmental impact of an Open Food Facts product can be done using the :class:`~impacts_estimation.impacts_estimation.ImpactEstimator` class or the wrapper :class:`~impacts_estimation.impacts_estimation.estimate_impacts`. The later can be used with ``safe_mode=True`` to progressively relax the constraints on the model in order to get a result in case of failure.

Central limit theorem
---------------------

This algorithm uses a Monte-Carlo based approach to estimate the expectation of a random variable by a large number of draws. It uses the `Central Limit Theorem <https://en.wikipedia.org/wiki/Central_limit_theorem>`_ which establishes the convergence in law of the mean of a sequence of random variables to a normal distribution in order to detect when the number of computed values is sufficient.

This theorem can be used to calculate the expectation of the environmental impact of a recipe obtained with :class:`~impacts_estimation.impacts_estimation.RandomRecipeCreator`. Note that the calculated impact values have a large dispersion, sometimes over several orders of magnitude. LCA results mostly follow lognormal distributions (Qin Y, Suh S (2017) *What distribution function do life cycle inventories follow?* Int J Life Cycle Assess 22:1138–1145. `doi.org/10.1007/s11367-016-1224-4 <https://doi.org/10.1007/s11367-016-1224-4>`_). To address this point, the CLT is applied by considering the logarithm of the environmental impact of a recipe as a random variable :math:`(X_n=\ln(x_i))` of expectation :math:`\mu` and variance :math:`\sigma^2`.
Thus, the arithmetic mean :math:`\overline{X}_n` of a large number of draws of this random variable converges in law to a normal distribution of the same expectation :math:`\mu` and whose standard deviation :math:`\frac{\sigma}{\sqrt{n}}` decreases as the number of draws :math:`n` increases.

Since the variance :math:`\sigma^2` of the impact of the compositions is unknown, we can use a Student's law to calculate a confidence interval of the expectation :math:`\mu`. At each run, this confidence interval is calculated (with a level of confidence specified by the ``confidence_level`` parameter which is 95% by default). When this confidence interval is narrower than the threshold defined by :math:`\mu \cdot confidence\_interval\_width` (with ``confidence_interval_width`` equal to 5% by default), we consider that the number of draws is sufficient to calculate a result. We then calculate

.. math::
   G=exp(\overline{X}_n)=\exp\left(\frac{\sum_{i=1}^{n}{\ln(x_i)}}{n}\right)

which corresponds to the geometric mean of the draws

.. note::
   In order to avoid erroneous convergence detection caused by a small number of runs, a minimum number of run is determined by the ``min_run_nb`` parameter which is equal to 30 by default.

Confidence score weighting
--------------------------

In order to give more weight to the most credible recipes in the calculation of the final result, the confidence score was used to weight the calculation of the averages. The result of the algorithm is the weighted geometric mean :math:`G'` defined by :

.. math::
    G'=\exp\left(\frac{\sum_{i=1}^{n}{w_i\cdot\ln(x_i)}}{\sum_{i=1}^{n}w_i}\right)

The advantage of this weighting is that it makes the result more credible by minimizing the weight of compositions that are too unlikely. On the other hand, the classical version of the CLT does not apply to weighted averages. Indeed, one of the conditions of applicability of the CLT is that the random variables must be independent, and we can consider a weighted average as an average for which the draws appear as many times as their weight, which makes them dependent.
However, one can intuitively think that the weighting of the draws does not prevent the convergence of the result. One could even think that it accelerates it by hypothesizing that the higher the confidence score of a recipe the closer its impact value is to the average.

Algorithm description
---------------------

The algorithm consists of a while loop that continues as long as the minimum number of loop turns is not reached or the confidence interval of the result of at least one of the impact categories is higher than the stopping threshold.
At each turn of this loop, :meth:`~impacts_estimation.impacts_estimation.RandomRecipeCreator.random_recipe` is called to obtain a possible recipe of the product and its confidence score is calculated.
We then loop over all the impact categories considered to calculate the impact of this recipe and add it to a list.
The logarithms of the impact values of the recipes calculated so far are averaged and weighted by their confidence score and this result is added to a list.
This list thus contains the weighted average of the impact logs of the first :math:`1, 2, \dots, n` first draws.
Thanks to the CLT, the values of this list of means seem to follow a normal distribution.
We can therefore estimate a confidence interval for this distribution.
If the width of this interval converted back to the linear space (by taking the exponential of the bounds) is smaller than the ``confidence_interval_width`` parameter for all impact categories, the loop ends and the weighted geometric mean of the calculated impacts for each category is returned as well as other results derived from the recipes impacts distributions.

Result warnings
---------------

During the algorithm execution, errors can occur. In theses cases an exception will be raised and the program will be terminated. In other cases, the algorithm can encounter non blocking issues. For example, if :meth:`~impacts_estimation.impacts_estimation.ImpactEstimator._check_defined_percentages` finds that the defined percentages are inconsistent, the program can still run ignoring these percentages. In that case, it will be recorded in the ``warnings`` attribute of the result. This attribute is a list of textual warnings about the algorithm execution or its result.

.. code-block:: json
   :caption: Example of ``warnings`` result attribute content

    {"warnings": [
            "2 compound ingredients whose percentage type is undefined.",
            "The product as a high number of impact uncharacterized ingredients: 33%",
            "The impact relative interquartile is high for Changement climatique (56%)"
        ]
    }


Result additional data
----------------------

The result of :meth:`~impacts_estimation.impacts_estimation.ImpactEstimator.estimate_impacts` or :class:`~impacts_estimation.impacts_estimation.estimate_impacts` is not only an impact. The result is a dictionary containing useful information about the estimated impact or the algorithm execution. The dictionary's attributes are detailed below :


.. list-table:: Result dictionary attributes
   :header-rows: 1
   :align: center


   *  - Attribute
      - Description
   *  - ``impact_geom_means``
      - **Geometric means of the impacts of all sampled recipes in each impact category.** The main result.
   *  - ``impact_geom_stdevs``
      - Geometric standard deviations of the impacts of all sampled recipes in each impact category.
   *  - ``impacts_quantiles``
      - Quantiles of the impacts of all sampled recipes in each impact category. Cutting points are defined by the ``quantiles_points`` parameter.
   *  - ``impacts_relative_interquartile``
      - Relative interquartile of the impacts of all sampled recipes in each impact category. Useful to estimate the spread of the possible impact.
   *  - ``ingredients_impact_share``
      - Average share of the impact carried by each ingredient for each impact category.
   *  - ``impacts_units``
      - Units in which the impacts are expressed.
   *  - ``product_quantity``
      - Quantity of product in grams for which the impact have been calculated.
   *  - ``const_relax_coef``
      - Constraints relaxation coefficient used to ensure a result. See :ref:`Constraints relaxation`.
   *  - ``warnings``
      - List of possible text warnings. See :ref:`Result warnings`.
   *  - ``reliability``
      - Result reliability indicator (1: very reliable, 4: one or several significant warnings)
   *  - ``ignored_unknown_ingredients``
      - List of ingredients that have been ignored if the ``ignore_unknown_ingredients`` parameter have been set to ``True``.
   *  - ``uncharacterized_ingredients``
      - List of ingredients with no data about nutrition and/or environmental impact.
   *  - ``uncharacterized_ingredients_ratio``
      - Ratio ingredients with no data about nutrition and/or environmental impact.
   *  - ``uncharacterized_ingredients_mass_proportion``
      - Average mass proportion of ingredients with no data about nutrition and/or environmental impact.
   *  - ``number_of_runs``
      - Number of runs before impact convergence.
   *  - ``number_of_ingredients``
      - Number of ingredients of the product.
   *  - ``average_total_used_mass``
      - Average total ingredient mass used :math:`M` of the recipes.
   *  - ``calculation_time``
      - Impact calculation time in seconds.
   *  - ``data_sources``
      - Sources of the impact and nutrition data for each ingredient.
   *  - ``impact_distributions``
      - Distributions of the impacts of all sampled recipes in each impact category. Only present if the ``distributions_as_result`` parameter is set to ``True``.
   *  - ``mean_confidence_interval_distribution``
      - Distributions of the confidence interval of the mean of the impacts of all sampled recipes in each impact category. Only present if the ``distributions_as_result`` parameter is set to ``True``.
   *  - ``confidence_score_distribution``
      - Distributions of the confidence score of all sampled recipes. Only present if the ``distributions_as_result`` parameter is set to ``True``.
   *  - ``recipes``
      - Recipes calculated for the impact estimation. Only present if the ``distributions_as_result`` parameter is set to ``True``.
   *  - ``total_used_mass_distribution``
      - Distributions of the total ingredient mass used :math:`M` of all sampled recipes. Only present if the ``distributions_as_result`` parameter is set to ``True``.

Product check and preprocessing
-------------------------------

Before calculating the impact of a product with :meth:`~impacts_estimation.impacts_estimation.ImpactEstimator.estimate_impacts`, the constructor of the :class:`~impacts_estimation.impacts_estimation.ImpactEstimator` class does some checks on the product with private methods.

* :meth:`~impacts_estimation.impacts_estimation.ImpactEstimator._remove_allergens` removes allergens from the ingredient tree to avoid them to be considered as subingredients. Allergens are usually present surrounded by parenthesis in the ingredient list (ex: *wheat flour (gluten)*). If the product has identified allergens, ingredients that are unique subingredients of a compound ingredient and that correspond to a allergen are removed from the ingredient tree.
* :meth:`~impacts_estimation.impacts_estimation.ImpactEstimator._check_ingredients` will perform checks and preprocessing on ingredients such as removing ingredients that are not present in Open Food Facts's ingredients taxonomy or raising an exception if no ingredient have environmental impact values.
* :meth:`~impacts_estimation.impacts_estimation.ImpactEstimator._check_defined_percentages` will check the validity of ingredients percentages. If an inconsistency is spotted (for example a higher percentage defined for the second ingredient than the first), the defined percentages will not be used and a warning will be added to the result.
* :meth:`~impacts_estimation.impacts_estimation.ImpactEstimator._check_product_water_loss` will check if the product belongs to a category that has a high water loss potential, such as cheese for example. In that case, it will adjust the evaporation coefficient accordingly and add a warning to the result.
* :meth:`~impacts_estimation.impacts_estimation.ImpactEstimator._check_fermented_product` will check if the product belongs to a fermented product category or if it contains ingredients that may induce a fermentation. In that case, the hypothesis of conservation of the nutrients during product processing may be false for carbohydrates and sugars. These nutriments are then ignored and a warning is added to the result.
* :meth:`~impacts_estimation.impacts_estimation.ImpactEstimator.check_butters_product` checks if the ingredient is butter. In this case, the “fat” nutrient is the only one used by the algorithm (even when we make the recipe) and the evaporation coefficient is relaxed to 0.99, which allows to have almost 5000g of milk/cream to make 1000g of butter.
* :meth:`~impacts_estimation.impacts_estimation.ImpactEstimator._remove_double_parenthesis` checks that there is no information on the ingredient in the ingredient sub-list (happens very rarely... e.g. for fr:puree-de-tomate-mi-reduced ( en:acid ( en:e330 ) ) we keep the ingredient tomato puree).
* :meth:`~impacts_estimation.impacts_estimation.ImpactEstimator.check_nutri_well_informed` checks (1) if the product has more than 100g or less than 10g of nutrients and (2) if the product belongs to the category coffee or pepper without nutrients on the packaging or less than 10g of nutrients. In both cases, the product will automatically be “unreliable” (=4). 

