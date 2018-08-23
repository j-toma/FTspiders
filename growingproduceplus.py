# -*- coding: utf-8 -*-
import scrapy
import gc
import datetime
import urlparse
from data_fetchers.items import DataFetchersItem
from data_fetchers import utils
from lxml.html import fromstring, tostring
from data_fetchers.spider import Spider


class GrowingProducePlusSpider(Spider):
    # scrapy crawl GrowingProducePlus -a reparse=hh --loglevel=ERROR
    name = 'GrowingProducePlus'
    source_crawler = 'growing_produce'
    crawl_type = 'news'
    version = 1
    allowed_domains = []
    start_urls = (
        'http://www.growingproduce.com',
        'http://www.growingproduce.com/vegetables',
        'http://www.growingproduce.com/fruits',
        'http://www.growingproduce.com/nuts',
        'http://www.growingproduce.com/citrus',
    )
    has_scraped_uris = set()

    def parse_item(self, response):
        self.log('this is an item page! %s' % response.url)
        if "jump" not in response.meta:
            html = utils.decode(response.body)
            response.meta["page_html"]=html
            item = self.get_new_item(response)
            item["htmls_path"] = {}
            item["htmls_path"][response.meta['source_url']] = html
            json = item["json"]
            json['item_url'] = response.url

            if 'category' in response.meta:
                category = response.meta['category']
                json['category'] = category

            if response.xpath("//h1[contains(@class,'title')]"):
                json['title'] = response.xpath("//h1[contains(@class,'title')]/text()").extract()[0].strip()
            else:
                json['title'] = response.meta['title']

            json['date'] = response.meta['date']
            json['excerpt'] = response.meta['excerpt']
            thumb_urls = []
            if 'thumb_urls' in response.meta:
                thumb_urls += response.meta['thumb_urls']
            item['thumb_urls'] = thumb_urls

            tags = []
            for item_tag in response.xpath("//section[@class='tags']/span[@itemprop='keywords']/a[@rel='tag']"):
                tagTuple = (item_tag.xpath(".//text()").extract()[0].strip(), item_tag.xpath(".//@href").extract()[0].strip())
                tags.append(tagTuple)
            json['tags'] = tags
            if response.xpath("//div[contains(@class,'date-author-wrap')]/descendant::a[@rel='author']"):
                json['author'] = response.xpath("//div[contains(@class,'date-author-wrap')]/descendant::a[@rel='author']/span/text()").extract()[0].strip()
        else:
            json=response.meta["json"]
            item=response.meta["item"]
            item["htmls_path"][response.meta["sourceurl"]] = utils.decode(response.body)
        summaryOriginal = "".join(response.xpath("//section[@class='body']").extract()).strip()
        lxmlTree = fromstring(summaryOriginal)
        image_urls = []
        caption_images = {}
        blackouts=lxmlTree.xpath("//div[contains(@class,'blackout-gallery')]")
        for blackout in blackouts:
            image_divs=blackout.xpath(".//div[@class='image-data']")
            for image_div in image_divs:
                image_url=image_div.xpath(".//div[@class='data-urls']/meta/@content")[0]
                image=urlparse.urljoin(response.url,image_url.encode("UTF-8"))
                width=image_div.xpath(".//div[@class='data-urls']/meta/@data-width")[0].encode("UTF-8")
                height=image_div.xpath(".//div[@class='data-urls']/meta/@data-height")[0].encode("UTF-8")
                image_urls.append(image)
                img="<img src='%s' width='%s' height='%s' />" % (image,width,height)
                figcaption="<figcaption>%s</figcaption>" % image_div.xpath(".//meta[@itemprop='caption']/@content")[0].encode("UTF-8")
                caption_images[image] = (figcaption,None)
                blackout.addnext(fromstring(img))
            blackout.getparent().remove(blackout)

        for url in lxmlTree.xpath("//section[@class='body']/p/img[@src]/@src"):
            image_url=url.encode("UTF-8")
            if image_url not in image_urls:
                image_urls += [image_url]
                caption_images[image_url] = (None,None)

        for figure in lxmlTree.xpath("//section[@class='body']/figure"):
            image_url = figure.xpath(".//img[@src]/@src")[0].encode("UTF-8")
            desc = tostring(figure.xpath(".//figcaption[contains(@class,'wp-caption-text')]")[0], encoding="UTF-8")
            if image_url not in image_urls:
                image_urls += [image_url]
                caption_images[image_url] = (desc,None)
            keep_img = figure.xpath(".//img[@src]")[0]
            figure.addnext(keep_img)
            figure.getparent().remove(figure)

        section_start="<section class=\"body\" itemprop=\"articleBody\">"
        section_end="</section>"
        content=tostring(lxmlTree,encoding="UTF-8").replace(section_start,"").replace(section_end,"")
        if "jump" not in response.meta:
            item['image_urls'] = image_urls
            json["caption_images"] = caption_images
            json['content']=section_start
            json['content'] = "".join([json['content'],content])
        else:
            item['image_urls']=response.meta["item"]["image_urls"]+image_urls
            json["caption_images"] = dict(response.meta["json"]["caption_images"], **caption_images)
            json['content']="".join([response.meta["json"]["content"],content])

        pages=response.xpath("//section[@class='body']/following-sibling::p[starts-with(.,'Pages')]/a/text()")
        if pages:
            if "max_page" not in response.meta:
                max_page=int(pages.extract()[len(pages.extract())-1])
                jump=True
                next_page=2

            else:
                max_page=response.meta["max_page"]
                jump=response.meta["jump"]
                next_page=response.meta["next_page"]+1
            param=response.meta

            if next_page<=max_page:
                param["item"]=item
                param["json"]=json
                param["max_page"]=max_page
                param["next_page"]=next_page
                param["jump"]=jump
                next_url=response.meta['source_url']+str(next_page)+"/"
                param["sourceurl"]=next_url
                yield scrapy.Request(next_url, callback=self.parse_item, dont_filter=True, meta=param)
            else:
                jump=False
        if not pages or not jump:
            json['content'] = "".join([json['content'],"\n</section>"])
            item['json'] = json
            try:
                item['html'] = html
            except UnboundLocalError:
                item['html'] = response.meta["page_html"]
            item['source_url'] = response.meta['source_url']
            yield item

    def parse_list(self, response):
        self.log('this is a latest list page: %s' % response.url)
        listItems = response.xpath("//div[@class='tertiary column adCheck']/div[@class='column-content text-center']/div[contains(@class,'latest')]")
        for listItem in listItems:
            param = {}
            listItemUrl = ''
            if listItem.xpath(".//div[@class='image']"):
                param['thumb_urls'] = [urlparse.urljoin(response.url,listItem.xpath(".//div[@class='image']/a/img/@src").extract()[0].strip())]
                param['category'] = listItem.xpath(".//div[@class='image']/div[contains(@class,'category-tag')]/a/text()").extract()[0].strip()
            if listItem.xpath(".//div[@class='meta clear']"):
                listItemUrl = listItem.xpath(".//div[@class='meta clear']/a[contains(@class,'title')]/@href").extract()[0].strip()
                param['title'] = listItem.xpath(".//div[@class='meta clear']/a[contains(@class,'title')]/text()").extract()[0].strip()
                param['date'] = listItem.xpath(".//div[@class='meta clear']/div[@class='date']/text()").extract()[0].strip()
                param['excerpt'] = listItem.xpath(".//div[@class='meta clear']/div[@class='excerpt']/text()").extract()[0].strip()
                param['source_url'] = listItemUrl
            if not self.check_existance(sourceCrawler=self.source_crawler,
                                        sourceURL=listItemUrl,
                                        items_scraped=self.items_scraped) and listItemUrl not in self.has_scraped_uris:
                self.has_scraped_uris.add(listItemUrl)
                yield scrapy.Request(listItemUrl, callback=self.parse_item, dont_filter=True, meta=param)
            else:
                self.log('the item has scraped already! %s' % listItemUrl)
        gc.collect()

    def parse(self, response):
        url = response.url
        self.log('this is a latest page! %s' % url)
        yield scrapy.Request(url, callback=self.parse_list, dont_filter=True)
        gc.collect()
