import scrapy
from scrapy.crawler import CrawlerProcess
import sys
import json

process = CrawlerProcess(settings={'FEED_FORMAT': 'json', 'FEED_URI': 'output.json'})

class PlayerSpider(scrapy.Spider):
    name = "PlayerSpider"
    
    def __init__(self, input = None):
        self.input = input  # steam id

    def start_requests(self):
        url = 'https://rgl.gg/Public/PlayerProfile.aspx?p=' + self.input
        yield scrapy.Request(url=url, callback=self.parse)
        
    def parse(self, response):
        for player in response.css('body'):
            yield {
                'name': response.xpath("//*[@id='ContentPlaceHolder1_ContentPlaceHolder1_ContentPlaceHolder1_lblPlayerName']/descendant-or-self::*/text()").get(),
                'pfp': player.css("img#ContentPlaceHolder1_ContentPlaceHolder1_ContentPlaceHolder1_imgProfileImage").xpath("@src").get(),
                'seasons': player.css("tr > td > a::text").getall()
            }

def rglSearch(id):
    process.crawl(PlayerSpider, input = str(id))
    if "twisted.internet.reactor" in sys.modules:
        del sys.modules["twisted.internet.reactor"]
    process.start()
    
    f = open('output.json')
    data = json.load(f)
    
    number = 0
    seasons = []
    for count, i in enumerate(data[0]['seasons']):
        if i.strip() == "":
            del data[0]['seasons'][count]
            
    for count, i in enumerate(data[0]["seasons"]):
        if count == number:
            seasons.append([data[0]["seasons"][count].strip(), data[0]["seasons"][count + 1].strip(), data[0]["seasons"][count + 2].strip()])
            number += 3
            
    name = data[0]['name']
    pfp = data[0]['pfp']
            
    sixes = ""
    hl = ""
    pl = ""
    for i in seasons:
        if i[0].startswith("Sixes S"):
            sixes += i[0] + " - " + i[1] + " - " + i[2] + "\n"
        if i[0].startswith("HL Season"):
            hl += i[0] + " - " + i[1] + " - " + i[2] + "\n"
        if i[0].startswith("P7 Season"):
            pl += i[0] + " - " + i[1] + " - " + i[2] + "\n"
    
    if "twisted.internet.reactor" in sys.modules:
        del sys.modules["twisted.internet.reactor"]
    
    return [name, pfp, sixes, hl, pl]

