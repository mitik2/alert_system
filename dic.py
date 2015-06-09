
"""
dic1 = {
    "type": "rss",
    "link": "https://developer.apple.com/news/rss/news.rss",
    "format": "iOS\\s(.+?)\\sbeta\\s(.+?)\\s+."
}

dic2 = {
    "type": "html_table_wiki",
    "link": "http://en.wikipedia.org/wiki/History_of_iOS",
    "format": "background:\\#3d4.+?<b>(.+?)<\\/b>.+?td>.*?<td>.*?<td>(\\w+).+?;([0-9]+?).+?([0-9]+?)<",
    "color": "#3d4"
}

dic = {"ios beta":dic1,"ios official":dic2}

import json
with open('data.json', 'w') as fp:
    json.dump(dic, fp,indent=4, sort_keys=True)
"""
import json
with open("sources.json") as data_file:
    data_dic = json.load(data_file)

print ("sdad")