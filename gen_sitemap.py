#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#-------------------------------------------------------------------------------
# Name:          gen_sitemap.py
# Purpose:       Generar Sitemap para sindioses.org
#
# Author:        Kilroy
#
# Created:       03/05/2016
#-------------------------------------------------------------------------------

import lxml
import os
from urllib.parse import urljoin

from lxml import etree
from lxml.builder import ElementMaker
import arrow


SITEROOT = 'http://www.sindioses.org'
NS = "http://www.sitemaps.org/schemas/sitemap/0.9"

def main():

    E = ElementMaker()
    e = E.urlset(xmlns=NS)

    oldcwd = os.getcwd()
    os.chdir('output')
    c = 0
    for raiz, dirs, archs in os.walk('.'):
        for arch in archs:
##            if c == 500:
##                break
##            c += 1

            fn = os.path.join(raiz, arch)
            if not arch.endswith('.html'):
                continue
            elif fn.startswith((r'.\index', r'.\20', r'.\categories', r'.\anillo', r'.\activismo')):
                continue
            print(fn)
            st = os.stat(fn)
            dt = arrow.get(st.st_mtime)
            url = urljoin(SITEROOT, fn[2:].replace('\\', '/'))
##            print(c, fn, url)
            eurl = E.url()
            eurl.append(E.loc(url))
            eurl.append(E.changefreq('daily'))
            eurl.append(E.priority('1.0'))
            eurl.append(E.lastmod(dt.format('YYYY-MM-DDTHH:mm:ssZZ')))
            e.append(eurl)
    os.chdir(oldcwd)

    with open('output/sitemap.xml', 'wt', encoding='UTF-8') as f:
        f.write('<?xml version="1.0" encoding="UTF-8"?>\n')
        f.write(etree.tounicode(e, pretty_print=True))

if __name__ == '__main__':
    main()