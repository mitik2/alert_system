import tornado.httpserver
import tornado.ioloop
import tornado.log
import tornado.web
from pymongo import MongoClient
from field import field
from time import gmtime, strftime
from constants import dbURI, html_name, listFields, waiting_time_sec


class MainHandler(tornado.web.RequestHandler):
    client = MongoClient(dbURI)


    def readDB(self):
        coll = self.client.test.work
        cur = coll.find()
        if cur.count() == 0:
            raise KeyError('The DB seems to be empty')

        tmpdic = {}
        for i in cur:
            tmpdic.update(i)
        return tmpdic


    def get(self):
        TableStr = self.readDB()
        self.render(html_name, TableStr=TableStr, listFields=listFields)




application = tornado.web.Application([
    (r"/", MainHandler),
])

def check_updates():
    print(strftime("%Y-%m-%d, %H:%M:%S: ", gmtime()) + "Update is now running")
    a = field('ios official')
    b = field('ios beta')
    c = field("firefox official")
    d = field("safari official")
    if field.load_and_compare():
        print(strftime("%Y-%m-%d, %H:%M:%S: ", gmtime()) + "End of update: There was an update\n")
    else:
        print(strftime("%Y-%m-%d, %H:%M:%S: ", gmtime()) + "End of update: No update\n")




if __name__ == "__main__":

    application.listen(8888)

    check_updates()
    task = tornado.ioloop.PeriodicCallback(check_updates, waiting_time_sec*1000)
    task.start()
    tornado.ioloop.IOLoop.instance().start()