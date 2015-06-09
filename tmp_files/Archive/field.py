#!/usr/bin/python
# -*- coding: utf-8 -*-
import xml.etree.ElementTree as ET
import feedparser
import re
import datetime
import HTMLParser
from bs4 import BeautifulSoup
import urllib2
import HTML
from time import mktime
from pymongo import MongoClient
from DictDiffer import DictDiffer
import smtplib
from email.mime.text import MIMEText


class empty_field(object):

    """
    A Class that might be cancelled in the future. Is used for returning empty values in the empty table entries.
    Also is the parent Class of field.
    """

    def return_date(self):
        return ''

    def send_mail(self):
        return


class field(empty_field):

    from_mail = 'test@test.com'
    to_mail = 'michael.mirkin@gmail.com'
    smtp_mail = 'smtp.gmail.com:587'
    smtp_user = 'yotamproject'
    smtp_pass = 'Tirasham'

    xml_name = 'sources.xml'
    html_name = 'info.html'
    dbURI = 'mongodb://localhost:27017/'

    # The list that contains all the enteries in the table.

    listFields = [
        'iOS',
        'Android',
        'Chrome browser for android',
        'Standard browser for android',
        'Firefox',
        'Chrome',
        'Safari',
        'IE',
        'Selenium new',
        'Selenium new python bindings for webdrivers',
        ]

    # A table (realised through dictionary with values as 2-dim list) containing all the Objects of selected releases.

    TableObj = dict((el, [empty_field(), empty_field()]) for el in
                    listFields)

    # A table (realised through dictionary with values as 2-dim list) containing all the dates (Strings)
    # of selected releases. This is the Table which is written to the DB and creates the HTML file.

    TableStr = dict((el, ['', '']) for el in listFields)
    html_code = ''
    currentYear = datetime.datetime.now().year

    # The XML tree

    tree = ET.parse(xml_name)
    root = tree.getroot()

    def return_date(self):
        """
        Returns the date: If the year is the current year it will return it in DD.MM format else it will be returned in
        DD.MM.YYYY format.

        :return:
        String date
        """

        if self.date.year == self.currentYear:
            return '{d.day}.{d.month}'.format(d=self.date)
        return '{d.day}.{d.month}.{d.year}'.format(d=self.date)

    def get_data_ios_beta(self):
        """
        Grabs releases from official Apple's Developer's RSS.
        The method throws KeyError if it can't find any release.
        The code grabs the matching from the XML file so it can easily be changed to handle other RSS feeds.
        :return:
        None
        """

        d = feedparser.parse(self.link)

        for e in d.entries:
            m = re.search(self.format, e.title)
            if m:
                self.version = m.group(1)
                self.beta = m.group(2)
                self.date = \
                    datetime.datetime.fromtimestamp(mktime(e.published_parsed))
                self.TableObj[self.soft_name][0] = self
                self.TableStr[self.soft_name][0] = self.return_date()
                return
        raise KeyError('ERROR: No new releases in the rss feed, please change RSS url or REGEX matching pattern'
                       )

    def get_data_ios(self):
        """
        Grabs official releases Data from Wikipedia page regarding iOS releases.
        The code uses BeautifulSoup to grab the first table. The code looks for the entry which is colored in green
        (This color is defined in the XML file and can be easily changed without opening the code).
        In case the Wikipedia format is changed a KeyError is thrown.
        :return:
        """

        html = urllib2.urlopen(self.link).read()
        soup = BeautifulSoup(html)
        soup.prettify()

        rows = soup.find('table').find_all('tr')
        for row in rows:
            tmp = row.find('td', {'style': 'background:' + self.color
                           + ';'})
            if tmp:
                cells = row.find_all('td')
                self.version = tmp.get_text()
                self.date = datetime.datetime.strptime(row.find('span',
                        {'class': 'bday dtstart published updated'
                        }).get_text(), '%Y-%m-%d')
                self.TableObj[self.soft_name][1] = self
                self.TableStr[self.soft_name][1] = self.return_date()
                return
        raise KeyError('ERROR: The Wikipedia format has probably changed.'
                       )

    def __init__(self, name):

        self.name = name

        # The section which parses the XML file

        xml_entry = self.root.findall("./*[@name=\'" + name + "\']")

        # We Check here for errors in the xml files or the name in the field

        if not xml_entry:
            raise KeyError('The selected value was not found')
        elif len(xml_entry) > 1:
            raise KeyError('More than one element has been found')
        self.xml_entry = xml_entry[0]
        self.type = self.xml_entry.find('type').text
        self.link = self.xml_entry.find('link').text
        self.format = \
            HTMLParser.HTMLParser().unescape(self.xml_entry.find('format'
                ).text)

        # Checks what type is the Object and decides which Web-Grabbing function will be called.

        if self.type == 'rss':
            self.is_beta = True
            self.soft_name = 'iOS'

            self.get_data_ios_beta()
        elif self.type == 'html_table_wiki':
            self.color = self.xml_entry.find('color').text

            self.is_beta = False
            self.soft_name = 'iOS'

            self.get_data_ios()

    @classmethod
    def generate_html(cls):
        """
        Generates the HTML file with the table. The table is created from class variable TableStr.
        """

        cls.html_code = HTML.Table(header_row=['Software',
                                   'Latest beta release',
                                   'Latest release',
                                   'Link to update if available'])
        for row in cls.listFields:
            cls.html_code.rows.append([row, cls.TableStr[row][0],
                    cls.TableStr[row][1], ''])

        target = open(cls.html_name, 'w')
        target.write(str(cls.html_code))
        target.close()

    @classmethod
    def load_and_compare(cls):
        """
        Loads the DB from MongoDB (If the selected Document doesn't exist we create it). Checks for changes and calls
        send_mail for every change. In the end we write back the Table to the DataBase. Due to the small maximum size
        of the Table we remove the old one and insert the new.
        """

        client = MongoClient(cls.dbURI)
        coll = client.test.work
        cur = coll.find()
        if cur.count() == 0:
            coll.insert(cls.TableStr)
            return

        tmpdic = {}
        for i in cur:
            tmpdic.update(i)
        diff = DictDiffer(tmpdic, cls.TableStr)
        for i in diff.changed():
            if cls.TableStr[i][0] != tmpdic[i][0]:
                cls.TableObj[i][0].send_mail()
            if cls.TableStr[i][1] != tmpdic[i][1]:
                cls.TableObj[i][1].send_mail()

        coll.remove({})
        coll.insert(cls.TableStr)

    def send_mail(self):
        """
        Tries to send a mail in the wanted format. In case there is an error probably due to SMTP connection problem
        throws error. In the future it would be wise to write the message to a log file for future sending.
        """
        try:

            self.msg = MIMEText('')

            self.msg['Subject'] = 'SOFTWARE ALERT SYSTEM New ' \
                + (('Beta ' if self.is_beta else ' ')) + 'Release for ' \
                + self.soft_name
            self.msg['From'] = self.from_mail
            self.msg['To'] = self.to_mail

            s = smtplib.SMTP(self.smtp_mail)

            s.ehlo()
            s.starttls()
            s.login(self.smtp_user, self.smtp_pass)
            s.sendmail(self.from_mail, self.to_mail,
                       self.msg.as_string())
            s.quit()

        except:
            print 'ERROR: Connecting to SMTP server, Please Check connection'


a = field('ios official')
b = field('ios beta')
a.generate_html()
a.load_and_compare()
print a.TableStr

			