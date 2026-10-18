"""Draw paper-style structure diagrams from a small JSON scene. Requires Pillow."""
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont
from html import escape
import math, json, argparse

BASE = None
CUSTOM_FONT = None

def get_font(size, bold=False):
    candidates = [CUSTOM_FONT]
    candidates += (['C:/Windows/Fonts/timesbd.ttf', '/usr/share/fonts/truetype/dejavu/DejaVuSerif-Bold.ttf', '/System/Library/Fonts/Supplemental/Times New Roman Bold.ttf'] if bold else ['C:/Windows/Fonts/times.ttf', '/usr/share/fonts/truetype/dejavu/DejaVuSerif.ttf', '/System/Library/Fonts/Supplemental/Times New Roman.ttf'])
    for path in candidates:
        if path and Path(path).is_file():
            return ImageFont.truetype(path, round(size*2))
    raise RuntimeError('No font found. Supply --font with an installed font file.')

C = dict(bg='#f3f3f4', norm='#f4f4ce', kda='#fff1dc', mla='#e9baba', moe='#ccebf4', linear='#d7ebd7', latent='#e5e3ef')

class Diagram:
    def __init__(self,w,h,title):
        self.w,self.h=w,h
        self.im=Image.new('RGB',(w*2,h*2),'white'); self.d=ImageDraw.Draw(self.im)
        self.svg=[f'<svg xmlns="http://www.w3.org/2000/svg" width="{w}" height="{h}" viewBox="0 0 {w} {h}"><rect width="100%" height="100%" fill="white"/>']
        self.text(w/2,35,title,27,bold=True)
    def text(self,x,y,t,size=22,bold=False):
        font=get_font(size, bold)
        self.d.text((x*2,y*2),t,font=font,anchor='mm',fill='black')
        self.svg.append(f'<text x="{x}" y="{y}" dominant-baseline="central" text-anchor="middle" font-family="Times New Roman,serif" font-size="{size}" font-weight="{700 if bold else 400}">{escape(t)}</text>')
    def box(self,x,y,w,h,t='',fill='bg',size=22,r=9):
        color=C.get(fill,fill)
        self.d.rounded_rectangle((x*2,y*2,(x+w)*2,(y+h)*2),radius=r*2,fill=color,outline='black',width=3)
        self.svg.append(f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="{r}" fill="{color}" stroke="black" stroke-width="1.5"/>')
        if t:self.text(x+w/2,y+h/2,t,size)
    def line(self,pts,arrow=False,dash=False):
        if dash:
            for (x1,y1),(x2,y2) in zip(pts,pts[1:]):
                length=math.hypot(x2-x1,y2-y1)
                for p in range(0,int(length),12):
                    a=p/max(length,1); b=min(p+7,length)/max(length,1)
                    self.d.line(((x1+(x2-x1)*a)*2,(y1+(y2-y1)*a)*2,(x1+(x2-x1)*b)*2,(y1+(y2-y1)*b)*2),fill='black',width=3)
        else:self.d.line([(x*2,y*2) for x,y in pts],fill='black',width=3,joint='curve')
        self.svg.append('<polyline points="'+' '.join(f'{x},{y}' for x,y in pts)+'" fill="none" stroke="black" stroke-width="1.5"'+(' stroke-dasharray="7 5"' if dash else '')+'/>')
        if arrow:
            x,y=pts[-1]; a=math.atan2(y-pts[-2][1],x-pts[-2][0]); tri=[(x,y),(x-11*math.cos(a)+4*math.sin(a),y-11*math.sin(a)-4*math.cos(a)),(x-11*math.cos(a)-4*math.sin(a),y-11*math.sin(a)+4*math.cos(a))]
            self.d.polygon([(a*2,b*2) for a,b in tri],fill='black')
            self.svg.append('<polygon points="'+' '.join(f'{a},{b}' for a,b in tri)+'" fill="black"/>')
    def circ(self,x,y,t='+'):
        self.d.ellipse(((x-9)*2,(y-9)*2,(x+9)*2,(y+9)*2),fill='white',outline='black',width=3)
        self.svg.append(f'<circle cx="{x}" cy="{y}" r="9" fill="white" stroke="black" stroke-width="1.5"/>')
        self.text(x,y,t,20)
    def save(self,name):
        self.im.save(BASE/(name+'.png'))
        (BASE/(name+'.svg')).write_text(''.join(self.svg)+'</svg>',encoding='utf-8')


def main():
    global BASE, CUSTOM_FONT
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('scene', type=Path)
    parser.add_argument('--output-dir', required=True, type=Path)
    parser.add_argument('--name', default='structure')
    parser.add_argument('--font', type=Path)
    args = parser.parse_args()
    if Path(args.name).name != args.name or args.name in ('', '.', '..'):
        parser.error('--name must be a filename stem without directories')
    BASE = args.output_dir
    BASE.mkdir(parents=True, exist_ok=True)
    CUSTOM_FONT = str(args.font) if args.font else None
    scene = json.loads(args.scene.read_text(encoding='utf-8-sig'))
    if scene['width'] <= 0 or scene['height'] <= 0:
        raise ValueError('Canvas dimensions must be positive')
    d = Diagram(scene['width'], scene['height'], scene.get('title',''))
    for shape in scene['shapes']:
        s = dict(shape)
        kind = s.pop('type')
        label = s.pop('label', '')
        if kind == 'box':
            if s['w'] <= 0 or s['h'] <= 0 or min(s['x'],s['y']) < 0 or s['x']+s['w'] > scene['width'] or s['y']+s['h'] > scene['height']:
                raise ValueError('Box is outside the canvas or has invalid dimensions')
            d.box(t=label, **s)
        elif kind == 'text':
            d.text(t=label, **s)
        elif kind == 'line':
            points = s.pop('points')
            if len(points) < 2 or points[-1] == points[-2]:
                raise ValueError('Line needs at least two points and a nonzero final segment')
            d.line(pts=points, **s)
        elif kind == 'circle':
            d.circ(t=label or '+', **s)
        else:
            raise ValueError(f'Unknown shape type: {kind}')
    d.save(args.name)
    print(BASE / (args.name + '.png'))
    print(BASE / (args.name + '.svg'))

if __name__ == '__main__':
    main()
