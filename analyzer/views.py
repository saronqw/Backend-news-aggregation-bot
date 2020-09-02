from datetime import *

import numpy
import time
from chartjs.views.lines import BaseLineOptionsChartView
from django.http import HttpResponse
from django.template import loader
from rest_framework import viewsets
from rest_framework.response import Response

from analyzer.models import Keyword, KeywordGroup
from analyzer.serializers import KeywordSerializer
from rest_api.models import NewsItem, University


def all_top_tags():
    def top_tags(university_id):
        tag_items = Keyword.objects.filter(university_id=university_id).order_by('-coef')
        counts = []
        for item in tag_items:
            counts.append(item.count)
        counts_median = numpy.median(counts) + (len(tag_items) // 100) * 2 - 2

        result_tags = []
        for item in tag_items:
            if counts_median <= item.count < counts_median * 3 and (
                    item.tag.find(' ') != -1 or item.tag.find('-') != -1):
                result_tags.append(item)
        return result_tags

    top = []
    tags_text = []

    def already_exist(item):
        if item.tag in tags_text:
            return True
        else:
            return False

    for university_id in range(1, 11):
        top_tags_items = top_tags(university_id)
        i = 0
        tag = top_tags_items[i]
        while already_exist(tag):
            i += 1
            tag = top_tags_items[i]
        top.append(tag)
        tags_text.append(tag.tag)
    return top


class KeywordViewSet(viewsets.ViewSet):

    def list(self, request):
        tags = all_top_tags()

        serializer = KeywordSerializer(tags, many=True, context={'request': request})
        return Response(serializer.data)


def index(request):
    template = loader.get_template('analyzer/index.html')
    return HttpResponse(template.render(request=request))


class LineChartJSONView(BaseLineOptionsChartView):
    tags = all_top_tags()
    serializer = KeywordSerializer(tags, many=True)
    tags_data = sorted(serializer.data, key=lambda k: k.get('score'), reverse=True)

    def get_dataset_options(self, index, color):
        return []

    def get_labels(self):
        labels = []
        for keyword in self.tags_data:
            labels.append(keyword.get('tag'))

        return labels

    def get_data(self):
        data = []
        for keyword in self.tags_data:
            data.append(keyword.get('score'))

        return [data]

    def get_options(self):
        return {
            'scales': {
                'xAxes': [{
                    'gridLines': {
                        'display': False
                    }
                }]
            },
            'plugins': {
                'colorschemes': {
                    'scheme': 'tableau.Classic10'
                }
            },
            'responsive': True,
            'legend': {
                'display': False
            },
            'title': {
                'display': True,
                'text': 'Top tags universities'
            },
            'animation': {
                'duration': 1500,
                'easing': 'easeOutSine'
            }
        }


class ComparisonChartJSONView(BaseLineOptionsChartView):

    def get_dataset_options(self, index, color):
        return []

    def get_labels(self):
        labels = [
            'NUS',
            'Harvard',
            'NSU',
            'Cambridge',
            'Caltech',
            'SPSU',
            'Stanford',
            'TSU',
            'ITMO',
        ]
        return labels

    def get_data(self):
        data = [
            53,
            58,
            61,
            61,
            67,
            70,
            75,
            78,
            83,
        ]
        return [data]

    def get_options(self):
        return {
            'plugins': {
                'colorschemes': {
                    'fillAlpha': 0,
                    'scheme': 'tableau.Tableau10',
                }
            },
            'responsive': True,
            'legend': {
                'position': 'right',
                'labels': {
                    'boxWidth': 60
                }
            },
            'title': {
                'display': True,
                'text': 'Collaborations with other universities',
            },
            'animation': {
                'duration': 1500
            }
        }

def plotbox_news_number(years):
    count_university = len(University.objects.all())
    array = {}
    for university_id in range(1, count_university + 1):
        array[university_id] = {}
        for year in years:
            current_week = datetime(year, 1, 1, 0, 0) + timedelta(7)
            news_items = NewsItem.objects.filter(pub_date__year=year, university_id=university_id).order_by('pub_date')
            count = 0
            (array[university_id])[year] = []
            for news_item in news_items:
                if news_item.pub_date < current_week:
                    count += 1
                else:
                    (array[university_id])[year].append(count)
                    current_week += timedelta(7)
                    while news_item.pub_date >= current_week:
                        (array[university_id])[year].append(0)
                        current_week += timedelta(7)
                    count = 1
    return array


def plotbox_words_number(years):
    count_university = len(University.objects.all())
    array = {}

    for university_id in range(1, count_university + 1):
        array[university_id] = {}
        for year in years:
            current_week = datetime(year, 1, 1, 0, 0) + timedelta(7)
            news_items = NewsItem.objects.filter(pub_date__year=year, university_id=university_id).order_by('pub_date')
            count = 0
            news_count = 0
            (array[university_id])[year] = []
            for news_item in news_items:
                if news_item.pub_date < current_week:
                    count += len(news_item.full_text.split(' '))
                    news_count += 1
                else:
                    if news_count == 0:
                        (array[university_id])[year].append(None)
                    else:
                        (array[university_id])[year].append(count // news_count)
                    current_week += timedelta(7)
                    while news_item.pub_date >= current_week:
                        (array[university_id])[year].append(None)
                        current_week += timedelta(7)
                    count = len(news_item.full_text.split(' '))
                    news_count = 1
    return array


def calc_month_publication_number():
    count_days_ago = datetime.now() - timedelta(3 * 370)
    news_items = NewsItem.objects.filter(pub_date__range=[count_days_ago, datetime.now()]).order_by('-pub_date')
    today = datetime.now()
    week_ago_date = today - timedelta(days=14) + timedelta(days=-today.weekday(), weeks=1)

    label = datetime.now() + timedelta(days=-today.weekday(), weeks=1) - timedelta(days=7)
    pubNumArray = [{}, {}, {}, {}, {}, {}, {}, {}, {}, {}, {}]
    counts = [0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0]

    for item in news_items:
        while item.pub_date < week_ago_date:
            for i in range(1, len(pubNumArray)):
                (pubNumArray[i])[label] = counts[i]
            counts = [0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0]
            label = label - timedelta(days=28)
            week_ago_date = week_ago_date - timedelta(days=28)
        counts[item.university_id] += 1

    return pubNumArray


def calc_publication_words_number():
    count_days_ago = datetime.now() - timedelta(3 * 370)
    news_items = NewsItem.objects.filter(pub_date__range=[count_days_ago, datetime.now()]).order_by('-pub_date')
    today = datetime.now()
    week_ago_date = today - timedelta(days=14) + timedelta(days=-today.weekday(), weeks=1)

    label = datetime.now() + timedelta(days=-today.weekday(), weeks=1) - timedelta(days=7)
    # pubNumDict = {}
    pubWordsNumArray = [{}, {}, {}, {}, {}, {}, {}, {}, {}, {}, {}]
    counts = [0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0]
    news_counts = [0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0]

    for item in news_items:
        id = item.university_id
        news_date = item.pub_date
        while news_date < week_ago_date:
            for i in range(1, len(pubWordsNumArray)):
                if  news_counts[i] == 0:
                    (pubWordsNumArray[i])[label] = None
                else:
                    (pubWordsNumArray[i])[label] = counts[i] // news_counts[i]
            counts = [0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0]
            news_counts = [0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0]
            label = label - timedelta(days=28)
            week_ago_date = week_ago_date - timedelta(days=28)
        counts[id] += len(item.full_text.split(' '))
        news_counts[id] += 1

    return pubWordsNumArray


class NewsPerWeekChartJSONView(BaseLineOptionsChartView):
    university_array = calc_month_publication_number()

    def get_providers(self):
        queryset = University.objects.all()
        providers = []
        for university in queryset:
            providers.append(university.name)
        return providers

    def get_dataset_options(self, index, color):
        return {
            'backgroundColor': 'rgba(0, 255, 0, 0)',
            'fill': False,
            'lineTension': 0
        }

    def get_labels(self):
        dict = self.university_array[1]
        keys = dict.keys()
        dates = []
        for date_and_time in keys:
            dates.append(date_and_time.date().strftime('%b %d, %y'))
        dates.reverse()
        return dates

    def get_data(self):
        temp_data = []
        return_array = []
        for dict in self.university_array[1:]:
            temp_data = list(dict.values())
            temp_data.reverse()
            return_array.append(temp_data)
        return return_array

    def get_options(self):
        return {
            'plugins': {
                'colorschemes': {
                    'scheme': 'tableau.Classic10'
                }
            },
            'responsive': True,
            'title': {
                'display': True,
                'text': 'Publication activity'
            },
            'tooltips': {
                'mode': 'index',
            },
            'scales': {
                'yAxes': [{
                    'ticks': {
                        'suggestedMin': 0,
                    }
                }]
            }
        }


class WordsPerWeekChartJSONView(BaseLineOptionsChartView):
    university_array = calc_publication_words_number()

    def get_providers(self):
        queryset = University.objects.all()
        providers = []
        for university in queryset:
            providers.append(university.name)
        return providers

    def get_dataset_options(self, index, color):
        return {
            'backgroundColor': 'rgba(0, 255, 0, 0)',
            'fill': False,
            'lineTension': 0
        }

    def get_labels(self):
        dict = self.university_array[1]
        keys = dict.keys()
        dates = []
        for date_and_time in keys:
            dates.append(date_and_time.date().strftime('%b %d, %y'))
        dates.reverse()
        return dates

    def get_data(self):
        temp_data = []
        return_array = []
        for dict in self.university_array[1:]:
            temp_data = list(dict.values())
            temp_data.reverse()
            return_array.append(temp_data)

        return return_array

    def get_options(self):
        return {
            'plugins': {
                'colorschemes': {
                    'scheme': 'tableau.Classic10'
                }
            },
            'responsive': True,
            'title': {
                'display': True,
                'text': 'Volume of news publications'
            },
            'tooltips': {
                'mode': 'index',
            },
            'scales': {
                'yAxes': [{
                    'ticks': {
                        # 'suggestedMin': 0,
                        # 'suggestedMax': max_line + 1
                    }
                }]
            }
        }


class BoxPlotNewsChartJSONView(BaseLineOptionsChartView):
    years = [2017, 2018, 2019]
    news_number_data = plotbox_news_number(years)

    def get_providers(self):
        providers = [
            'TPU',
            'TSU',
            'NSU',
            'Harvard',
            'Stanford',
            'Caltech',
            'Cambridge',
            'ITMO',
            'NUS',
            'SPSU',
        ]
        return providers

    def get_dataset_options(self, index, color):
        color_scheme = [
            'rgba(31,119,180, 0.55)', 'rgba(255,127,14, 0.55)',
            'rgba(44,160,44, 0.55)', 'rgba(214,39,40, 0.55)',
            'rgba(148,103,189, 0.55)', 'rgba(140,86,75, 0.55)',
            'rgba(227,119,194, 0.55)', 'rgba(127,127,127, 0.55)',
            'rgba(188,189,34, 0.55)', 'rgba(23,190,207, 0.55)'
        ]

        color_scheme_without_alpha = [
            'rgb(0,0,139)', 'rgb(255,69,0)',
            'rgb(0,128,0)', 'rgb(255,0,0)',
            'rgb(148,0,211)', 'rgb(139,69,19)',
            'rgb(255,20,147)', 'rgb(112,128,144)',
            'rgb(205,133,63)', 'rgb(0,128,128)'
        ]

        options = [ {}, {}, {}, {}, {}, {}, {}, {}, {}, {} ]

        color_index = 0
        for item in options:
            item.update(
                {
                    'backgroundColor': color_scheme[color_index],
                    'borderColor': color_scheme_without_alpha[color_index],
                    'borderWidth': 1,
                    'itemRadius': 0
                }
            )
            color_index += 1

        return options[index]

    def get_labels(self):
        return self.years

    def get_data(self):

        data_array = []
        for x in list(self.news_number_data.values()):
           data_array.append(list(x.values()))

        return data_array

    def get_options(self):
        return {
            'responsive': True,
            'legend': {
                'position': 'top',
            },
            'title': {
                'display': True,
                'text': 'Analysis of publication activity'
            },
        }


class BoxPlotWordsChartJSONView(BaseLineOptionsChartView):
    years = [2017, 2018, 2019]
    news_number_data = plotbox_words_number(years)

    def get_providers(self):
        providers = [
            'TPU',
            'TSU',
            'NSU',
            'Harvard',
            'Stanford',
            'Caltech',
            'Cambridge',
            'ITMO',
            'NUS',
            'SPSU',
        ]
        return providers

    def get_dataset_options(self, index, color):
        color_scheme = [
            'rgba(31,119,180, 0.55)', 'rgba(255,127,14, 0.55)',
            'rgba(44,160,44, 0.55)', 'rgba(214,39,40, 0.55)',
            'rgba(148,103,189, 0.55)', 'rgba(140,86,75, 0.55)',
            'rgba(227,119,194, 0.55)', 'rgba(127,127,127, 0.55)',
            'rgba(188,189,34, 0.55)', 'rgba(23,190,207, 0.55)'
        ]

        color_scheme_without_alpha = [
            'rgb(0,0,139)', 'rgb(255,69,0)',
            'rgb(0,128,0)', 'rgb(255,0,0)',
            'rgb(148,0,211)', 'rgb(139,69,19)',
            'rgb(255,20,147)', 'rgb(112,128,144)',
            'rgb(205,133,63)', 'rgb(0,128,128)'
        ]

        options = [ {}, {}, {}, {}, {}, {}, {}, {}, {}, {} ]

        color_index = 0
        for item in options:
            item.update(
                {
                    'backgroundColor': color_scheme[color_index],
                    'borderColor': color_scheme_without_alpha[color_index],
                    'borderWidth': 1,
                    'itemRadius': 0
                }
            )
            color_index += 1

        return options[index]

    def get_labels(self):
        return self.years

    def get_data(self):

        data_array = []
        for x in list(self.news_number_data.values()):
           data_array.append(list(x.values()))

        return data_array

    def get_options(self):
        return {
            'responsive': True,
            'legend': {
                'position': 'top',
            },
            'title': {
                'display': True,
                'text': 'Volume of news publications analysis'
            },
        }


class RadarThemeChartJSONView(BaseLineOptionsChartView):
    # list_themes = list(KeywordGroup.objects.values_list('group_name', flat=True).order_by('id'))
    list_themes = list(KeywordGroup.objects.values_list('group_name', flat=True).order_by('id').exclude(group_name__in=['Other', 'Art', 'Research process']))
    list_universities = list(University.objects.values_list('name', flat=True).order_by('id'))

    def get_providers(self):
        return self.list_universities

    def get_dataset_options(self, index, color):
        color_scheme = [
            'rgba(31,119,180, 0.2)', 'rgba(255,127,14, 0.2)',
            'rgba(44,160,44, 0.2)', 'rgba(214,39,40, 0.2)',
            'rgba(148,103,189, 0.2)', 'rgba(140,86,75, 0.2)',
            'rgba(227,119,194, 0.2)', 'rgba(127,127,127, 0.2)',
            'rgba(188,189,34, 0.2)', 'rgba(23,190,207, 0.2)'
        ]

        color_scheme_without_alpha = [
            'rgb(0,0,139)', 'rgb(255,69,0)',
            'rgb(0,128,0)', 'rgb(255,0,0)',
            'rgb(148,0,211)', 'rgb(139,69,19)',
            'rgb(255,20,147)', 'rgb(112,128,144)',
            'rgb(205,133,63)', 'rgb(0,128,128)'
        ]

        options = [{}, {}, {}, {}, {}, {}, {}, {}, {}, {}]

        color_index = 0
        for item in options:
            item.update(
                {
                    'backgroundColor': color_scheme[color_index],
                    'borderColor': color_scheme_without_alpha[color_index],
                    'pointBackgroundColor': color_scheme_without_alpha[color_index],
                }
            )
            color_index += 1

        return options[index]

    def get_labels(self):
        return self.list_themes

    def get_data(self):

        keywords_data = Keyword.objects.all().exclude(group__group_name__in=['Other', 'Art', 'Research process'])

        # keywords_data = Keyword.objects.all()
        data = []
        for university in self.list_universities:
            university_keywords = keywords_data.filter(university__name=university)
            university_keywords_list = list(university_keywords)
            keyword_time = time.time()
            count_keywords = len(university_keywords_list)
            themes_dict = {}
            for theme in self.list_themes:
                themes_dict[theme] = 0
                university_keywords_theme = university_keywords.filter(group__group_name=theme)
                for keyword in university_keywords_theme:
                    themes_dict[theme] += 1

            print("theme counter: {:.2f}s".format(time.time() - keyword_time))
            university_array = []
            start_time = time.time()
            for item in themes_dict.values():
                university_array.append(round(item / count_keywords, 2) * 100)
            # print("Multiplication and division: {:.2f}s".format(time.time() - start_time))

            data.append(university_array)



        return data

    def get_options(self):
        return {
            'legend': {
                'position': 'right',
                'labels': {
                    'boxWidth': 60
                }
            },
            'title': {
                'display': True,
                'text': 'University passports'
            },
            'scale': {
                'ticks': {
                    'beginAtZero': True
                },
                'pointLabels': {
                  'fontSize': 20
                }
            }
        }
