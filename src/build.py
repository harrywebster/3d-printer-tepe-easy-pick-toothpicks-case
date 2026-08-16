# SPDX-License-Identifier: CERN-OHL-S-2.0
# Copyright (C) 2026 Harry Webster
# Source location: https://github.com/harrywebster/3d-printer-tepe-easy-pick-toothpicks-case
"""Regenerate every deliverable from one geometry module.

    python3 src/build.py geom14 v14        # -> build/v14/
    EASYPICK_OUT=somewhere python3 src/build.py geom14 v14

Normally driven by `make v14`, which runs this and then ships the result.

Keeps the views, the schematic and the exported files locked to the same
model — no more hand-edited import lines drifting apart.
"""
import sys, os, zipfile, importlib
import numpy as np, matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.patches import Polygon as MPoly
from shapely.geometry import Polygon as SPoly
from shapely.ops import unary_union
import trimesh, render

# Where the deliverables land. Overridable so the build is not tied to one
# machine's layout; the Makefile points it at build/<tag>/.
OUT = os.path.join(os.environ.get('EASYPICK_OUT', 'build'), '')
CASE_C, LID_C = (0.93, 0.93, 0.94), (0.95, 0.45, 0.10)
WHITE, ORANGE = '#FFFFFF', '#FF6A13'
INK, HID, FILL = '#1b1f24', '#8a949e', '#eef1f4'


