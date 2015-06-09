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
import json
import requests
from constants import *
from pprint import pprint


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





    # A table (realised through dictionary with values as 2-dim list) containing all the Objects of selected releases.

    TableObj = dict((el, [empty_field(), empty_field(), ""]) for el in
                    listFields)

    # A table (realised through dictionary with values as 2-dim list) containing all the dates (Strings)
    # of selected releases. This is the Table which is written to the DB and creates the HTML file.

    TableStr = dict((el, ['', '','']) for el in listFields)
    html_code = ''
    currentYear = datetime.datetime.now().year

    with open(json_name) as data_file:
        data_dic = json.load(data_file)


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

    def get_data_firefox(self):
        r = requests.get(self.data_dic[self.name]["link"], stream=True)

        for e in r.iter_lines():
            m = re.search(self.data_dic[self.name]["format"], e)
            if m:
                self.version = m.group(1)

                r2 = requests.get(self.data_dic[self.name]["date_link_beg"] + self.version + self.data_dic[self.name]["date_link_end"])
                for e in r2.iter_lines():
                    m2 = re.search(self.data_dic[self.name]["format2"], e)
                    if m2:
                        k = m2.group(1)
                        self.date = datetime.datetime.strptime(m2.group(1), self.data_dic[self.name]["date_format"])
                        self.TableObj[self.soft_name][self.is_official] = self
                        self.TableStr[self.soft_name][self.is_official] = self.return_date()
                        self.TableStr[self.soft_name][2] = self.data_dic[self.name]["date_link_beg"] + self.version + self.data_dic[self.name]["date_link_end"]
                        return
        raise KeyError('ERROR: No new releases were found, please change url or REGEX matching pattern')

    def get_data_ios_beta(self):
        """
        Grabs releases from official Apple's Developer's RSS.
        The method throws KeyError if it can't find any release.
        The code grabs the matching from the XML file so it can easily be changed to handle other RSS feeds.
        :return:
        None
        """

        d = feedparser.parse(self.data_dic[self.name]["link"])

        for e in d.entries:
            m = re.search(self.data_dic[self.name]["format"], e.title)
            if m:
                self.version = m.group(1)
                self.beta = m.group(2)
                self.date = \
                    datetime.datetime.fromtimestamp(mktime(e.published_parsed))
                self.TableObj[self.soft_name][self.is_official] = self
                self.TableStr[self.soft_name][self.is_official] = self.return_date()
                return
        raise KeyError('ERROR: No new releases in the rss feed, please change RSS url or REGEX matching pattern'
                       )

    def get_data_chrome_driver(self):
        try:
            link = self.data_dic[self.name]["link"]
            version = urllib2.urlopen(link).read()
            req = urllib2.Request(link)
            url_handle = urllib2.urlopen(req)
            headers = url_handle.info()

            etag = headers.getheader("ETag")
            last_modified = headers.getheader("Last-Modified")
            print(last_modified)
        except:
            raise KeyError('ERROR: Error reading version or date.')

    def get_data_apple(self):
        """
        Grabs official releases from Apple site.
        The code uses BeautifulSoup to grab the first table. The code looks for a row with the right Software.
        In case the Apple's format has changed a KeyError is thrown.
        :return:
        """

        html = urllib2.urlopen(self.data_dic[self.name]["link"]).read()
        soup = BeautifulSoup(html)
        soup.prettify()

        rows = soup.find('table').find_all('tr')
        for row in rows:
            text = row.contents[0].get_text()

            m = re.search(self.data_dic[self.name]["format"], text)
            if m:
                self.version = m.group(1)
                self.date = datetime.datetime.strptime(row.contents[4].get_text(), self.data_dic[self.name]["date_format"])

                self.TableObj[self.soft_name][self.is_official] = self
                self.TableStr[self.soft_name][self.is_official] = self.return_date()
                return

        raise KeyError('ERROR: No new releases in the Apple site, please change url or matching pattern')



    def __init__(self, name):

        self.type = self.data_dic[name]["type"]
        self.name = name
        self.soft_name = self.data_dic[name]["soft_name"]


        # Checks what type is the Object and decides which Web-Grabbing function will be called.

        if self.type == 'rss':
            self.is_official = 0
            self.get_data_ios_beta()
        elif self.type == 'html_table_apple':
            self.is_official = 1
            self.get_data_apple()
        elif self.type == 'hidden_in_html_source':
            self.is_official = 1
            self.get_data_firefox()

    @classmethod
    def generate_html(cls):
        """
        Generates the HTML file with the table. The table is created from class variable TableStr.
        """

        cls.html_code = HTML.Table(header_row=['Software',
                                   'Latest beta release',
                                   'Latest release',
                                   'Link to update if available'])
        for row in listFields:
            cls.html_code.rows.append([row, cls.TableStr[row][0],
                    cls.TableStr[row][1], ''])

        target = open(html_name, 'w')
        target.write(str(cls.html_code))
        target.close()

    @classmethod
    def load_and_compare(cls):
        """
        Loads the DB from MongoDB (If the selected Document doesn't exist we create it). Checks for changes and calls
        send_mail for every change. In the end we write back the Table to the DataBase. Due to the small maximum size
        of the Table we remove the old one and insert the new.
        :return
        True - if there was a change
        False - if there was no change
        """
        change = False
        client = MongoClient(dbURI)
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
                change = True
                cls.TableObj[i][0].send_mail()
            if cls.TableStr[i][1] != tmpdic[i][1]:
                change = True
                cls.TableObj[i][1].send_mail()

        coll.remove({})
        coll.insert(cls.TableStr)
        return change

    def send_mail(self):
        """
        Tries to send a mail in the wanted format. In case there is an error probably due to SMTP connection problem
        throws error. In the future it would be wise to write the message to a log file for future sending.
        """
        try:

            self.msg = MIMEText('')

            self.msg['Subject'] = 'SOFTWARE ALERT SYSTEM New ' \
                + (('Beta ' if not(self.is_official) else '')) + 'Release for ' \
                + self.soft_name
            self.msg['From'] = from_mail
            self.msg['To'] = to_mail

            s = smtplib.SMTP(smtp_mail)

            s.ehlo()
            s.starttls()
            s.login(smtp_user, smtp_pass)
            s.sendmail(from_mail, to_mail,
                       self.msg.as_string())
            s.quit()

        except:
            print 'ERROR: Connecting to SMTP server, Please Check connection'