# -*- coding: utf-8 -*-
import scrapy
import gc
import datetime
import urlparse

from data_fetchers.items import DataFetchersItem
from data_fetchers import utils
from lxml.html import fromstring, tostring, Element
from data_fetchers.spider import get_text
from data_fetchers.spider import Spider


class FreshFruitPortalPlusSpider(Spider):
    name = 'FreshFruitPortalPlus'
    source_crawler = "FFP_news"
    crawl_type = "news"
    version = 1
    allowed_domains = []
    start_urls = (
    )
    itemBasicURL = 'http://www.freshfruitportal.com/news/%d/%d/?country=china'
    all_urls = set()

    def parse_item(self, response):
        self.log('this is an item page! %s' % response.url)
        item = self.get_new_item(response)
        if "summary" in response.meta:
            item['json']['summary'] = response.meta['summary']
        if "self_tag" in response.meta:
            item['json']['self_tag'] = response.meta['self_tag']
        sourceurl = response.meta["source_url"]
        item['json']['title'] = get_text(''.join(response.xpath("//div[@class='single']/h3[@class='tit-pagina']").extract()).strip())
        item['json']['date'] = response.xpath("//div[@class='single']/div/span[@class='noti-fecha']/text()").extract()[0].strip()
        tags = []
        for item_tag in response.xpath(
            "//div[@class='single']/div[@class='cloud']/a[@rel='tag']"
        ):
            tagTuple = (item_tag.xpath(".//text()").extract()[0].strip(),
                        item_tag.xpath(".//@href").extract()[0].strip())
            tags.append(tagTuple)
        item['json']['tags'] = tags

        contentOriginal = response.xpath("//div[@class='single']").extract()[0]
        lxmlTree = fromstring(contentOriginal)
        deleteTitle = lxmlTree.xpath("//h3[@class='tit-pagina']")[0]
        deleteTitle.getparent().remove(deleteTitle)
        deleteDivVolver = lxmlTree.xpath("//div[@id='volver']")[0]
        deleteDivVolver.getparent().remove(deleteDivVolver)
        deleteDivJason = lxmlTree.xpath("//div[@id='jason']")[0]
        deleteDivJason.getparent().remove(deleteDivJason)
        deletePdate = lxmlTree.xpath("//span[@class='noti-fecha']")[0]
        deletePdate.getparent().remove(deletePdate)
        deleteSharedBar = lxmlTree.xpath("//div[@class='shared-bar']")[0]
        deleteSharedBar.getparent().remove(deleteSharedBar)
        for deleteDivCloud in lxmlTree.xpath("//div[@class='cloud']"):
            deleteDivCloud.getparent().remove(deleteDivCloud)
        image_infos = []
        image_urls = []
        for image in lxmlTree.xpath(
            "//div[@class='single']/descendant::img"
        ):
            image_src = urlparse.urljoin(response.url, image.xpath(".//@src")[0].encode("UTF-8").strip())
            if image.xpath(".//@alt"):
                image_alt = image.xpath(".//@alt")[0].encode("UTF-8").strip()
            elif image.xpath(".//@title"):
                image_alt = image.xpath(".//@title")[0].encode("UTF-8").strip()
            else:
                image_alt = None
            image_infos.append((image_src,image_alt))
        caption_images = {}
        for image_info in image_infos:
            image_url,image_alt = image_info
            caption_images[image_url] = (None,image_alt)
            image_urls.append(image_url)
        slide_images = []
        for slide_image_tag in response.xpath("//div[contains(@class,'flashalbum')]//a[contains(@id,'flag_pic')]"):
            image_url = urlparse.urljoin(response.url,slide_image_tag.xpath(".//@href").extract()[0].strip())
            caption_images[image_url] = (None,None)
            image_urls.append(image_url)
            slide_images.append(image_url)

        item['image_urls'] = image_urls
        item["json"]["caption_images"] = caption_images

        for wp_caption in lxmlTree.xpath("//div[@class='single']/div[contains(@class,'wp-caption')]"):
            keep_img = wp_caption.xpath(".//img")[0]
            wp_caption.addnext(keep_img)
            wp_caption.getparent().remove(wp_caption)
        if lxmlTree.xpath(".//div[contains(@class,'flashalbum')]"):
            del_slide_div = lxmlTree.xpath(".//div[contains(@class,'flashalbum')]")[0]
            for image_url in slide_images:
                img_doc = Element("img",**{"src":image_url})
                del_slide_div.addprevious(img_doc)
            del_slide_div.getparent().remove(del_slide_div)

        item['json']['content'] = tostring(
            lxmlTree.xpath("//div[@class='single']")[0],
            encoding="UTF-8")
        del lxmlTree
        item['html'] = response.body
        item["json"]["item_url"] = response.url
        htmls_path = {
            sourceurl:response.body
        }
        item["htmls_path"] = htmls_path
        item['source_url'] = sourceurl
        return item

    def parse_list(self, response):
        tag = 'news'
        self.log('this is a list page of %s! %s' % (tag, response.url))
        items = response.xpath("//div[@id='content']/table[@id='table_articulos']")
        for item in items:
            item_url = item.xpath(".//h3/a/@href").extract()[0].strip()
            if item.xpath(".//p[3]/text()"):
                item_summary = item.xpath(".//p[3]/text()").extract()[0].strip()
            else:
                item_summary = ""
            list_meta = {'self_tag': tag, 'summary': item_summary, "source_url": item_url}
            if not self.check_existance(sourceCrawler=self.source_crawler,
                                        sourceURL=item_url,
                                        items_scraped=self.items_scraped) and \
                    item_url not in self.all_urls:
                self.all_urls.add(item_url)
                yield scrapy.Request(item_url,
                                     callback=self.parse_item,
                                     dont_filter=True,
                                     meta=list_meta)
            else:
                self.log(
                    'the news of TAG(%s) has scraped already! %s'
                    % (tag, item_url))
        gc.collect()

    def _start_requests(self):
        now = datetime.datetime.now()
        url = self.itemBasicURL % (now.year, now.month)
        self.log('plus list request: %s' % url)
        yield scrapy.Request(url, callback=self.parse_list, dont_filter=True)
