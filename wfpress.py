# -*- coding: utf-8 -*-
import scrapy
import urlparse
import datetime
from data_fetchers.spider import Spider
from lxml.html import fromstring, tostring


class WesternFarmPress(Spider):
    name = 'wfpress'
    source_crawler = "wfpress"
    crawl_type = "news"
    item_parser = "parse_content"
    version = 1
    allowed_domains = ['http://westernfarmpress.com']
    start_urls = ["http://westernfarmpress.com/site-archive"]
    all_urls = set()
    # download_delay = 10

    def parse(self, response):
        month_list = response.xpath("//ul[@class=\"views-summary\"]/li/a/@href"
                                    ).extract()
        for month in month_list:
            month_url = urlparse.urljoin(response.url, month)
            if month_url:
                yield scrapy.Request(
                    month_url,
                    # 'http://westernfarmpress.com/site-archive/201503',
                    callback=self.parse_list,
                    dont_filter=True
                )

    def parse_list(self, response):

        partial_urls = response.xpath(
            "//div[@class=\"view-content\"]//div[@class=\"title\"]/a/@href"
        ).extract()
        for partial_url in partial_urls:
            article_url = urlparse.urljoin(response.url, partial_url)
            month = response.xpath(
                "//h1[@class='page-title']/text()"
            ).extract()[0].strip('Sitemap - ')
            meta = {"article_url": article_url, "month": month}
            if article_url:
                if not self.check_existance(sourceCrawler=self.source_crawler,
                                            sourceURL=article_url,
                                            items_scraped=self.items_scraped)\
                        and article_url not in self.all_urls:
                    self.all_urls.add(article_url)
                    yield scrapy.Request(
                        article_url,
                        callback=self.parse_content,
                        dont_filter=True,
                        meta=meta
                    )

        next_partial = response.xpath(
            "//ul[@class=\"pager\"]//li[@class=\"pager-next last\"]/a/@href"
        ).extract()
        if next_partial:
            next_url = urlparse.urljoin(response.url, next_partial[0])
            if next_url:
                yield scrapy.Request(
                    next_url,
                    callback=self.parse_list,
                    dont_filter=True
                )

    def parse_content(self, response):

        # filter bad content
        if response.xpath(".//div[text()='Sponsored']"):
            print "sponsored"
            return
        if response.xpath(".//div[@class='datasheet-details']"):
            print "datasheet"
            return
        if response.url == 'http://westernfarmpress.com/advertising-block':
            print "advertising"
            return
        if response.xpath("//div[contains(@class,'course_link')]"):
            print "course_link"
            return
        if response.xpath("//div[@class='event-intro clearfix']"):
            print "event"
            return
        if response.xpath("//div[@class='author-bio-area']"):
            print "author"
            return

        # list of urls
        if 'url_list' not in response.meta:
            url_list = [response.url]
        else:
            url_list = response.meta['url_list']
            url_list.append(response.url)

        # list of htmls
        html = response.body
        if 'html_list' not in response.meta:
            html_list = [html]
        else:
            html_list = response.meta['html_list']
            html_list.append(html)

        if 'content' in response.meta:
            content = response.meta['content']
        else:
            content = None

        if response.xpath("//div[@class=\"truncated-body\"]"):
            content = response.xpath("//div[@class=\"truncated-body\"]").extract()[0]
        elif response.xpath("//div[@class='node-body article-body']"):
            if content:
                content = response.meta['content'] + response.xpath(
                    "//div[@class='node-body article-body']").extract()[0]
            else:
                content = response.xpath(
                    "//div[@class='node-body article-body']").extract()[0]
        elif response.xpath("//div[@class='node-body gallery-body']"):
            content = response.xpath("//div[@class='node-body gallery-body']").extract()[0]
        elif response.xpath("//div[@class=\"node-body video-body\"]"):
            content = response.xpath("//div[@class=\"node-body video-body\"]").extract()[0]
        elif response.xpath("//div[@class='node-body blog-body']"):
            if content:
                content = response.meta['content'] + response.xpath("//div[@class='node-body blog-body']").extract()[0]
            else:
                content = response.xpath("//div[@class='node-body blog-body']").extract()[0]
            # blog_flag = True
        elif response.xpath("//div[@class='event-intro clearfix']"):
            content = response.xpath("//div[@class='event-intro clearfix']").extract()[0]
        elif response.xpath("//div[@class='node-body sponsored-body']"):
            content = response.xpath("//div[@class='node-body sponsored-body']").extract()[0]
        elif response.xpath("//div[@class='audio-control clearfix']"):
            content = response.xpath("//div[@class='node-body audio-body']").extract()[0] +\
                response.xpath("//div[@class='media-download-block']").extract()[0] +\
                response.xpath("//div[@class='thumbnail']").extract()[0]
        else:
            content = "No content was extracted from this article.\
                Please see the original source."

        # add page titles
        if content is not None:
            bulk_content = fromstring(content)
            if bulk_content is not None:
                next_title = response.xpath(
                    "//div[@class='pagination-title pagination-next title']/a/text()")
                if next_title:
                    next_title = fromstring("<h2> %s</h2>" % (next_title.extract()[0]))
                    bulk_content.append(next_title)
                    content = tostring(bulk_content, encoding='UTF-8')
        else:
            return

        # if 'html' not in item:
        #     item['html'] = response.body
        # else:
        #     item['html'] += response.body

        # if "htmls_path" not in item:
        #     item["htmls_path"] = {}

        # item["htmls_path"][response.meta['article_url']] = response.body

        # if 'json' not in item:
        #     item['json'] = {}

        have_next = response.xpath("//div[@class=\"pagination-index item-list\"]\
            //li[@class=\"pager-next last\"]/a/@href")
        if have_next:
            page_url = urlparse.urljoin(response.url, have_next.extract()[0])
            meta = {'content': content,
                    'url_list': url_list,
                    'html_list': html_list}
            print
            yield scrapy.Request(
                page_url,
                callback=self.parse_content,
                dont_filter=True,
                meta=meta
            )

        else:
            item = response.meta['item'] if 'item' in response.meta else \
                self.get_new_item(response)

            category = None
            if response.xpath(".//div[@class='breadcrumb']/a"):
                breadcrumb = response.xpath(".//div[@class='breadcrumb']/a")[-1]
                if breadcrumb:
                    category = self.get_text(breadcrumb.xpath(".//text()").extract()[0])
                    if category == u'Home':
                        category = u'Farm Press Blog'

            title = self.get_text(response.xpath(
                "//h1[contains(@class,'page-title')]"
            ).extract()[0]) if response.xpath(
                "//h1[contains(@class,'page-title')]"
            ) else "Western Farm Press"

            # date = self.get_text(response.xpath(
            #     "//div[contains(@class,\"byline-date\")]\
            #     //span[contains(@class,\"publish-date\")]"
            # ).extract()[0]) if response.xpath(
            #     "//div[contains(@class,\"byline-date\")]\
            #     //span[contains(@class,\"publish-date\")]"
            # ) else datetime.datetime.now()

            if response.xpath(
                "//div[contains(@class,\"byline-date\")]\
                //span[contains(@class,\"publish-date\")]"
            ):
                date = self.get_text(response.xpath(
                    "//div[contains(@class,\"byline-date\")]\
                    //span[contains(@class,\"publish-date\")]"
                ).extract()[0])
            elif 'month' in response.meta:
                date = response.meta['month']
            else:
                date = response.meta['date']

            author = self.get_text(response.xpath(
                "//span[@class='author-name']"
            ).extract()[0]) if response.xpath(
                "//span[@class='author-name']"
            ) else "Western Farm Press"

            p_summary = self.get_text(response.xpath(
                "//div[@class=\"summary\"]/p"
            ).extract()[0]) if response.xpath(
                "//div[@class=\"summary\"]/p"
            ) else None

            bs = response.xpath("//div[@class='summary']/ul/li")
            if len(bs) > 0:
                b_summary = ""
                # for i in range(len(bs)):
                #     if i == 0:
                #         b_summary += " <b> <p> In Brief: %s </p> \n" % self.get_text(bs[i].extract())
                #     elif i < len(bs) - 1:
                #         b_summary += " <p> %s </p> \n" % self.get_text(bs[i].extract())
                #     else:
                #         b_summary += " <p> %s </p> </b> \n" % self.get_text(bs[i].extract())

                for b in bs:
                    b_summary += "<li><b> %s </b></li>" % self.get_text(b.extract())
                    b_summary += '\n'
            else:
                b_summary = None

            summary = p_summary if p_summary else b_summary

            imgs = []
            capd_imgs = {}
            # gallery
            if response.xpath("//li[@class='pm-gal-slide']"):
                gal = response.xpath("//li[@class='pm-gal-slide']")
                for slide in gal:
                    url = slide.xpath(".//img/@src")
                    if url:
                        url = urlparse.\
                            urljoin(
                                response.url, url[0].extract()
                            )
                    imgs.append(url)
                    cap_t = slide.xpath(".//h3/text()")
                    cap_c = slide.xpath(".//p/text()")
                    if cap_t and cap_c:
                        cap = cap_t[0].extract() + ": " + cap_c[0].extract()
                    elif not cap_t and cap_c:
                        cap = cap_c.extract()[0]
                    elif cap_t and not cap_c:
                        cap = cap_t.extract()[0]
                    else:
                        cap = None
                    if slide.xpath(".//img/@title"):
                        alt_cap = slide.xpath(".//img/@title").extract()[0]
                    if alt_cap == '':
                        alt_cap = title
                    capd_imgs[url] = (cap, alt_cap)
            # top image
            elif response.xpath("//div[contains(@class,'article-image')]"):
                img = response.xpath("//div[contains(@class,'article-image')]")
                url = urlparse.urljoin(response.url, img.xpath(
                    ".//img/@src").extract()[0])
                imgs.append(url)
                cap = img.xpath(".//p/text()").extract()[0]\
                    if img.xpath(".//p/text()") else None
                alt_cap = title
                capd_imgs[url] = (cap, alt_cap)
            # article image (remaining images)
            # imgs = bulk_content.xpath('//img')
            # for img in imgs:
            #     if img.xpath("./@src"):
            #         url = img.xpath("./@src")[0]
            #     cap = None
            #     alt = title
            #     # if img.xpath("./text()"):
            #     #     cap = img.xpath("./text()").extract()[0]
            #     # else:
            #     #     cap = None
            #     # if img.xpath("./@alt"):
            #     #     alt = img.xpath("./@alt").extract()[0]
            #     # else:
            #     #     alt = title
            #     capd_imgs[url] = (cap, alt)

            item['thumb_urls'] = []
            item['image_urls'] = capd_imgs.keys()
            item['json']['caption_images'] = capd_imgs
            item['json']['title'] = title
            item['json']['date'] = date
            item['json']['author'] = author
            item['json']['categories'] = [category]
            item['json']['tags'] = []
            # item['json']['summary'] = summary

            if len(response.xpath("//h1[@class='page-title']/text()")) > 0:
                title = response.xpath("//h1[@class='page-title']/text()").extract()[0]
                item['json']['title'] = title

            # remove whitespace
            content = content.replace(u'\xa0', u' ')

            # create bulk_content
            if content is not None:
                bulk_content = fromstring(content)
            else:
                bulk_content = None

            # add images
            count = 0
            for im in imgs:
                tag = fromstring("<img src='%s'/>" % (im))
                bulk_content.insert(count, tag)
                count += 1

            # Put the summary at the beginning
            if bulk_content is not None and summary is not None:
                # begin = '<p> In Brief: %s</p>' % (summary)
                begin = '<ul><b> In Brief: %s</b></ul>' % (summary)
                bulk_content.insert(0, fromstring(begin))

            # # switch h1 title for h2 events, change date
            # if event_flag:
            #     if response.xpath("//h2/text()"):
            #         new_title = self.get_text(response.xpath("//h2/text()").extract()[0])
            #         item['json']['title'] = new_title
            #         del_nt = bulk_content.xpath("//h2")[0]
            #         del_nt.getparent().remove(del_nt)
            #     if bulk_content.xpath(".//div[@class='time-and-location']//text()"):
            #         new_date = bulk_content.xpath(".//div[@class='time-and-location']//text()")[0].split(u'\u2022')[0].strip()
            #         if len(new_date) > 2:
            #             if "-" in new_date:
            #                 year = new_date[-4:]
            #                 new_date = new_date.split('-')[0] + year
            #             item['json']['date'] = new_date

            # del all items with links to wfp
            if bulk_content.xpath("//*[contains(@href,'westernfarmpress')]"):
                intern_links = bulk_content.xpath(
                    "//*[contains(@href,'westernfarmpress')]|\
                    //*[contains(@href,'../')]")
                for intern_link in intern_links:
                    ancestors = intern_link.iterancestors()
                    for ancestor in ancestors:
                        if ancestor.tag == 'h3':
                            break
                        if ancestor.tag == 'p' or ancestor.tag == 'h6':
                            if ancestor.getparent() is not None:
                                ancestor.getparent().remove(ancestor)
                        # if ancestor.getparent().tag == 'div':
                        #     ancestor.getparent().remove(ancestor)
                        #     break

            # del rss
            if bulk_content.xpath("//*[contains(@href,'rss')]"):
                rss = bulk_content.xpath("//*[contains(@href,'rss')]")
                for s in rss:
                    s.getparent().remove(s)

            # del rel content
            if bulk_content.xpath("//div[contains(@class,'related-content')]"):
                rels = bulk_content.xpath("//div[contains(@class,'related-content')]")
                for rel in rels:
                    rel.getparent().remove(rel)

            # # del rel content
            # if bulk_content.xpath("//div[contains(@class,'related-content')]"):
            #     for rel in bulk_content.xpath(
            #             "//div[contains(@class,'related-content')]"):
            #         del_rel = rel[0]
            #         del_rel.getparent().remove(del_rel)
            # elif bulk_content.xpath("//div/p/strong/em"):
            #     rel_h = bulk_content.xpath("//div/p/strong/em/../..")[0]
            #     for sib in rel_h.itersiblings():
            #         if sib.xpath(".//strong/a/@href"):
            #             sib.getparent().remove(sib)
            #         else:
            #             break
            #     rel_h.getparent().remove(rel_h)
            # elif bulk_content.xpath("//*[contains(text(),'Blog')]"):
            #     rel_h = bulk_content.xpath("//*[contains(text(),'Blog')]")[0]
            #     for sib in rel_h.itersiblings():
            #         if sib.xpath(".//strong/a/@href"):
            #             sib.getparent().remove(sib)
            #         else:
            #             break
            #     rel_h.getparent().remove(rel_h)

            # del want access, twitter
            ps = bulk_content.xpath("//p")
            for p in ps:
                # if p.xpath(".//a/@href='http://www.westernfarmpress.com\
                #         /nltxt?intlink=nltxc'"):
                #     p.getparent().remove(p)
                # elif p.xpath(".//a/@href='https://www.westernfarmpress.com\
                #         /nltxt?intlink=nltxc'"):
                #     p.getparent().remove(p)
                # elif p.xpath(".//*[contains(text(),'newsletter')]"):
                #     p.getparent().remove(p)
                # elif p.xpath(".//a/strong[contains(text(), 'Want access')]"):
                #     p.getparent().remove(p)
                if p.xpath(".//a[contains(@href,'twitter')]"):
                    p.getparent().remove(p)
                if p.xpath(".//*[contains(text(),'More from Wes')]"):
                    p.getparent().remove(p)
                if p.xpath(".//*[contains(text(),'Blog archive')]"):
                    p.getparent().remove(p)
                if p.xpath(".//*[contains(text(),'From the \"10\"')]"):
                    p.getparent().remove(p)

            # # clean blog
            # if blog_flag:
            #     if bulk_content.xpath("//p/strong\
            #             [text()='Follow me on Twitter']"):
            #         twit = bulk_content.xpath("//p/strong\
            #             [text()='Follow me on Twitter']/..")
            #         twit.getparent().remove(twit)
            #     end = None
            if bulk_content.xpath("//p/em[contains(text(),'*Photo')]"):
                end = bulk_content.xpath(
                    "//p/em[contains(text(),'*Photo')]/..")[0]
                end.getparent().remove(end)
            #     elif bulk_content.xpath(
            #             "//p/em[contains(text(),'For more')]/.."):
            #         end = bulk_content.xpath(
            #             "//p/em[contains(text(),'For more')]/..")[0]
            #     if end:
            #         for sib in end.itersiblings():
            #             sib.getparent().remove(sib)

            if bulk_content.xpath("//p/em[contains(text(),'* Photo')]"):
                end = bulk_content.xpath(
                    "//p/em[contains(text(),'* Photo')]/..")[0]
                end.getparent().remove(end)

            item['source_url'] = url_list[0]
            item['html'] = html_list[0]
            item['htmls_path'] = dict(zip(url_list, html_list))
            item['json']['content'] = tostring(bulk_content, encoding='UTF-8')
            yield item
