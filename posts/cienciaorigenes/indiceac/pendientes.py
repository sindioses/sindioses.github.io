#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#-------------------------------------------------------------------------------
# Name:          pendientes.py
# Purpose:       Buscar páginas HTML generadas que tengan errores de generación
#                para determinar si son referencias faltantes y si es así,
#                informarlas
#
# Author:        Kilroy
#
# Created:       23/01/2016
#-------------------------------------------------------------------------------

import itertools
import os
import pprint; pp = pprint.pprint
import re
import sqlite3

from collections import Counter
from collections import defaultdict
from collections import namedtuple
from pathlib import Path
from urllib.parse import urljoin

import clize
import colorama as c
import requests
import yaml

from bs4 import BeautifulSoup as BS

BASEURL = 'http://talkorigins.org/indexcc/'
RAIZHTML = Path('.').resolve().parents[2] /  'output/cienciaorigenes/indiceac'

OK = c.Fore.GREEN + c.Style.BRIGHT
REVIEW = c.Fore.RED + c.Style.BRIGHT

ISFILE = c.Fore.WHITE + c.Back.GREEN + c.Style.BRIGHT
ISNOTFILE = c.Fore.WHITE + c.Back.RED + c.Style.BRIGHT
ISFILESRC = c.Fore.CYAN + c.Style.BRIGHT
ISNOTFILESRC = c.Fore.CYAN + c.Style.NORMAL

FN = c.Fore.YELLOW + c.Style.BRIGHT
EFN = c.Fore.WHITE + c.Style.NORMAL

OFF = c.Fore.RESET + c.Style.RESET_ALL

c.init(autoreset=True)
con = sqlite3.connect('pendientes.db')
con.row_factory = sqlite3.Row
cur = con.cursor()

BUSQUEDA = ':strong:`([a-zA-Z0-9_]+?)`'

def detectar_articulos():
    Det = namedtuple('Detectados', 'articulos pendientes errores cantidad asignados')

    a = {}
    p = defaultdict(set)
    e = defaultdict(set)
    cnt = Counter()
    cwd = Path('.').resolve()

    for arch in itertools.chain(cwd.glob('**/*.txt'), cwd.glob('**/*.rst')):
        bn = arch.stem
        a[bn] = str(arch)
        for linea in arch.read_text(encoding='utf-8').splitlines():
            lst = re.findall(BUSQUEDA, linea)
            if lst:
                p[bn].update(lst)
                for _ in lst:
                    cnt[_]+=1

    for arch in RAIZHTML.glob('**/*.html'):
        bn = arch.stem
        sopa = BS(arch.read_text(encoding='utf-8'), 'lxml')
        errores = sopa.find_all('div', class_='system-message')
        if len(errores) == 0:
            continue
        slugs = []
        for error in errores:
            txt = error.text.split('\n')[2].split(' slug')[0]
            slug = txt.encode('ascii', 'ignore').decode('ascii').upper()
            slugs.append(slug)
            cnt[slug]+=1
        e[bn].update(slugs)

    enc = set()
    ruta = 'asignados.yaml'
    with open(ruta, 'r', encoding='utf-8') as f:
        info = yaml.safe_load(f)
    asi = info['asignados']
    for k, v in asi.items():
        enc.update(v)
    return Det(a,dict(p),dict(e), cnt, enc)


