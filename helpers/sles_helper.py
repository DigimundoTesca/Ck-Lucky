import json
from datetime import date, datetime, timedelta
from decimal import Decimal

from django.db.models import Min, Max

from helpers.helpers import Helper
from sales.models import TicketBase, TicketPOS, TicketOrder, TicketDetail, TicketExtraIngredient


class TicketPOSHelper(object):
    """
    Class that manages all types of entries, whether generated in a branch or
    from the web page.
    """
    def __init__(self):
        self.__all_tickets = None
        self.__all_tickets_details = None
        self.__all_extra_ingredients = None
        super(TicketPOSHelper, self).__init__()

    def set_all_tickets(self):
        self.__all_tickets = TicketPOS.objects.select_related('ticket')

    def set_all_tickets_details(self):
        self.__all_tickets_details = TicketDetail.objects. \
            select_related('ticket'). \
            select_related('cartridge'). \
            select_related('package_cartridge'). \
            all()

    def set_all_extra_ingredients(self):
        self.__all_extra_ingredients = TicketExtraIngredient.objects. \
            select_related('ticket_detail'). \
            select_related('extra_ingredient'). \
            select_related('extra_ingredient__ingredient'). \
            all()

    def get_all_tickets(self):
        """
        :rtype: django.db.models.query.QuerySet
        """
        if self.__all_tickets is None:
            self.set_all_tickets()
        return self.__all_tickets

    def get_all_tickets_details(self):
        """
        :rtype: django.db.models.query.QuerySet
        """
        if self.__all_tickets_details is None:
            self.set_all_tickets_details()
        return self.__all_tickets_details

    def get_tickets_details(self, initial_date, final_date):
        """
        :rtype: django.db.models.query.QuerySet
        """
        if self.__all_tickets_details is None:
            self.set_all_tickets_details()
        return self.__all_tickets_details.filter(ticket__created_at__range=[initial_date, final_date])

    def get_all_extra_ingredients(self):
        """
        :rtype: django.db.models.query.QuerySet
        """
        if self.__all_extra_ingredients is None:
            self.set_all_extra_ingredients()
        return self.__all_extra_ingredients

    def get_years_list(self):
        """
        Returns a list of all the years in which there have been sales
        """
        years_list = []

        for ticket_pos in self.get_all_tickets():
            if ticket_pos.ticket.created_at.year not in years_list:
                years_list.append(ticket_pos.ticket.created_at.year)

        return years_list

    def get_tickets_today_list(self):
        helper = Helper()

        tickets_list = []
        filtered_tickets = self.get_all_tickets().\
            filter(ticket__created_at__gte=helper.naive_to_datetime(date.today())).\
            order_by('-ticket__created_at')

        for ticket_pos in filtered_tickets:
            ticket_object = {
                'ticket_parent': ticket_pos.ticket,
                'order_number': ticket_pos.ticket.order_number,
                'cartridges': [],
                'cashier': ticket_pos.cashier,
                'packages': [],
                'total': Decimal(0.00),
                'is_active': ticket_pos.ticket.is_active,
            }

            for ticket_details in self.get_all_tickets_details():
                if ticket_details.ticket == ticket_pos.ticket:
                    if ticket_details.cartridge:
                        cartridge_object = {
                            'cartridge': ticket_details.cartridge,
                            'quantity': ticket_details.quantity
                        }
                        ticket_object['cartridges'].append(cartridge_object)
                        ticket_object['total'] += ticket_details.price
                    elif ticket_details.package_cartridge:
                        package_cartridge_object = {
                            'package': ticket_details.package_cartridge,
                            'quantity': ticket_details.quantity
                        }
                        ticket_object['packages'].append(package_cartridge_object)
                        ticket_object['total'] += ticket_details.price

            tickets_list.append(ticket_object)

        return tickets_list

    def get_dates_range_json(self):
        """
        Returns a JSON with a years list.
        The years list contains years objects that contains a weeks list
            and the Weeks list contains a weeks objects with two attributes:
            start date and final date. Ranges of each week.
        """
        helper = Helper()
        try:
            min_year = self.get_all_tickets().\
                aggregate(Min('ticket__created_at'))['ticket__created_at__min'].year
            max_year = self.get_all_tickets().\
                aggregate(Max('ticket__created_at'))['ticket__created_at__max'].year
            years_list = []  # [2015:object, 2016:object, 2017:object, ...]
        except Exception as e:
            min_year = datetime.now().year
            max_year = datetime.now().year
            years_list = []  # [2015:object, 2016:object, 2017:object, ...]

        while max_year >= min_year:
            year_object = {  # 2015:object or 2016:object or 2017:object ...
                'year': max_year,
                'weeks_list': [],
            }

            tickets_per_year = self.get_all_tickets().filter(
                ticket__created_at__range=[helper.naive_to_datetime(date(max_year, 1, 1)),
                                   helper.naive_to_datetime(date(max_year, 12, 31))])
            for ticket_item in tickets_per_year:
                if len(year_object['weeks_list']) == 0:
                    """
                    Creates a new week_object in the weeks_list of the actual year_object
                    """
                    week_object = {
                        'week_number': ticket_item.ticket.created_at.isocalendar()[1],
                        'start_date': ticket_item.ticket.created_at.date().strftime("%d-%m-%Y"),
                        'end_date': ticket_item.ticket.created_at.date().strftime("%d-%m-%Y"),
                    }
                    year_object['weeks_list'].append(week_object)
                    # End if
                else:
                    """
                    Validates if exists some week with an similar week_number of the actual year
                    If exists a same week in the list validates the start_date and the end_date,
                    In each case valid if there is an older start date or a more current end date
                        if it is the case, update the values.
                    Else creates a new week_object with the required week number
                    """
                    existing_week = False
                    for week_object in year_object['weeks_list']:
                        if week_object['week_number'] == ticket_item.ticket.created_at.isocalendar()[1]:
                            # There's a same week number
                            if datetime.strptime(week_object['start_date'],"%d-%m-%Y").date() > ticket_item.ticket.created_at.date():
                                week_object['start_date'] = ticket_item.ticket.created_at.date().strftime("%d-%m-%Y")
                            elif datetime.strptime(week_object['end_date'],
                                                   "%d-%m-%Y").date() < ticket_item.ticket.created_at.date():
                                week_object['end_date'] = ticket_item.ticket.created_at.date().strftime("%d-%m-%Y")

                            existing_week = True
                            break

                    if not existing_week:
                        # There's a different week number
                        week_object = {
                            'week_number': ticket_item.ticket.created_at.isocalendar()[1],
                            'start_date': ticket_item.ticket.created_at.date().strftime("%d-%m-%Y"),
                            'end_date': ticket_item.ticket.created_at.date().strftime("%d-%m-%Y"),
                        }
                        year_object['weeks_list'].append(week_object)

                        # End else
            years_list.append(year_object)
            max_year -= 1
        # End while
        return json.dumps(years_list)

    def get_sales_list(self, start_dt, final_dt):
        """
        Gets the following properties for each week's day: Name, Date and Earnings
        """
        helper = Helper()
        limit_day = start_dt + timedelta(days=1)
        total_days = (final_dt - start_dt).days
        week_sales_list = []
        count = 1
        total_earnings = 0

        while count <= total_days:
            day_tickets = self.get_all_tickets().filter(ticket__created_at__range=[start_dt, limit_day])
            day_object = {
                'date': str(start_dt.date().strftime('%d-%m-%Y')),
                'day_name': None,
                'earnings': None,
                'number_day': helper.get_number_day(start_dt),
            }

            for ticket_item in day_tickets:
                for ticket_detail_item in self.get_all_tickets_details():
                    if ticket_detail_item.ticket == ticket_item.ticket:
                        total_earnings += ticket_detail_item.price

            day_object['day_name'] = helper.get_name_day(start_dt.date())
            day_object['earnings'] = str(total_earnings)

            week_sales_list.append(day_object)

            # Reset data
            limit_day += timedelta(days=1)
            start_dt += timedelta(days=1)
            total_earnings = 0
            count += 1

        return week_sales_list

    def get_sales_actual_week(self):
        """
        Gets the following properties for each week's day: Name, Date and Earnings
        """
        helper = Helper()
        week_sales_list = []
        total_earnings = 0
        days_to_count = helper.get_number_day(datetime.now())
        day_limit = days_to_count
        start_date_number = 0

        while start_date_number <= day_limit:
            day_object = {
                'date': str(helper.start_datetime(days_to_count).date().strftime('%d-%m-%Y')),
                'day_name': None,
                'earnings': None,
                'number_day': helper.get_number_day(helper.start_datetime(days_to_count).date()),
            }

            day_tickets = self.get_all_tickets().filter(
                ticket__created_at__range=[helper.start_datetime(days_to_count), helper.end_datetime(days_to_count)])

            for ticket_item in day_tickets:
                for ticket_detail_item in self.get_all_tickets_details():
                    if ticket_detail_item.ticket == ticket_item.ticket:
                        total_earnings += ticket_detail_item.price

            day_object['earnings'] = str(total_earnings)
            day_object['day_name'] = helper.get_name_day(helper.start_datetime(days_to_count).date())

            week_sales_list.append(day_object)

            # restarting counters
            days_to_count -= 1
            total_earnings = 0
            start_date_number += 1

        return json.dumps(week_sales_list)

    def get_tickets_list(self, initial_date, final_date):
        """
        :rtype: list
        :param initial_date: datetime
        :param final_date: datetime
        """
        all_tickets = self.get_all_tickets().filter(
            ticket__created_at__range=(initial_date, final_date)).order_by('-ticket__created_at')
        all_tickets_details = self.get_all_tickets_details()
        tickets_list = []
        for ticket_pos in all_tickets:

            ticket_object = {
                'id': ticket_pos.ticket.id,
                'order_number': ticket_pos.ticket.order_number,
                'created_at': datetime.strftime(ticket_pos.ticket.created_at, "%B %d, %Y, %H:%M:%S %p"),
                'cashier': ticket_pos.cashier.username,
                'ticket_details': {
                    'cartridges': [],
                    'packages': [],
                },
                'total': 0,
            }
            for ticket_detail in all_tickets_details:
                if ticket_detail.ticket == ticket_pos.ticket:
                    ticket_detail_object = {}
                    if ticket_detail.cartridge:
                        ticket_detail_object = {
                            'name': ticket_detail.cartridge.name,
                            'quantity': ticket_detail.quantity,
                            'price': float(ticket_detail.price),
                        }
                        ticket_object['ticket_details']['cartridges'].append(ticket_detail_object)
                    elif ticket_detail.package_cartridge:
                        ticket_detail_object = {
                            'name': ticket_detail.package_cartridge.name,
                            'quantity': ticket_detail.quantity,
                            'price': float(ticket_detail.price),
                        }
                        ticket_object['ticket_details']['packages'].append(ticket_detail_object)

                    ticket_object['total'] += float(ticket_detail.price)

                    try:
                        ticket_object['ticket_details'].append(ticket_detail_object)
                    except Exception as e:
                        pass
            ticket_object['total'] = str(ticket_object['total'])
            tickets_list.append(ticket_object)
        return tickets_list

    def get_new_order_number(self):
        if self.__all_tickets is None:
            self.set_all_tickets()

        order_numbers_list = []
        for ticket_pos in self.get_all_tickets():
            order_numbers_list.append(ticket_pos.ticket.order_number)

        try:
            return max(order_numbers_list) +1

        except ValueError:
            return 1
