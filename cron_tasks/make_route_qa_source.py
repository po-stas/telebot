# This is a django function called every night to regenerate text info about all routes

import re
import pymorphy2
from django.core.management.base import BaseCommand
from allclimbApp.models import Region, RouteReport, Route
import pandas as pd
import os
import errno
from django.db.models import Q
from allclimb.settings import LOG_DIR
from allclimbApp.luts_n_tables import grade_lut, type_lut_ru
from allclimbApp.luts_n_tables import top_lut_ru as top_lut
from django.contrib.postgres.aggregates import StringAgg
from django.db.models import Count
from django.db import models
from django.db.models.functions import Cast


class Command(BaseCommand):
    # args = 'Arguments is not needed'
    help = 'Django admin custom command poc.'

    def handle(self, *args, **options):

        # Convert geographic names to 'location' form for russian language
        def parse(name):
            name_parsed = []
            for word in name.split():
                norm_form = morph.parse(word)[0]
                loct_form = norm_form.inflect({'loct'})
                if loct_form:
                    loct_form = loct_form.word.capitalize()
                else:
                    loct_form = word
                name_parsed.append(loct_form)
            return ' '.join(name_parsed)

        def grade(route):
            grade = grade_lut[route["grade"]]
            if route["secgrade"] > route["grade"]:
                grade += '/' + grade_lut[route["secgrade"]]

            return ' ' + grade

        base_dir = os.path.join(LOG_DIR, 'qa_source')
        try:
            os.makedirs(base_dir)
        except OSError as e:
            if e.errno != errno.EEXIST:
                raise

        morph = pymorphy2.MorphAnalyzer(lang='ru')

        with open(os.path.join(base_dir, 'qa_route_specs.txt'), 'w') as out:
            for route in Route.objects.all().order_by('id').\
                    values('name', 'rtype', 'grade', 'secgrade', 'res3int', 'res4int',
                           'res1int', 'res2int', 'length', 'bolts', 'region__name', 'spot__name', 'sector__name',
                           'toptype', 'author', 'creationdate', 'info',
                           ).\
                    annotate(ascent_count=Count('Ascents')).\
                    annotate(rate_count=Count('Rates')):

                route_text = f'Маршрут "{route["name"]}" {type_lut_ru[route["rtype"]]} {grade(route)}'
                route_text += f' {route["length"]}м' if route["length"] > 1 else ''
                route_text += f' {route["bolts"]} болтов' if route["bolts"] > 1 else ''
                route_text += f', станция {top_lut[route["toptype"]]}' if -1 < route["toptype"] < len(top_lut)-1 else ''
                quick_draw = morph.parse('оттяжка')[0]
                route_text += f', нужно {route["bolts"]} {quick_draw.make_agree_with_number(route["bolts"]).word}' \
                    if route["bolts"] > 1 else ', сколько нужно оттяжек - неизвестно'
                meter = morph.parse('метр')[0]
                route_text += f', нужно {route["length"]} {meter.make_agree_with_number(route["length"]).word} веревки' \
                    if route["length"] > 1 else ', сколько нужно веревки - неизвестно'
                route_text += f', наверху {top_lut[route["toptype"]]}' if -1 < route["toptype"] < len(top_lut)-1 else \
                    ', что наверху - неизвестно'
                route_text += f', топ {top_lut[route["toptype"]]}' if -1 < route["toptype"] < len(top_lut)-1 else \
                    ', какой топ неизвестно'
                sector_name = re.sub(r"[^\w\s]+", "", route["sector__name"])
                region_name = parse(route['region__name'])
                if region_name == 'Крыме':
                    region_name = 'Крыму'   # Stupid pymorphy :))
                spot_name = parse(route['spot__name'])

                route_text += f', находится в {spot_name} в секторе {sector_name} в {region_name}'
                route_text += f', автор {route["author"]}' if route["author"] else ', автор неизвестен'
                route_text += f', год создания {route["creationdate"].year}' if route["creationdate"].year > 1971 else \
                    ', год создания неизвестен'
                route_text += f', {route["ascent_count"]} пролазов'
                route_text += f', {route["ascent_count"]} прохождений'
                route_text += f', {route["ascent_count"]} людей пролезло'
                route_text += f', {route["ascent_count"]} людей вылезло'
                route_text += f', {route["rate_count"]} лайков'
                route_text += f', {route["rate_count"]} людям нравится'
                route_text += f', {route["rate_count"]} оценок'

                out.write(route_text + '\n')