def main(*, verbose:'v'=False, num:int=10):
    '''
    Buscar problemas en los archivos del Índice de Afirmaciones Creacionistas

    :param verbose: detalle de los artículos faltantes

    '''

    art = detectar_articulos()
    keys = sorted(set(art.errores.keys()) | set(art.pendientes.keys()))
    faltantes = set()
    for s in art.errores.values():
        faltantes |= s
    for s in art.pendientes.values():
        faltantes |= s
    faltantes = sorted(faltantes)

    for i, k in enumerate(keys, 1):
        pagecolor = OK
        lst = ''
        if k in art.errores:
            for e in sorted(art.errores[k]):
                isfile = e in art.articulos
                if isfile:
                    pagecolor=REVIEW
                lst += (ISFILE if isfile else ISNOTFILE) + e + ('* ' if e in art.asignados else ' ')
        if k in art.pendientes:
            for e in sorted(art.pendientes[k]):
                isfile = e in art.articulos
                if isfile:
                    pagecolor=REVIEW
                lst += (ISFILESRC if isfile else ISNOTFILESRC) + e + ('* ' if e in art.asignados else ' ')

        print('{:2d}) {}{}: {}'.format(i, pagecolor, k, lst))

    print('\nNotación:')
    print(f'- {REVIEW}error resoluble recompilando', end='')
    print(f' / {OK}sin errores resolubles')
    print(f'- {ISFILE}artículo en error existe', end='')
    print(f' / {ISNOTFILE}artículo en error no existe')
    print(f'- :doc: pasados a :strong: -> {ISFILESRC}existe / {ISNOTFILESRC}no existe')
    print(f'- *=asignado')

    lst = [_ for _ in itertools.takewhile(lambda x: x[1] > 1, art.cantidad.most_common())]
    if len(lst) > 0:
        print()
        print('Más buscados: ')
        for c in lst:
            cur.execute('select size from paginas where code = ?', (c[0],))
            reg = cur.fetchone() or ['N/A']
            print('{3}{1}:{4} {2} ({0})'.format(reg[0], *c, FN, EFN), end='| ')
        print()

    allfiles = sorted(art.articulos.keys())
    cur.executemany("update or ignore paginas set found=1 where code = ?", tuple((_, ) for _ in allfiles))
    con.commit()

    print()
    print ('Falta generar: ', end='')
    cur.execute('select substr(code, 1, 2) as section, count(*) as pend from paginas where found is null group by 1')
    for reg in cur:
        print('{}: {} - '.format(*reg), end='')
    print()
    if verbose:
        cur.execute('select code, desc, size from paginas where found is null order by 1')
        ant = ''
        for reg in cur:
            if reg[0][:2] != ant[:2]:
                print()
            ant = reg[0]
            print(f'* {reg[0]:7.7s}) {reg[1]} ({reg[2]} bytes)')

    print()
    print(f'Los {num} más breves de los artículos faltantes:')
    numreal = min(num, len(faltantes))
    params = ','.join(['?'] * numreal)
    cur.execute(f"select code, size from paginas where code in ({params}) order by size limit 10", faltantes[:numreal])

    for reg in cur:
        print('{0}{1}{3}: {2}'.format(FN, *reg, EFN), end='; ')
    print()

    exis = []
    for a in sorted(art.asignados):
        fn = '{}/{}.txt'.format(a[:2], a)
        fn2 = '{}/{}.rst'.format(a[:2], a)
        if os.path.isfile(fn) or os.path.isfile(fn2):
            exis.append(a)
    if len(exis) > 0:
        print()
        print('Artículos encargados ya disponibles: [' + '] ['.join(exis) + ']')


def load_info(arch):
    '''Cargar nombre y descripción de las páginas del índice a partir de un archivo HTML
    '''

    VERDE = c.Fore.GREEN + c.Style.BRIGHT

    def busq(tag):
        href = tag.get('href')
        return tag.name == 'a' and href and href.startswith('C')

    cur.executescript('''
    create table if not exists paginas(
        code string primary key,
        desc string,
        url string,
        size integer,
        contents text,
        found boolean
    );
    ''')

    s = requests.Session()

    with open(arch, 'r') as f:
        sopa = BS(f.read(), 'lxml')
    tags = sopa.find_all(busq)
    n = len(tags)

    COMMITNUM = 50

    for i, tag in enumerate(tags, 1):
        origurl = urljoin(BASEURL, tag.get('href'))
        slug = os.path.basename(origurl).split('.')[0]
        desc = tag.text.replace('\n', '')
        print('{:5d}/{:5d}) {} {}{}'.format(i, n, desc, VERDE, slug))
        r = s.get(origurl) #, stream=True)
        # size = int(r.headers['Content-Length'])
        text = r.text
        size = len(text)
        cur.execute('replace into paginas(code, desc, url, contents, size) values (:slug, :desc, :origurl, :text, :size)', locals())
        print('\t', origurl, slug, size)
        if i % COMMITNUM == 0:
            con.commit()
    con.commit()


def test():
    d = detectar_articulos()
    pp(d)


if __name__ == '__main__':
    clize.run(main, alt=(load_info, test))