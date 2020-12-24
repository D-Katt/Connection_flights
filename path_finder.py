"""Модуль для генерации расписания перелетов между условными точками и построения маршрута.
1. Методом случайного перебора списка исходных точек "cities" формируется словарь "routes",
   где названиям точек вылета соответствуют словари продолжительности полета до связанных городов.
2. Методом случайного выбора формируется расписание полетов между городами "flights" -
   в формате pd.DataFrame, содержит точку вылета, точку прилета, день недели, время вылета и стоимость.
Расписание условное - структурировано по дням недели. Между двумя точками может существовать
от 1 до 7 прямых рейсов в неделю в обоих направлениях либо ни одного прямого рейса.
Стоимость зависит от продолжительности перелета и включает наценку (от 1% до 30%).
Стоимость перелета между двумя точками в разных направлениях, в разные дни недели и время суток отличается.
Пользовать вводит точку вылета и конечный пункт назначения.
Программа находит крайтчайший путь - путь с минимальным количеством стыковочных рейсов.
Выводится рекомендуемый маршрут и все варианты перелетов с информацией о стоимости, времени вылета
из каждой точки, общей продолжительности перелетов (время на борту) и длительности путешествия
с учетом трансферов между стыковочными рейсами.
"""

import pandas as pd
import random
from datetime import timedelta
from collections import defaultdict, deque

cities = ['A', 'B', 'C', 'D', 'E', 'F', 'G', 'H', 'I',
          'J', 'K', 'L', 'M', 'N', 'O', 'P', 'Q', 'R',
          'S', 'T', 'U', 'V', 'W', 'X', 'Y', 'Z']

week_days = {1: 'Понедельник', 2: 'Вторник', 3: 'Среда', 4: 'Четверг',
             5: 'Пятница', 6: 'Суббота', 7: 'Воскресенье'}

# -------------------------- Генерация случайных данных ----------------------------------------


def set_price(minutes: int) -> int:
    """Функция определяет стоимость с учетом времени перелета,
    добавляет случайную наценку в пределах до 30%."""
    price_per_minute = 30
    random_increase = 1 + random.randint(1, 30) / 100
    price = int(price_per_minute * minutes * random_increase)
    return price


def add_route(routes: defaultdict, existing_routes: set, flights: pd.DataFrame) -> tuple:
    """Функция случайным образом выбирает два города и продолжительность
    перелета между ними и добавляет в словарь маршрутов."""

    duplicate_routes = True

    while duplicate_routes:

        origin_city = random.choice(cities)
        possible_destinations = set(cities).difference({origin_city})
        destination_city = random.choice(list(possible_destinations))

        if (origin_city, destination_city) not in existing_routes:
            duplicate_routes = False
            existing_routes.add((origin_city, destination_city))
            existing_routes.add((destination_city, origin_city))

            # Продолжительность перелета в минутах:
            travel_time_minutes = random.randint(90, 540)
            hours = travel_time_minutes // 60
            minutes = travel_time_minutes % 60
            travel_time = timedelta(minutes=minutes, hours=hours)

            # Прямой и обратный маршрут:
            routes[origin_city][destination_city] = travel_time
            routes[destination_city][origin_city] = travel_time

            # Расписание вылетов:
            flights = make_schedule(origin_city, destination_city, travel_time, flights)

    return routes, existing_routes, flights


