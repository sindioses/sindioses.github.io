#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import pathlib

def main():
    p = pathlib.Path('.')
    archs = p.glob('**/*.rst')
    for arch in archs:
        txt = arch.read_text(encoding='utf-8')
        # normalmente faltan ``type: afirmacrea`` y ``description: ``
        cab, resto = txt.split('\n\n', 1)
        tags = {}
        lincab = cab.split('\n')
        for li in lincab:
            k, v = li.split(':', 1)
            k = k[3:]
            v = v[1:]
            tags[k] = v
        if not 'type' in tags or not 'description' in tags:
            print(arch.name)
            print(tags)
            if not 'type' in tags:
                lincab.append('.. type: afirmacrea')
            if not 'description' in tags:
                lincab.append('.. description: Respuesta a la afirmación creacionista «{}»'
                    .format(tags['title'].split(': ')[1]))
            cab = '\n'.join(lincab)
            arch.write_text(cab + "\n\n" + resto, encoding='utf-8')


if __name__ == '__main__':
    main()