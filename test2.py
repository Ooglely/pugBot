import discord
from discord.ext import commands
from steam import steamid
from steam.steamid import SteamID
import scrapy
from scrapy.crawler import CrawlerProcess
import json
import os
import sys
import re

process = CrawlerProcess(settings={'FEED_FORMAT': 'json', 'FEED_URI': 'output.json'})
spanID = "ContentPlaceHolder1_ContentPlaceHolder1_ContentPlaceHolder1_rptLeagues_lblLeagueName_"

class PlayerSpider(scrapy.Spider):
    name = "playerspider"
    
    def __init__(self, id = None, input = None):
        self.input = input  # steam id

    def start_requests(self):
        url = 'https://rgl.gg/Public/PlayerProfile.aspx?p=' + self.input
        yield scrapy.Request(url=url, callback=self.parse)
        
    def parse(self, response):
        for player in response.css('body'):
            yield {
                'seasons': player.css("h3").getall()
            }
            
class HistorySpider(scrapy.Spider):
    name = "historyspider"
    
    def __init__(self, input = None):
        self.input = input

    def start_requests(self):
        url = 'https://rgl.gg/Public/PlayerProfile.aspx?p=' + self.input
        yield scrapy.Request(url=url, callback=self.parse)
        
    def parse(self, response):
        for player in response.css('body'):
            yield {
                'seasons': player.css("tr > td > a::text").getall()
            }

open('output.json', 'w').close()
id = "76561198382688914"
process.crawl(HistorySpider, input = str(id))
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
        res = i.strip()
        print(res)
        seasons.append([data[0]["seasons"][count].strip(), data[0]["seasons"][count + 1].strip(), data[0]["seasons"][count + 2].strip()])
        number += 3

sixes = []
hl = []
pl = []
for i in seasons:
    if i[0].startswith("Sixes S"):
        sixes.append(i[0] + " - " + i[1] + " - " + i[2])
    if i[0].startswith("HL Season"):
        hl.append(i[0] + " - " + i[1] + " - " + i[2])
    if i[0].startswith("P7 Season"):
        pl.append(i[0] + " - " + i[1] + " - " + i[2])

print(sixes)
print(hl)
print(pl)
    
    
    

""" for item in data[0]["seasons"]:
    if item.startswith('<h3><span id="ContentPlaceHolder1_ContentPlaceHolder1_ContentPlaceHolder1'):
        mode = item.split('</strong>')[1].split('</span></h3>')[0].split(' - ')[2]
        
        if mode == "NA Traditional Sixes":
            historyLoc['6s'] = count
        if mode == "NA Highlander":
            historyLoc['hl'] = count
        if mode == "NA Prolander":
            historyLoc['pl'] = count
        
        count += 1
            
print(historyLoc)
process.crawl(PlayerSpider, id = str(id), input = historyLoc) """