# -*- coding: utf-8 -*-
import scrapy
import urlparse
from data_fetchers import utils
from data_fetchers.spider import Spider
# from data_fetchers.items import DataFetchersItem
from lxml.html import fromstring, tostring


class Cdfa(Spider):
    name = 'cdfa'
    source_crawler = 'cdfa'
    crawl_type = 'news'
    version = 0
    allowed_domains = ['http://cdfa.ca.gov/']
    start_urls = [
        'http://cdfa.ca.gov/exec/Public_Affairs/All_Press_Releases.html']
    all_urls = set()

    def parse(self, response):
        years = response.xpath("//ul[@id='mylist']/li/a/@href")[1:14]
        for year in years:
            year_url = urlparse.urljoin(response.url, year.extract())
            if year_url:
                yield scrapy.Request(year_url,
                                     callback=self.parse_year,
                                     dont_filter=True)

    def parse_year(self, response):
        meta = {}
        # thumb = urlparse.urljoin(response.url,response.xpath("//div[@class='welcome']//img/@src")[0].extract())
        releases = response.xpath("//td[text()='Press Release Number:']")
        for release in releases:
            number = release.xpath(
                ".//following-sibling::td/text()").extract()[0]
            date = release.xpath(
                "./../following-sibling::tr[1]/td/text()").extract()[1]
            title = release.xpath(
                "./../following-sibling::tr[2]/td/text()").extract()[1]
            url = urlparse.urljoin(response.url, release.xpath(
                "./../following-sibling::tr[3]/td//b/a/@href").extract()[0])
            meta['number'] = number
            meta['date'] = date
            meta['title'] = title
            # meta['thumb'] = thumb
            if not self.check_existance(sourceCrawler='cdfa',
                                        sourceURL=url,
                                        items_scraped=self.items_scraped)\
                    and url not in self.all_urls:
                self.all_urls.add(url)
                yield scrapy.Request(
                    url,
                    callback=self.parse_release,
                    dont_filter=True,
                    meta=meta)

    def parse_release(self, response):
        item = self.get_new_item(response)
        item['source_url'] = response.url
        item['html'] = response.body
        item["htmls_path"] = {response.url: response.body}
        item['thumb_urls'] = []  # [response.meta['thumb']]
        item['json']['date'] = response.meta['date']
        item['json']['title'] = response.meta['title']
        item['json']['number'] = response.meta['number']

        content = response.xpath(
            "//div[contains(@style,'font-size: 12px')]").extract()[0]
        lxml_content = fromstring(content)
        # remove junk
        if lxml_content.xpath(".//div[@align='center']|.//p[@align='center']"):
            thirty = lxml_content.xpath(
                ".//div[@align='center']|.//p[@align='center']")[0]
            thirty.getparent().remove(thirty)
        if lxml_content.xpath(".//div[contains(@stlye,'margine-bottom')]"):
            junk = lxml_content.xpath(
                ".//div[contains(@stlye,'margine-bottom')]")
            junk.getparent().remove()

        item['json']['content'] = tostring(lxml_content, encoding='utf-8')

        yield item