# ----------------------------------------------------------------- views
def views(g, case, lid, tag):
    open_lid = lid.copy(); open_lid.apply_translation([0, g.out_l/2, 0])
    off_lid = lid.copy(); off_lid.apply_translation([0, 0, 26])
    spec = [
        ('Three-quarter, closed', [(case, CASE_C), (lid, LID_C)], -52, 28),
        ('Opposite corner',       [(case, CASE_C), (lid, LID_C)], 128, 26),
        ('Plan',                  [(case, CASE_C), (lid, LID_C)], -90, 88),
        ('Mouth end',             [(case, CASE_C), (lid, LID_C)], -90, 14),
        ('Side elevation',        [(case, CASE_C), (lid, LID_C)],   0, 16),
        ('Half open',             [(case, CASE_C), (open_lid, LID_C)], -58, 34),
        ('Lid lifted',            [(case, CASE_C), (off_lid, LID_C)], -60, 24),
        ('Underside',             [(case, CASE_C), (lid, LID_C)], -52, -34),
    ]
    imgs = [(t, render.trim(render.render(it, azim=a, elev=e, W=760, H=620)))
            for t, it, a, e in spec]
    fig = plt.figure(figsize=(11, 13.4), dpi=150, facecolor='white')
    gs = fig.add_gridspec(4, 2, hspace=0.13, wspace=0.04,
                          left=0.02, right=0.98, top=0.935, bottom=0.02)
    for i, (t, img) in enumerate(imgs):
        ax = fig.add_subplot(gs[i // 2, i % 2]); ax.imshow(img); ax.axis('off')
        ax.set_title(t, fontsize=11, weight='bold', color='#222', pad=4)
    fig.suptitle('EasyPick case — %.1f × %.1f × %.1f mm'
                 % (g.out_w, g.out_l, g.out_h),
                 fontsize=15, weight='bold', color='#111', y=0.965)
    fig.text(0.5, 0.005, 'PLA Basic White body, PLA Basic Orange lid.',
             ha='center', fontsize=9, color='#666')
    p = OUT + 'easypick-case-%s-views.png' % tag
    fig.savefig(p, bbox_inches='tight', facecolor='white'); plt.close(fig)
    return p


# ------------------------------------------------------------- schematic
def _sil(mesh, i, j):
    tris = mesh.vertices[mesh.faces][:, :, [i, j]]
    polys = [SPoly(t) for t in tris
             if abs((t[1,0]-t[0,0])*(t[2,1]-t[0,1]) - (t[1,1]-t[0,1])*(t[2,0]-t[0,0])) > 1e-9]
    return unary_union(polys).buffer(0.002).buffer(-0.002)

def _draw(ax, shape, fc=FILL, ec=INK, lw=1.2, z=2):
    for p in (shape.geoms if hasattr(shape, 'geoms') else [shape]):
        ax.add_patch(MPoly(np.array(p.exterior.coords), closed=True,
                           fc=fc, ec=ec, lw=lw, zorder=z))
        for hole in p.interiors:
            ax.add_patch(MPoly(np.array(hole.coords), closed=True,
                               fc='white', ec=ec, lw=lw*0.8, zorder=z+1))

def _dim(ax, p0, p1, text, off=0, vert=False, fs=8.5):
    p0, p1 = np.array(p0, float), np.array(p1, float)
    n = np.array([1.0, 0]) if vert else np.array([0, 1.0])
    a, b = p0 + n*off, p1 + n*off
    ax.annotate('', xy=a, xytext=b,
                arrowprops=dict(arrowstyle='<->', color='#4a5560', lw=0.9))
    for p, q in ((p0, a), (p1, b)):
        ax.plot([p[0], q[0]], [p[1], q[1]], color='#b6bec6', lw=0.6, zorder=1)
    m = (a + b) / 2
    ax.text(m[0] + (0.9 if vert else 0), m[1] + (0 if vert else 1.2), text,
            ha='left' if vert else 'center', va='center' if vert else 'bottom',
            fontsize=fs, color='#2a333c')

def _sec(mesh, normal, origin, basis):
    s = mesh.section(plane_origin=origin, plane_normal=normal)
    p, _ = s.to_2D(to_2D=basis)
    return p

LONG = np.array([[0,1,0,0],[0,0,1,0],[1,0,0,0],[0,0,0,1.]])
CROSS = np.array([[1,0,0,0],[0,0,1,0],[0,-1,0,0],[0,0,0,1.]])

def schematic(g, case, lid, tag):
    fig = plt.figure(figsize=(11.5, 13.4), dpi=160, facecolor='white')
    gs = fig.add_gridspec(3, 2, height_ratios=[1.15, 0.95, 0.95],
                          hspace=0.05, wspace=0.06,
                          left=0.05, right=0.96, top=0.915, bottom=0.045)
    lab = dict(fontsize=8, color='#2a333c',
               arrowprops=dict(arrowstyle='->', color='#6b7680', lw=0.8))

    ax = fig.add_subplot(gs[0, 0])
    _draw(ax, _sil(case, 0, 1)); _draw(ax, _sil(lid, 0, 1), fc='none', ec=HID, lw=0.9, z=4)
    _dim(ax, (-g.out_w/2, g.out_l/2), (g.out_w/2, g.out_l/2), '%.1f' % g.out_w, off=5)
    _dim(ax, (g.out_w/2, -g.out_l/2), (g.out_w/2, g.out_l/2), '%.1f' % g.out_l, off=6, vert=True)
    ax.set_title('Plan', fontsize=11.5, weight='bold', color=INK)

    ax2 = fig.add_subplot(gs[0, 1])
    _draw(ax2, _sil(case, 0, 2)); _draw(ax2, _sil(lid, 0, 2), fc='none', ec=HID, lw=0.9, z=4)
    _dim(ax2, (-g.out_w/2, g.out_h), (g.out_w/2, g.out_h), '%.1f' % g.out_w, off=5)
    _dim(ax2, (g.out_w/2, 0), (g.out_w/2, g.out_h), '%.1f' % g.out_h, off=6, vert=True)
    ax2.set_title('Elevation — mouth end', fontsize=11.5, weight='bold', color=INK)

    ax3 = fig.add_subplot(gs[1, 0])
    _draw(ax3, _sil(case, 1, 2)); _draw(ax3, _sil(lid, 1, 2), fc='none', ec=HID, lw=0.9, z=4)
    _dim(ax3, (-g.out_l/2, g.out_h), (g.out_l/2, g.out_h), '%.1f' % g.out_l, off=5)
    _dim(ax3, (g.out_l/2, 0), (g.out_l/2, g.out_h), '%.1f' % g.out_h, off=6, vert=True)
    ax3.set_title('Side elevation', fontsize=11.5, weight='bold', color=INK)

    ax4 = fig.add_subplot(gs[1, 1])
    for m, fc in ((case, '#cfd7de'), (lid, '#f6b27a')):
        for poly in _sec(m, [1, 0, 0], [0, 0, 0], LONG).polygons_full:
            ax4.add_patch(MPoly(np.array(poly.exterior.coords), closed=True,
                                fc=fc, ec=INK, lw=1.1, zorder=2))
    _dim(ax4, (-g.int_l/2, g.floor_t), (g.int_l/2, g.floor_t), 'cavity %.0f' % g.int_l, off=-5)
    _dim(ax4, (-g.out_l/2 - 3, g.floor_t), (-g.out_l/2 - 3, g.floor_t + g.int_h),
         '%.0f' % g.int_h, off=-3, vert=True)
    ax4.annotate('wall %.1f' % g.wall, xy=(-g.out_l/2 + 1.7, g.out_h*0.55),
                 xytext=(-g.out_l/2 - 24, g.out_h*0.72), **lab)
    ax4.annotate('floor %.1f' % g.floor_t, xy=(-6, g.floor_t/2), xytext=(-30, -9), **lab)
    ax4.annotate('lid %.1f + %.1f boss' % (g.lid_t, g.lip), xy=(-8, g.lid_z + 2.4),
                 xytext=(-40, g.out_h + 9), **lab)
    if getattr(g, 'HAS_CATCH', True):
        ax4.annotate('catch %.1f on a %.1f strip' % (g.det_h, g.tongue_t),
                     xy=(g.y_end, g.shelf_z + 0.4), xytext=(-2, g.out_h + 11), **lab)
    else:
        ax4.annotate('lid held by the rails alone — no catch',
                     xy=(g.y_end, g.shelf_z + 0.4), xytext=(-8, g.out_h + 11), **lab)
    ax4.annotate('rail %.1f, clearance %.2f' % (g.rail, g.clr),
                 xy=(-g.int_l/2 - 1.2, g.lid_z + 1.2),
                 xytext=(-g.out_l/2 - 26, g.lid_z - 6), **lab)
    ax4.set_xlim(-g.out_l/2 - 30, g.out_l/2 + 12); ax4.set_ylim(-14, g.out_h + 20)
    ax4.set_title('Section on the centreline', fontsize=11.5, weight='bold', color=INK, pad=10)

    ax5 = fig.add_subplot(gs[2, :])
    for m, fc in ((case, '#cfd7de'), (lid, '#f6b27a')):
        for poly in _sec(m, [0, 1, 0], [0, 0, 0], CROSS).polygons_full:
            ax5.add_patch(MPoly(np.array(poly.exterior.coords), closed=True,
                                fc=fc, ec=INK, lw=1.1, zorder=2))
    _dim(ax5, (-g.int_w/2, g.floor_t - 1.2), (g.int_w/2, g.floor_t - 1.2),
         'internal opening %.0f' % g.int_w, off=-4)
    _dim(ax5, (-g.out_w/2 - 4, g.floor_t), (-g.out_w/2 - 4, g.floor_t + g.int_h),
         '%.0f' % g.int_h, off=-3, vert=True)
    _dim(ax5, (-g.out_w/2, g.out_h + 3), (g.out_w/2, g.out_h + 3), '%.1f' % g.out_w, off=2)
    ax5.annotate('lid tucks %.1f into each wall\nunder a %.1f lip' % (g.rail, g.lip),
                 xy=(-g.int_w/2 - 0.8, g.lid_z + 1.2),
                 xytext=(-g.out_w/2 - 22, g.out_h + 7), **lab)
    ax5.annotate('%.2f clearance all round' % g.clr, xy=(g.int_w/2 + 0.8, g.lid_z + 0.4),
                 xytext=(g.out_w/2 + 4, g.lid_z + 9), **lab)
    ax5.annotate('wall %.1f, uniform on the\nflats and the diagonals' % g.wall,
                 xy=(g.out_w/2 - 1.7, g.out_h*0.45),
                 xytext=(g.out_w/2 + 4, g.out_h*0.30), **lab)
    ax5.set_xlim(-g.out_w/2 - 28, g.out_w/2 + 30); ax5.set_ylim(-7, g.out_h + 16)
    ax5.set_title('Transverse section — the internal opening', fontsize=11.5,
                  weight='bold', color=INK, pad=8)

    for a in (ax, ax2, ax3):
        a.set_aspect('equal'); a.axis('off'); a.margins(0.14)
    for a in (ax4, ax5):
        a.set_aspect('equal'); a.axis('off')

    fig.suptitle('EasyPick case — general arrangement', fontsize=15.5,
                 weight='bold', color='#111', y=0.975)
    fig.text(0.5, 0.008, 'All dimensions in millimetres. Grey outline = lid position. '
             'Cavity %.0f × %.0f × %.0f.' % (g.int_w, g.int_l, g.int_h),
             ha='center', fontsize=9, color='#666')
    p = OUT + 'easypick-case-%s-schematic.png' % tag
    fig.savefig(p, bbox_inches='tight', facecolor='white'); plt.close(fig)
    return p


# ---------------------------------------------------------------- export
NS = 'http://schemas.microsoft.com/3dmanufacturing/core/2015/02'

def _obj(mesh, oid, name, pindex):
    v = ''.join('<vertex x="%.4f" y="%.4f" z="%.4f"/>' % tuple(p) for p in mesh.vertices)
    t = ''.join('<triangle v1="%d" v2="%d" v3="%d"/>' % tuple(f) for f in mesh.faces)
    return ('<object id="%d" type="model" name="%s" pid="10" pindex="%d">'
            '<mesh><vertices>%s</vertices><triangles>%s</triangles></mesh></object>'
            % (oid, name, pindex, v, t))

def export(g, case, lid, tag):
    c, l = case.copy(), lid.copy()
    for m, dx in ((c, -33), (l, 33)):
        m.apply_translation([0, 0, -m.bounds[0][2]])
        m.apply_translation([dx, 0, 0])
        m.merge_vertices(); m.fix_normals()
    stls = []
    for m, n in ((c, 'case'), (l, 'lid')):
        p = OUT + 'easypick-%s-%s.stl' % (n, tag)
        m.export(p); stls.append(p)

    model = ('<?xml version="1.0" encoding="UTF-8"?>\n<model unit="millimeter" '
             'xml:lang="en-US" xmlns="%s">\n<metadata name="Title">EasyPick case %s</metadata>\n'
             '<resources><basematerials id="10">'
             '<base name="PLA Basic White" displaycolor="%sFF"/>'
             '<base name="PLA Basic Orange" displaycolor="%sFF"/></basematerials>%s%s</resources>\n'
             '<build><item objectid="1" transform="1 0 0 0 1 0 0 0 1 0 0 0"/>'
             '<item objectid="2" transform="1 0 0 0 1 0 0 0 1 0 0 0"/></build>\n</model>\n'
             ) % (NS, tag, WHITE, ORANGE,
                  _obj(c, 1, 'EasyPick case body', 0), _obj(l, 2, 'EasyPick lid', 1))
    ms = ('<?xml version="1.0" encoding="UTF-8"?>\n<config>\n'
          '  <object id="1"><metadata key="name" value="EasyPick case body"/>'
          '<metadata key="extruder" value="1"/></object>\n'
          '  <object id="2"><metadata key="name" value="EasyPick lid"/>'
          '<metadata key="extruder" value="2"/></object>\n</config>\n')

    # Supports off, carried in the file rather than left to the operator.
    # Auto-support fires on the spring slot, and support printed inside that
    # slot cannot be removed and would jam the catch. The key name is Bambu
    # Studio's own — it matches fdm_process_common.json in the installed
    # profiles, and Orca uses the same schema.
    # Kept to the single key: anything else here would be adopted as project
    # settings on import and could quietly replace the operator's own profile.
    ps = '{\n  "enable_support": "0"\n}\n'
    ct = ('<?xml version="1.0" encoding="UTF-8"?><Types xmlns="http://schemas.openxmlformats.org'
          '/package/2006/content-types"><Default Extension="rels" ContentType="application/'
          'vnd.openxmlformats-package.relationships+xml"/><Default Extension="model" '
          'ContentType="application/vnd.ms-package.3dmanufacturing-3dmodel+xml"/>'
          '<Default Extension="config" ContentType="application/xml"/>'
          '<Default Extension="txt" ContentType="text/plain"/></Types>')
    rels = ('<?xml version="1.0" encoding="UTF-8"?><Relationships xmlns="http://schemas.'
            'openxmlformats.org/package/2006/relationships"><Relationship Target='
            '"/3D/3dmodel.model" Id="rel-1" Type="http://schemas.microsoft.com/'
            '3dmanufacturing/2013/01/3dmodel"/></Relationships>')
    why = ('If the slicer offers auto-support for the spring slot at the mouth,\n'
           'decline it. Support inside that slot cannot be removed and would jam\n'
           'the catch. The "floating cantilever" warning there is expected: the\n'
           'strip is a bridge anchored at both ends, not a cantilever.\n'
           if getattr(g, 'HAS_CATCH', True) else
           'There is nothing unsupported in either part — no bridges, no\n'
           'overhangs. If the slicer proposes support anywhere, something is\n'
           'wrong with the orientation, not with the model.\n')
    readme = ('EasyPick case %s\nObject 1  case body -> slot 1  PLA Basic White  %s\n'
              'Object 2  lid       -> slot 2  PLA Basic Orange %s\n'
              'Both parts flat on the plate as modelled.\n\n'
              'NO SUPPORTS. project_settings.config sets enable_support to 0.\n'
              % (tag, WHITE, ORANGE)) + why

    p = OUT + 'easypick-case-%s-colour.3mf' % tag
    with zipfile.ZipFile(p, 'w', zipfile.ZIP_DEFLATED) as z:
        z.writestr('[Content_Types].xml', ct)
        z.writestr('_rels/.rels', rels)
        z.writestr('3D/3dmodel.model', model)
        z.writestr('Metadata/model_settings.config', ms)
        z.writestr('Metadata/project_settings.config', ps)
        z.writestr('Metadata/README.txt', readme)
    return p, stls


# ---------------------------------------------------------------- readme
HISTORY = [
    ('v4',  'first restyle: squircle body, fluted band, flush lid panel'),
    ('v5',  'square base after the first print lifted off the plate'),
    ('v6',  'sprung strip added so the catch has somewhere to flex'),
    ('v7',  'uniform wall offsets, lid tail inset, ribbed lid, clearance opened to 0.30'),
    ('v8',  'cavity to 48 x 61 x 20'),
    ('v9',  'relief holes and chamfers at the spring slot roots'),
    ('v10', 'clearance tightened to 0.25 after a loose print, catch trimmed to hold 2.8 N'),
    ('v11', 'floor dish removed; single build script introduced'),
    ('v12', '2 mm radius where the floor meets the walls'),
    ('v13', 'walls to 4.0 so the outside lands on whole millimetres'),
    ('v14', 'spring slot and catch onto the 0.20 layer grid after the v13 bridge '
            'dropped filament; lid geometry untouched'),
    ('v15', 'catch removed after the spring failed to print twice — the lid is '
            'held by the rails, and nothing in the part is unsupported'),
    ('v16', 'v15 slid open too easily: channel tapered tighter over the last '
            '6 mm at the deep end, plus a push notch through the lip'),
]

def readme(g, case, lid, tag, checks):
    cav = g.int_w * g.int_l * g.int_h
    hist = '\n'.join('| %s | %s |' % (v, d) for v, d in HISTORY)
    hc = checks['has_catch']

    # The catch was removed at v15, so every passage describing it is written
    # from the model rather than left to go stale.
    shut = ('is held shut by a sprung catch at the mouth'
            if hc else 'is held shut by friction in those rails')
    flow = ('''    D["Sprung strip ducks<br/>as the catch passes"] --> E
    E["Groove in the lid<br/>swallows the ridge"] --> F["Closed — %.1f N to open"]'''
            % checks['force'] if hc else
            '''    D["Friction in the rails<br/>holds it shut"] --> F["Closed"]''')
    catch_bullets = ('''- **Sprung catch.** A %.0f mm strip of the end wall, %.1f mm
  thick, is freed by a %.1f mm slot beneath it. It carries a
  %.1f mm ridge giving %.2f mm of net engagement, about
  %.1f N to open. Without the slot the catch would be rigid and
  would not click at all.
- **Relief at the slot roots.** Ø%.1f holes and a %.1f mm
  chamfer inside and out, so the strip roots into a radius rather than a square
  corner that would crack.''' % (g.tongue_w, g.tongue_t, g.slot_h, g.det_h,
                                 checks['net'], checks['force'],
                                 2*g.relief_r, g.slot_ch) if hc else
        '''- **No catch, and nothing unsupported.** The lid is held by the fit of the
  rails. Earlier revisions used a sprung strip at the mouth, but anything that
  has to deflect downward in a part printed flat needs air beneath it, and that
  strip failed to print twice. Removing it leaves the case with no bridges and
  no overhangs anywhere — it is the reason this revision prints.
- **Running clearance is its own number.** `slide_clr` (%.2f mm) grows only the
  channel cut into the case, so the slide can be tightened or loosened without
  touching the lid.''' % getattr(g, 'slide_clr', g.clr))
    if not hc and getattr(g, 'HAS_DETENT_FIT', False):
        zone = ('cut %.2f mm smaller than the lid, so the two must deform '
                'slightly to seat' % (2*abs(g.detent_clr))
                if g.detent_clr < 0 else
                'run at %.2f mm clearance' % g.detent_clr)
        catch_bullets += '''
- **Detent by interference.** The last %.0f mm at the deep end of the channel is
  %s, against %.2f mm of clearance everywhere else.
  Only the lid's leading edge reaches that zone, and only within %.0f mm of
  shut, so the case grips the lid closed instead of resisting across the whole
  travel. Nothing about it is unsupported — it is a change of size in a cut
  that already existed.
- **Push notch.** A %.0f mm window through the lip at the deep end exposes the
  lid's leading edge so it can be pushed toward the mouth. It is a cut rather
  than an addition, so the case still stands %.1f mm tall and pockets flat.''' % (
            g.detent_len, zone, g.slide_clr, g.detent_len, g.notch_w, g.out_h)
    seal = ('the spring slot at the mouth is an opening straight into the\ncavity, so the case is not sealed against water'
            if hc else 'the lid slides in an open channel, so the case is not\nsealed against water')
    reach = ('''The one place nothing will reach is the
%.1f mm spring slot at the mouth — that is the price of a catch that
actually clicks. Printing''' % g.slot_h if hc else
             '''With the spring slot gone there is no longer a
blind pocket anywhere inside. Printing''')
    txt = f"""# EasyPick case

## Why this exists

The case TePe supply with the picks is too small — it holds a handful, while a
pack contains far more. I wanted something that holds the whole pack, keeps the
picks safe and clean, and is easy to travel with. Nothing on the market suited
these picks, so I made this.

## What it is

A slide-lid pocket case for TePe EasyPick interdental picks, printed in two
parts on a Bambu Lab A1. The body holds the picks; the lid slides into rails
cut in the side walls and {shut}.

Everything below is generated from the model itself, so the numbers match the
files in this folder.

![Views]({'easypick-case-%s-views.png' % tag})

## Dimensions

| | Width | Length | Height |
|---|---|---|---|
| Outside | {g.out_w:.1f} | {g.out_l:.1f} | {g.out_h:.1f} |
| Cavity | {g.int_w:.0f} | {g.int_l:.0f} | {g.int_h:.0f} |

Cavity volume {cav:,.0f} mm³. Case body {case.volume:,.0f} mm³ of material,
lid {lid.volume:,.0f} mm³.

![Schematic]({'easypick-case-%s-schematic.png' % tag})

## How it goes together

```mermaid
flowchart LR
    A["Case body<br/>PLA Basic White"] -->|"lid enters at the mouth"| C
    B["Lid<br/>PLA Basic Orange"] --> C
    C["Rails: lid tucks {g.rail:.1f} mm<br/>into each wall"] --> D
{flow}
```

## The height stack

```mermaid
flowchart TD
    F["floor {g.floor_t:.2f}"] --> C["cavity {g.int_h:.0f}"]
    C --> G["clearance {g.clr:.2f}"]
    G --> L["lid plate {g.lid_t:.2f}"]
    L --> P["lip {g.lip:.1f}"]
    P --> T["= {g.out_h:.2f} mm overall"]
```

## Features

- **Slide lid, no hinge.** The lid tucks {g.rail:.1f} mm into each side wall
  under a {g.lip:.1f} mm lip. The groove roof sits at about
  {checks['angle']:.0f}° so it prints unsupported.
{catch_bullets}
- **Flush lid panel** with a {g.gap:.2f} mm shadow gap, ribbed at
  {2.4:.1f} mm pitch across the slide direction for grip.
- **Flat base.** No bottom chamfer — the full footprint meets the plate, which
  is what fixed the first print pulling loose.
- **Uniform wall.** Every profile is an offset of one outline, so the wall is
  {g.wall:.1f} mm on the flats *and* on the diagonals.
- **{g.floor_fillet:.0f} mm radius** where the floor meets the walls: wipeable, and it
  removes the highest-stress line in the part.

## Printing

| | |
|---|---|
| Printer | Bambu Lab A1, 0.4 nozzle |
| Layer | 0.20 mm |
| Walls | 4 loops |
| Material | PLA Basic — White body, Orange lid (PETG if you want it washable) |
| Supports | None — the 3MF sets `enable_support` to 0 |
| Orientation | Both parts flat, as laid out in the 3MF |
| Brim | 5 mm recommended |

Files: `easypick-case-{tag}-colour.3mf` carries both parts with filament slots
assigned, `easypick-case-{tag}.stl` and `easypick-lid-{tag}.stl` are the same
geometry separately.

## Care

Clean it regularly with warm water, then finish with an alcohol wipe. Don't
submerge it — {seal}.

Two things worth knowing if you print it in PLA. Keep the water warm rather than
hot — PLA starts to soften around 55–60 °C, so a dishwasher or a hot tap will
distort it, particularly the rails. And let it dry fully
before the alcohol wipe, so the alcohol is doing the work rather than diluting
into standing water in the corners.

The {g.floor_fillet:.0f} mm radius at the floor means a cotton bud or a fingertip in a
cloth reaches the whole inside. {reach} in PETG instead of PLA lifts the temperature limit
and makes the case properly washable, at the cost of the white-and-orange PLA
Basic pairing.

## Checks run at build time

| Check | Result |
|---|---|
| Case mesh — closed, one body | {checks['case_ok']} |
| Lid mesh — closed, one body | {checks['lid_ok']} |
| Lid protruding outside the shell | {checks['breach']:.2f} mm³ |
| Interference through the full slide | {checks['travel']} |
| Shipped 3MF vs model volume | {checks['volume_match']} |

Mesh volumes are compared to 0.1 mm³. The triangle counts are not compared:
the boolean and hull libraries tessellate flat regions a few triangles
differently between versions, which changes how the shape is written down and
not the shape itself. `make verify` rebuilds this revision and checks it.

## Repository layout

```
.                             latest revision, aliased in the root
├── README.md                 this file (regenerated every revision)
├── CLAUDE.md                 working rules for the project
├── LICENSE                   CERN-OHL-S v2
├── Makefile                  make vNN — build and ship in one step
├── requirements.txt          pinned build dependencies
├── views.png  schematic.png  latest renders
├── easypick-case.3mf         latest, both parts, filament slots assigned
├── easypick-case.stl
├── easypick-lid.stl
├── revisions/                every version, exactly as shipped
│   └── vNN/                  deliverables + geometry.py it was built from
└── src/                      the generator
    ├── geomNN.py             the model — all parameters live here
    ├── render.py             z-buffer renderer for the views
    ├── build.py              one command: views, schematic, README, 3MF, STLs
    ├── ship.py               copies a build into revisions/ and the root
    └── verify.py             rebuilds a revision and diffs it against shipped
```

Build everything from the model, where NN is the revision:

```
make vNN
```

which is `python3 src/build.py geomNN vNN` followed by the copy into
`revisions/vNN/` and the root. G-code is not kept here — it is tied to the
printer, filament and calibration state, so slice it locally from the 3MF.

## Licence

CERN Open Hardware Licence Version 2 — Strongly Reciprocal (CERN-OHL-S v2).
The full text is in [LICENSE](LICENSE).

You may use, make, modify and sell this design. If you distribute a modified
version — as files or as printed parts — the licence requires you to release
your modified source under CERN-OHL-S v2 as well, and to state what you
changed. Modified designs therefore stay publicly available.

Beyond what the licence requires: if you improve this, please send the change
back so there stays one version everyone benefits from. That is a request, not
a condition.

## Revisions

| Version | Change |
|---|---|
{hist}
"""
    p = OUT + 'README.md'
    open(p, 'w').write(txt)
    return p


if __name__ == '__main__':
    mod, tag = sys.argv[1], sys.argv[2]
    os.makedirs(OUT, exist_ok=True)
    g = importlib.import_module(mod)
    case, lid = g.make_case(), g.make_lid()
    print('built from %s: case %.1f mm3 watertight=%s | lid %.1f mm3 watertight=%s'
          % (mod, case.volume, case.is_watertight, lid.volume, lid.is_watertight))
    print(views(g, case, lid, tag))
    print(schematic(g, case, lid, tag))
    p, stls = export(g, case, lid, tag)
    print(p); [print(s) for s in stls]

    back = list(trimesh.load(p).geometry.values())
    match = ('%.1f / %.1f vs %.1f / %.1f mm3'
             % (back[0].volume, back[1].volume, case.volume, lid.volume))
    print('CHECK shipped vs model volume:', match)

    import math
    breach = trimesh.boolean.difference([lid, g.outer_shell()], engine='manifold').volume
    has_catch = getattr(g, 'HAS_CATCH', True)
    if has_catch:
        ridge = g.detent_ridge()
        net = ridge.bounds[1][2] - g.lid_z - g.clr
        span = g.tongue_w + 2*g.relief_r
        force = 192*2000*(g.wall*g.tongue_t**3/12)*net/span**3
    else:
        net = force = 0.0
    # A designed interference fit means the lid SHOULD foul at the closed
    # position. Sample finely near shut so the check can say where the grip
    # releases rather than just failing on it.
    fit = getattr(g, 'HAS_DETENT_FIT', False)
    dists = (0, 3, 6, 10, 20, 55, 80)
    tr = []
    for d in dists:
        t = lid.copy(); t.apply_translation([0, d, 0])
        tr.append(trimesh.boolean.intersection([case, t], engine='manifold').volume)
    free = max(v for d, v in zip(dists, tr) if d >= 10)
    if fit:
        released = [d for d, v in zip(dists, tr) if d > 0 and v < 0.01]
        if free >= 0.01:
            travel = 'FAIL — fouls %.2f mm3 away from the detent' % free
        elif not released:
            travel = 'FAIL — detent never releases within %d mm' % dists[-1]
        else:
            travel = ('detent grips %.1f mm3 shut, free by %d mm, '
                      'clear beyond' % (tr[0], released[0]))
    elif tr[0] >= 0.01:
        travel = 'FAIL — fouls at the closed position'
    elif has_catch:
        travel = 'clear; only the catch, %.1f mm3' % max(tr)
    else:
        travel = 'clear throughout, %.2f mm3 peak' % max(tr)
    checks = dict(case_ok=case.is_watertight and case.body_count == 1,
                  lid_ok=lid.is_watertight and lid.body_count == 1,
                  breach=breach, travel=travel, volume_match=match,
                  net=net, force=force, has_catch=has_catch,
                  angle=math.degrees(math.atan(g.lid_t/g.rail)))
    print(readme(g, case, lid, tag, checks))
