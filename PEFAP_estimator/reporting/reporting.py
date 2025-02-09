import os
import json
import io

from jinja2 import Environment, FileSystemLoader
import matplotlib.pyplot as plt
import pylab
import seaborn as sns

from impacts_estimation.impacts_estimation import estimate_impacts
from impacts_estimation.vars import AGRIBALYSE_IMPACT_CATEGORIES_FR, TOP_LEVEL_NUTRIMENTS_CATEGORIES, \
    ID_AGRIBALYSE_ISSUES
from impacts_estimation.utils import flat_ingredients_list_DFS, agribalyse_impact_name_i18n
from utils import get_product_from_barcode, ensure_extension, smart_round_format
from ingredients_characterization.vars import AGRIBALYSE_DATA_FILEPATH
from data import ingredients_data, off_categories, off_taxonomy

with open(AGRIBALYSE_DATA_FILEPATH, 'r', encoding='utf8') as file:
    agribalyse_data = {x['ciqual_AGB']: x for x in json.load(file)}


class ProductImpactReport:
    """ Class used to generate reports for Open Food Facts products impacts. """

    def __init__(self, barcode=None, product=None, barcode_similar = None, ciqual_AGB_similar = None, impact_categories=None, main_impact_category=None,
                 product_mass=1000, language='french', use_nutritional_info=True):
        """
        Args:
            barcode (str): Barcode of the Open Food Facts product (use only if product is None).
                If this parameter is used, the product will be downloaded from Open Food Facts API.
            product (dict): Open Food Facts product (use only if barcode is None)
            impact_categories (list): Impact categories to consider.
                By default will consider all the impact categories available in Agribalyse.
            main_impact_category (str): Main impact category to display. First element of impact_categories by default
            product_mass (float): Mass of product considered in grams
            language (str): Language of the report
        """
        self.impact_categories = impact_categories or AGRIBALYSE_IMPACT_CATEGORIES_FR
        self.main_impact_category = main_impact_category or self.impact_categories[0]
        self.product_mass = product_mass
        self.language = language.lower()
        self.language_short = language[:2]
        self.use_nutritional_info = use_nutritional_info

        assert self.main_impact_category in self.impact_categories
        assert all(agribalyse_impact_name_i18n(x) in AGRIBALYSE_IMPACT_CATEGORIES_FR for x in self.impact_categories)

        self._html_output = None
        self.images = {}

        if (barcode is not None) and (product is not None):
            raise ValueError('Both barcode and product parameters cannot be provided simultaneously.')

        if (barcode_similar is not None) and (ciqual_AGB_similar is not None):
            raise ValueError('Both barcode_similar and ciqual_AGB_similar parameters cannot be provided simultaneously.')

        if barcode is not None :
            self.product = get_product_from_barcode(barcode)
        elif product is not None and ciqual_AGB_similar is not None :
            self.product = product
            self.product['ecoscore_data'] = {'agribalyse' : {'agribalyse_food_code' : ciqual_AGB_similar}}
        elif product is not None and barcode_similar is not None :
            self.product = product
            data_agribalyse = get_product_from_barcode(barcode_similar)
            self.product['ecoscore_data'] = data_agribalyse['ecoscore_data']
        elif product is not None :
            self.product = product
        else:
            raise ValueError('Barcode and product parameters cannot be None simultaneously.')

        # Getting reference data from the corresponding Agribalyse product
        try:
            product_agribalyse_data = self.product['ecoscore_data']['agribalyse']
            if 'agribalyse_food_code' in product_agribalyse_data:
                self.agribalyse_proxy_code = product_agribalyse_data['agribalyse_food_code']
            elif 'agribalyse_proxy_food_code' in product_agribalyse_data:
                self.agribalyse_proxy_code = product_agribalyse_data['agribalyse_proxy_food_code']
            else:
                raise KeyError
        except KeyError:
            self.agribalyse_proxy_code = None

        self.has_agribalyse_proxy = self.agribalyse_proxy_code is not None

        if self.has_agribalyse_proxy:
            self.agribalyse_proxy_data = agribalyse_data[self.agribalyse_proxy_code]

            # Getting impact of non agricultural phases
            self.impact_base = {impact_category:
                                    sum([value for step, value in
                                         self.agribalyse_proxy_data
                                         ['impact_environnemental'][agribalyse_impact_name_i18n(impact_category)]
                                         ['etapes'].items()
                                         if step != 'Agriculture']) * product_mass / 1000
                                for impact_category in self.impact_categories}

            # Getting total reference impacts
            self.agribalyse_proxy_impacts = \
                {impact_category: self.agribalyse_proxy_data['impact_environnemental'][
                                      agribalyse_impact_name_i18n(impact_category)]['synthese']
                                  * product_mass / 1000
                 for impact_category in self.impact_categories}

        else:
            self.agribalyse_proxy_data = None
            self.impact_base = {impact_category: 0
                                for impact_category in self.impact_categories}
            self.agribalyse_proxy_impacts = None

        self._compute_impact()

        self.ingredients = list(self.impact_result['ingredients_impacts_share'][self.main_impact_category])
        self.ingredients_without_impact = [x for x in self.ingredients
                                           if (x not in ingredients_data)
                                           or ('impacts' not in ingredients_data[x])]

        self.env = Environment(loader=FileSystemLoader(
            os.path.join(os.path.dirname(os.path.realpath(__file__)), 'static')))
        self.env.filters['smart_round_format'] = smart_round_format
        self.template = self.env.get_template('product_impact_report_template.html')

    def _compute_impact(self):
        self.impact_result = estimate_impacts(self.product,
                                              self.impact_categories,
                                              quantity=self.product_mass,
                                              distributions_as_result=True,
                                              safe_mode=True, use_nutritional_info=self.use_nutritional_info)

    def main_impact_plot(self):
        """ Boxplot of the main impact """

        fig, ax = plt.subplots(figsize=(6, 1.5))

        impact_base = self.impact_base[self.main_impact_category]
        boxes = [
            {
                'label': '',
                'whislo': impact_base + self.impact_result['impacts_quantiles'][self.main_impact_category]['0.05'],
                'q1': impact_base + self.impact_result['impacts_quantiles'][self.main_impact_category]['0.25'],
                'med': impact_base + self.impact_result['impacts_quantiles'][self.main_impact_category]['0.5'],
                'q3': impact_base + self.impact_result['impacts_quantiles'][self.main_impact_category]['0.75'],
                'whishi': impact_base + self.impact_result['impacts_quantiles'][self.main_impact_category]['0.95'],
            }
        ]
        ax.bxp(boxes,
               vert=False,
               showfliers=False,
               medianprops=dict(linewidth=2),
               boxprops=dict(linewidth=2, color='#555555'),
               whiskerprops=dict(linewidth=2, color='#777777'),
               capprops=dict(linewidth=2, color='#777777'))

        if self.has_agribalyse_proxy:
            ax.axvline(self.agribalyse_proxy_impacts[self.main_impact_category],
                       linestyle='--',
                       color='darkgreen')

        lower, upper = ax.get_xlim()
        ax.set_xlim(0, upper)
        ax.set_ylim(0.85, 1.15)
        fig.tight_layout()

        return fig

    def impact_per_step_plot(self):
        """
            Stacked bar showing the impacts shares related to each production step.
            Only possible if the product is linked to an Agribalyse reference
        """
        if not self.has_agribalyse_proxy:
            raise Exception("The product has no agribalyse proxy."
                            "No information about productions steps are available.")

        # Creating the figure for the graphic
        fig = pylab.figure()
        ax = fig.add_subplot(111)

        rank = 0.5
        agricultural_impact_value = self.impact_result['impacts_quantiles'][self.main_impact_category]['0.5']
        steps = self.agribalyse_proxy_data \
            ['impact_environnemental'][agribalyse_impact_name_i18n(self.main_impact_category)]['etapes']
        total = agricultural_impact_value + \
                sum([v * self.product_mass / 1000 for k, v in steps.items() if k != 'Agriculture'])
        for step, value in reversed(list(steps.items())):
            if step == 'Agriculture':
                value = agricultural_impact_value
            else:
                value = value * self.product_mass / 1000

            ax.barh(y=rank,
                    width=value / total,
                    height=0.3,
                    left=0,
                    label=step,
                    color='#008040')
            ax.text(x=0.01,
                    y=rank + 0.25,
                    s=f"{step}: {value / total:.1%}")
            rank += 1

        xticks = [0, 0.25, 0.50, 0.75, 1]
        ax.set_xticks(xticks)
        ax.set_xticklabels([f"{int(x * 100)}%" for x in xticks])
        ax.set_yticks([])
        ax.set_ylim(0, rank)
        ax.set_xlim(0, 1)
        fig.tight_layout()

        return fig

    def impact_per_ingredient_plot(self):
        """
            Stacked bar showing the impacts shares related to each ingredient.
        """

        # Creating the figure for the graphic
        fig = pylab.figure()
        ax = fig.add_subplot(111)

        rank = 0.5
        impact_shares = {k: v for k, v
                         in self.impact_result['ingredients_impacts_share'][self.main_impact_category].items()}

        for ingredient in reversed(self.recipe_ingredients_in_list_order()):
            value = impact_shares[ingredient]
            ax.barh(y=rank,
                    width=value,
                    height=0.3,
                    left=0,
                    label=ingredient,
                    color='#008040')

            if ingredient in self.ingredients_without_impact:
                text_color = 'darkred'
            else:
                text_color = 'black'

            ax.text(x=0.01,
                    y=rank + 0.25,
                    s=f"{ingredient}: {value:.1%}",
                    color=text_color)
            rank += 1

        xticks = [0, 0.25, 0.50, 0.75, 1]
        ax.set_xticks(xticks)
        ax.set_xticklabels([f"{int(x * 100)}%" for x in xticks])
        ax.set_yticks([])
        ax.set_ylim(0, rank)
        ax.set_xlim(0, 1)
        fig.tight_layout()

        return fig

    def mass_per_ingredient_plot(self):
        """
            Stacked bar showing the mass shares related to each ingredient.
        """

        # Creating the figure for the graphic
        fig = pylab.figure()
        ax = fig.add_subplot(111)

        rank = 0.5
        for ingredient in reversed(self.recipe_ingredients_in_list_order()):
            value = self.impact_result['ingredients_mass_share'][ingredient]
            ax.barh(y=rank,
                    width=value,
                    height=0.3,
                    left=0,
                    label=ingredient,
                    color='#008040')

            ax.text(x=0.01,
                    y=rank + 0.25,
                    s=f"{ingredient}: {value:.1%}")
            rank += 1

        xticks = [0, 0.25, 0.50, 0.75, 1]
        ax.set_xticks(xticks)
        ax.set_xticklabels([f"{int(x * 100)}%" for x in xticks])
        ax.set_yticks([])
        ax.set_ylim(0, rank)
        ax.set_xlim(0, 1)
        fig.tight_layout()

        return fig

    def impacts_data(self):

        result = dict()
        for impact_category in self.impact_categories:
            impact_data = {
                'category': impact_category,
                'unit': self.impact_result['impacts_units'][impact_category],
                'confidence_interval': ''
            }

            if impact_category in self.impact_result['impacts_quantiles']:
                impact_data['amount'] = self.impact_base[impact_category] + \
                                        self.impact_result['impacts_quantiles'][impact_category]['0.5']
            else:
                impact_data['amount'] = "This impact could not be calculated."

            if impact_category in self.impact_result['impacts_quantiles']:
                impact_data['conf_int_lower_bound'] = self.impact_base[impact_category] + \
                                                      self.impact_result['impacts_quantiles'][impact_category]['0.05']
            else:
                impact_data['conf_int_lower_bound'] = "This impact could not be calculated."

            if impact_category in self.impact_result['impacts_quantiles']:
                impact_data['conf_int_upper_bound'] = self.impact_base[impact_category] + \
                                                      self.impact_result['impacts_quantiles'][impact_category]['0.95']
            else:
                impact_data['conf_int_upper_bound'] = "This impact could not be calculated."

            if self.has_agribalyse_proxy:
                impact_data['reference_impact'] = self.agribalyse_proxy_impacts[impact_category]

            result[impact_category] = impact_data

        return result

    def off_categories(self):
        """ Getting the names of the OFF categories in the desired language. """
        result = []
        if self.product.get('categories_tags'):
            for category in self.product['categories_tags']:
                try:
                    category_name = off_categories[category]['name'].get(self.language_short,
                                                                         off_categories[category]['name']['en'])
                    result.append(category_name)
                except KeyError:
                    result.append(category)

        return result

    def categorize_ingredients(self, ingredient_or_product):

        result = dict()

        # For ingredients only:
        if '_id' not in ingredient_or_product:
            ingredient_id = ingredient_or_product['id']
            result['id'] = ingredient_id
            result['in_taxonomy'] = ingredient_id in off_taxonomy
            result['has_nutrition'] = ingredient_id in ingredients_data \
                                      and 'nutriments' in ingredients_data[ingredient_id]
            result['has_impact'] = ingredient_id in ingredients_data \
                                   and 'impacts' in ingredients_data[ingredient_id]

            result['in_recipe'] = ingredient_id \
                                  in self.impact_result['ingredients_impacts_share'][self.main_impact_category]

            try:
                result['nutritional_references'] = \
                    [x['entry'] for x in self.impact_result['data_sources'][ingredient_id]['nutrition']]
            except KeyError:
                result['nutritional_references'] = []

            try:
                result['environmental_references'] = \
                    [x['entry'] for x in self.impact_result['data_sources'][ingredient_id]['environmental_impact']]
            except KeyError:
                result['environmental_references'] = []

        # For product and compound ingredients
        if 'ingredients' in ingredient_or_product:
            result['ingredients'] = []
            for subingredient in ingredient_or_product['ingredients']:
                result['ingredients'].append(self.categorize_ingredients(subingredient))

        return result

    def off_ingredients(self):
        """ Get a nested list of dictionaries containing the ingredients of the product and custom attributes """

        return self.categorize_ingredients(self.product)['ingredients']

    def recipe_ingredients_in_list_order(self):
        """
            Returns a list containing the names of the ingredients of the recipe in the order in which they first appear
             in the ingredients list.
        """

        result = flat_ingredients_list_DFS(self.product)

        # Removing ingredients that are not in the recipe
        result = [x['id'] for x in result if x['id'] in self.ingredients]

        # Removing the duplicates
        result = list(dict.fromkeys(result))

        return result

    def _generate_figure(self, plotting_function, figure_name):
        fig = plotting_function()

        string_io = io.BytesIO()
        fig.savefig(string_io, format='svg')
        self.images[figure_name] = string_io.getvalue().decode("utf-8").replace('\n', '')

    def _generate_figures(self):
        """ Generating the figures png files """

        sns.set()

        # Main impact plot
        self._generate_figure(plotting_function=self.main_impact_plot,
                              figure_name='main_impact_plot')

        # Impact per step plot
        if self.has_agribalyse_proxy:
            self._generate_figure(plotting_function=self.impact_per_step_plot,
                                  figure_name='impact_per_step_plot')

        # Impact per ingredient
        self._generate_figure(plotting_function=self.impact_per_ingredient_plot,
                              figure_name='impact_per_ingredient_plot')

        # Mass per ingredient
        self._generate_figure(plotting_function=self.mass_per_ingredient_plot,
                              figure_name='mass_per_ingredient_plot')

    def _generate_html(self):
        """ Generate the html version of the report """
        with open(os.path.join(os.path.dirname(os.path.realpath(__file__)), 'static', 'pure-min.css'),
                  encoding='utf8') as file:
            stylesheet = file.read()
        with open(os.path.join(os.path.dirname(os.path.realpath(__file__)), 'static', 'style.css'),
                  encoding='utf8') as file:
            stylesheet += file.read()

        template_vars = {"product_name": self.product.get('product_name', ''),
                         "barcode": self.product['_id'],
                         "main_impact_category": self.main_impact_category,
                         "has_agribalyse_proxy": self.has_agribalyse_proxy,
                         "reference_agb_product":
                             self.agribalyse_proxy_data['nom_francais'] if self.has_agribalyse_proxy else None,
                         "has_ingredients_without_impact": len(self.ingredients_without_impact) > 0,
                         "product_mass": self.product_mass,
                         "images": self.images,
                         "off_categories": self.off_categories(),
                         "total_mass_used": self.impact_result['average_total_used_mass'],
                         "full_ingredient_list": self.product.get('ingredients_text', ''),
                         "impacts_data": self.impacts_data(),
                         "result_warnings": self.impact_result['warnings'],
                         "reliability": str(self.impact_result['reliability']),
                         "off_ingredients": self.off_ingredients(),
                         "stylesheet": stylesheet}

        self._html_output = self.template.render(template_vars)

    def to_html(self, filename=None):
        """ Export the report to html """

        filename = filename or f"{self.product['_id']} - {self.product.get('product_name')}"
        filename = ensure_extension(filename, 'html')

        self._generate_figures()
        self._generate_html()
        with open(filename, 'w', encoding='utf8') as file:
            file.write(self._html_output)