def make_schedule(origin_city: str, destination_city: str, travel_time, schedule: pd.DataFrame) -> pd.DataFrame:
    """Функция случайным образом формирует расписание вылетов
    между двумя городами - от 1 до 7 рейсов в неделю в оба конца
    с 5-часовым интервалом между прямым и обратным рейсом."""

    flights_per_week = random.randint(1, 7)

    for _ in range(flights_per_week):
        # День недели и время вылета для прямого рейса:
        direct_week_day = random.randint(1, 7)
        direct_hours = random.randint(0, 23)
        direct_minutes = random.randint(0, 59)
        price = set_price(routes[origin_city][destination_city].seconds // 60)
        direct_time = timedelta(hours=direct_hours, minutes=direct_minutes)
        schedule = schedule.append({'city_from': origin_city, 'city_to': destination_city,
                                    'week_day': direct_week_day, 'time': direct_time,
                                    'price': price},
                                   ignore_index=True)

        # День недели и время вылета для обратного рейса
        # с учетом 5-часового интервала между прямым и обратным рейсом:
        time_since_week_start = timedelta(days=direct_week_day) + direct_time
        time_since_week_start += travel_time + timedelta(hours=5)
        backward_week_day = time_since_week_start.days
        if backward_week_day > 7:
            backward_week_day = backward_week_day % 7
        backward_hours = time_since_week_start.seconds // 3600
        if backward_hours > 24:
            backward_hours = backward_hours % 24
        backward_minutes = time_since_week_start.seconds // 60 % 60
        price = set_price(routes[destination_city][origin_city].seconds // 60)
        backward_time = timedelta(hours=backward_hours, minutes=backward_minutes)

        schedule = schedule.append({'city_from': destination_city, 'city_to': origin_city,
                                    'week_day': backward_week_day, 'time': backward_time,
                                    'price': price},
                                   ignore_index=True)

    return schedule


def find_flights(cities: list) -> list:
    """Функция подбирает варианты времени вылета для найденного маршрута,
    с тем чтобы общее время в пути было минимальным, и одсчитывает общую стоимость."""

    # Варианты перелета между первыми двумя точками:
    city_from = cities[0]
    city_to = cities[1]
    start_options = flights[(flights['city_from'] == city_from) & (flights['city_to'] == city_to)]

    available_flights = []  # Список для всех вариантов вылета из первой точки

    for index in range(len(start_options)):

        city_from = cities[0]  # Обновляем первые две точки на следующих циклах
        city_to = cities[1]

        this_option_price = start_options.iloc[index, :]['price']

        day = start_options.iloc[index, :]['week_day']
        time = start_options.iloc[index, :]['time']
        time_seconds = time.seconds
        hours, minutes = time_seconds // 3600, time_seconds // 60 % 60

        display_day = week_days[day]
        display_time = '{:02}:{:02}'.format(hours, minutes)
        this_option_flights = city_from + ' ' + display_day + ' ' + display_time

        # Для отслеживания времени посадки на следующий рейс и общей продолжительности пути:
        start_time = timedelta(days=day, hours=hours, minutes=minutes)
        flight_duration = routes[city_from][city_to]
        time_since_start = start_time + flight_duration

        # Находим ближайшие варианты посадки на следующие рейсы маршрута:
        pos = 2
        while pos < len(cities):
            city_from = city_to
            city_to = cities[pos]
            pos += 1
            connection_flight, time_since_start, this_option_price = find_nearest_flight(city_from, city_to,
                                                                                         time_since_start,
                                                                                         this_option_price)
            this_option_flights += connection_flight

        travel_time = time_since_start - start_time

        available_flights.append(this_option_flights + ' -> ' + f'{this_option_price} руб. ({travel_time})')

    return available_flights


def find_nearest_flight(origin_city: str, destination_city: str, time_pos: timedelta, total_price: int) -> tuple:
    """Функция находит ближайший по времени вылета стыковочный рейс
    с учетом 3-часового интервала для трансфера между рейсами."""

    time_pos += timedelta(hours=3)  # Минимальный интервал для трансфера
    day, hours, minutes = timedelta_to_day_hour_minutes(time_pos)

    # Все рейсы (отсортированная таблица):
    options = flights[(flights['city_from'] == origin_city) & (flights['city_to'] == destination_city)]

    # Рейсы до конца текущей недели:
    same_week = options[(options['week_day'] >= day) & (options['time'] >= timedelta(hours=hours, minutes=minutes))]

    if len(same_week) > 0:
        options = same_week

    # Время вылета и стоимость следующего рейса:
    flight_day, flight_time, price = options.iloc[0, :][['week_day', 'time', 'price']].values
    display_time = timedelta_to_formatted_string(flight_time)

    connection_flight = f' {origin_city} {week_days[flight_day]} {display_time}'
    total_price += price

    # Время ожидания (сверх минимального интервала в 3 часа):
    gap = timedelta(days=flight_day) + flight_time - timedelta(days=day, hours=hours, minutes=minutes)
    # Если ближайший рейс только на следующей неделе, делаем поправку:
    if len(same_week) == 0:
        gap += timedelta(days=7)
    time_pos += gap

    # Добавляем продолжительность перелета:
    time_pos += routes[origin_city][destination_city]

    return connection_flight, time_pos, total_price


def timedelta_to_day_hour_minutes(time_pos: timedelta) -> tuple:
    """Функция преобразует объект timedelta в кортеж,
    содержащий день недели, часы и минуты."""
    week_day = time_pos.days
    if week_day > 7:
        week_day = week_day % 7
    hours = time_pos.seconds // 3600
    if hours > 24:
        hours = hours % 24
    minutes = time_pos.seconds // 60 % 60
    return week_day, hours, minutes


def timedelta_to_formatted_string(td: timedelta) -> str:
    """Функция преобразует объект timedelta в форматированную строку."""
    time_seconds = td.seconds
    hours, minutes = time_seconds // 3600, time_seconds // 60 % 60
    formatted_time = '{:02}:{:02}'.format(hours, minutes)
    return formatted_time


# Ключи - названия точек вылета, значения - словари продолжительности полета до связанных точек:
routes = defaultdict(dict)

# Расписание перелетов:
flights = pd.DataFrame(columns=['city_from', 'city_to', 'week_day', 'time', 'price'])

# Формируем 50 маршрутов между 26 городами:
existing_routes = set()
n_connections = 50

while len(existing_routes) < n_connections:
    routes, existing_routes, flights = add_route(routes, existing_routes, flights)

flights.sort_values(by=['city_from', 'city_to', 'week_day', 'time'], inplace=True)

print('Расписание вылетов')
print(flights.head())

# ---------------------- Алгоритм поиска маршрута -----------------------------

# Начальная и конечная точки маршрута:
start_vertex = input('\nВведите точку вылета:\t')
end_vertex = input('Введите пункт назначения:\t')

# Если одной из выбранных точек нет в словаре доступных маршрутов:
if start_vertex not in routes or end_vertex not in routes:
    print(f'\nНевозможно построить маршрут из пункта {start_vertex} в пункт {end_vertex}.')

# Обход графа с поиском кратчейшего маршрута (минимум стыковочных рейсов):
else:
    n_routes = {city: None for city in routes.keys()}
    n_routes[start_vertex] = 0
    queue = deque([start_vertex])
    parents = {city: None for city in routes.keys()}

    path_exists = False

    while queue and not path_exists:
        cur_v = queue.popleft()

        for neigh_v in routes[cur_v]:

            if n_routes[neigh_v] is None:
                n_routes[neigh_v] = n_routes[cur_v] + 1
                parents[neigh_v] = cur_v
                queue.append(neigh_v)

                if neigh_v == end_vertex:
                    path_exists = True
                    break

    if not path_exists:
        print(f'\nНевозможно построить маршрут из пункта {start_vertex} в пункт {end_vertex}.')

    else:  # Восстановление оптимального маршрута от конечной точки
        path = [end_vertex]

        parent = parents[end_vertex]
        next_city = end_vertex
        total_time_on_board = timedelta(minutes=0, hours=0)

        while not parent is None:
            path.append(parent)
            total_time_on_board += routes[parent][next_city]
            next_city = parent
            parent = parents[parent]

        path = path[::-1]
        total_time_on_board = timedelta_to_formatted_string(total_time_on_board)
        available_flights = find_flights(path)

        print('\nРекомендуемый маршрут:', ' -> '.join(path))
        print(f'Общее время на борту: {total_time_on_board}')
        print('\nДоступные варианты перелета:')
        for option in available_flights:
            print(option)
